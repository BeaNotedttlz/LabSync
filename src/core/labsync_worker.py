"""
Module for creating and handling the workers for the blocking device communication.
This allows for single device commands and loop calls of methods
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/core/labsync_worker.py
@note:
"""
from typing import List, Tuple
from PySide6.QtCore import QTimer, QThread, QObject, Signal, Slot
from src.core.context import DeviceConnectionError, ErrorType
from src.core.context import DeviceRequest, RequestResult, RequestType, DeviceProfile
from src.backend.connection_status import ConnectionStatus

class LabSyncWorker(QObject):
	"""
	Worker for direct device connection and communication.
	This will run the blocking operations and send / receive data.
	"""
	# result signal for communication with the handler
	resultReady = Signal(RequestResult)

	def __init__(self, device_id: str, driver: object, profile: DeviceProfile) -> None:
		super().__init__()
		"""Constructor method
		"""
		# save own ID, Driver instance and device profile
		self.device_id = device_id
		self.driver = driver
		self.profile =profile

		# create timer for poll method
		self._timer = QTimer(self)
		self._timer.timeout.connect(self._handle_poll)

		# save poll_context
		self._poll_contexts: List[Tuple[DeviceRequest, int]] = []
		return

	@Slot(DeviceRequest)
	def execute_request(self, cmd: DeviceRequest) -> None:
		"""
		Executes the requested operation by the DeviceRequest object.
		This will also handle connection and disconnection, as well as the start and stop of the polling.
		Since QEvents work in a queue, SET/POLL requests are possible while the polling is running.
		:param cmd: Request for the device
		:type cmd: DeviceRequest
		:return: None
		"""
		# Handle connection and disconnection requests
		if cmd.cmd_type == RequestType.CONNECT:
			self._connect_device(cmd)
		elif cmd.cmd_type == RequestType.DISCONNECT:
			self._disconnect_device(cmd)

		# Handle quit request on application shutdown
		elif cmd.cmd_type == RequestType.QUIT:
			# disconnect device and clear poll contexts
			self._disconnect_device(cmd)
			self._poll_contexts.clear()

		# Handle polling requests
		elif cmd.cmd_type == RequestType.START_POLL:
			# get interval from the value, default to 500ms
			interval = int(cmd.value) if cmd.value else 500
			# only add new poll context if not already existing
			if not any(ctx.parameter == cmd.parameter for ctx, _ in self._poll_contexts):
				poll_request = DeviceRequest(
					device_id=cmd.device_id,
					cmd_type=RequestType.POLL,
					parameter=cmd.parameter
				)
				# add to poll contexts
				self._poll_contexts.append((poll_request, interval))

			'''
			(re)start timer with the minimum interval of all poll contexts.
			This ensures that the minimum polling rate is maintained, while individual rates will be ignored.
			This is the only "pretty" solution without creating <x> timers for all poll contexts with different intervals.
			'''
			if self._poll_contexts:
				min_interval = min(interval for _, interval in self._poll_contexts)
				self._timer.start(min_interval)
		# Handle stopping of polling
		# Stops all polling if no parameter is given. Otherwise, stops only the given parameter.
		elif cmd.cmd_type == RequestType.STOP_POLL:
			if cmd.parameter is None:
				self._timer.stop()
				self._poll_contexts.clear()
			else:
				# This removes the poll context with the given parameter
				# This uses a list comprehension to filter out the context, as removing items during iteration is not safe.
				self._poll_contexts = [(c, i) for (c, i) in self._poll_contexts if c.parameter != cmd.parameter]
				if not self._poll_contexts:
					# If no poll contexts are left, the current timer will be stopped
					self._timer.stop()
				else:
					# Otherwise restart the timer with the new minimum interval as explained before.
					min_interval = min(interval for _, interval in self._poll_contexts)
					self._timer.start(min_interval)
		# Handle SET and POLL requests
		else:
			try:
				# Get parameter definition from profile
				param_def = self.profile.parameters[cmd.parameter]
			except KeyError as e:
				# Return error if parameter is not found / defined.
				self.resultReady.emit(RequestResult(self.device_id, cmd.id, error=str(e)))
				return
			try:
				if cmd.cmd_type == RequestType.SET:
					# Return Error if no method is defined for the given parameter. This should not happen if the profile is defined correctly.
					if not param_def.method:
						self.resultReady.emit(RequestResult(
							self.device_id,
							cmd.id,
							error=f"Parameter '{cmd.parameter}' has no method to call.",
							error_type=ErrorType.TASK
						))
						return
					# Validate the value before setting it.
					# If validation fails, return an error (Low level Task error).
					if not param_def.validate(cmd.value):
						self.resultReady.emit(RequestResult(
							self.device_id,
							cmd.id,
							error=f"Validation failed for parameter '{cmd.parameter}' with value '{cmd.value}'\n"
								  f"{cmd.value} not in valid parameter range: {param_def.min_value} - {param_def.max_value}!",
							error_type=ErrorType.TASK
						))
						return

					# Get method to call for the parameter
					method_to_call = getattr(self.driver, param_def.method)
					if isinstance(cmd.value, tuple):
						# Handle tuple values (e.g., (value, channel)) for the frequency generator.
						method_to_call(cmd.value[1], cmd.value[0])
					elif cmd.value is None:
						# If no value is given, call the method without parameters. E.g. Start for EcoVario.
						method_to_call()
					else:
						# Otherwise call the method with the given parameter value.
						method_to_call(cmd.value)
					# Emit successful result after setting the value without exceptions.
					result_val = cmd.value
					self.resultReady.emit(RequestResult(self.device_id, cmd.id, value=result_val))
				elif cmd.cmd_type == RequestType.POLL:
					if not param_def.method:
						# Return error if no method is defined for the parameter. This should not happen if the profile is defined correctly.
						raise ValueError(f"Parameter '{cmd.parameter}' has no method to call.")

					# Get the method and call once to retrieve the value.
					method_to_call = getattr(self.driver, param_def.method)
					result_val = method_to_call()

					# Return the polled value.
					self.resultReady.emit(RequestResult(self.device_id, cmd.id, value=result_val))
			except Exception as e:
				import traceback
				print(traceback.format_exc())
				# Catch all exceptions during SET and POLL operations and return as Task error.
				self.resultReady.emit(RequestResult(self.device_id, cmd.id, error=str(e), error_type=ErrorType.TASK))

	def _connect_device(self, cmd: DeviceRequest) -> None:
		"""
		handler for connecting to the serial port of the device.
		:param cmd: Connection request. The port and baudrate should be in the value of the request
		:type cmd: DeviceRequest
		:return: None
		"""
		try:
			# Attempt to open the port with the given port and baudrate
			self.driver.open_port(cmd.value[0], cmd.value[1])
			# on success emit result to update UI
			self.resultReady.emit(RequestResult(self.device_id, cmd.id, value=True))
			if self._poll_contexts:
				# Restart timer if there are active poll contexts waiting to be called
				min_interval = min(interval for _, interval in self._poll_contexts)
				self._timer.start(min_interval)
			return
		except DeviceConnectionError as e:
			# On connection error, emit error result
			if cmd.parameter is not None and cmd.parameter == "SILENT":
				# For silent connections, only emit INIT_CONNECTION errors
				# TODO: This works but allows for active polling after failed silent connection attempts.
				# This should be fixed in future solutions -> no need for the "None" handling later on.
				self.resultReady.emit(RequestResult(self.device_id, cmd.id, error=str(e), error_type=ErrorType.INIT_CONNECTION))
			else:
				self.resultReady.emit(RequestResult(self.device_id, cmd.id, error=str(e), error_type=ErrorType.CONNECTION))
			return

	def _disconnect_device(self, cmd: DeviceRequest) -> None:
		"""
		handler for disconnecting from the serial port of the device.
		:param cmd: Disconnection request.
		:type cmd: DeviceRequest
		:return:
		"""
		if self._poll_contexts:
			# emit None for all active poll contexts to indicate disconnection
			# TODO: This suffers the same issue as above with silent connections. Needs to be fixed in future solutions.
			# This should be handled differently to avoid active polling after disconnection.
			for ctx, _ in self._poll_contexts:
				self.resultReady.emit(RequestResult(
					device_id=self.device_id,
					request_id=ctx.id,
					value=None
				))
		# Stop active timer
		if self._timer.isActive():
			self._timer.stop()

		try:
			# Try to close the device port
			self.driver.close_port()
			# on success emit result to update UI
			self.resultReady.emit(RequestResult(self.device_id, cmd.id, value=False))
		except Exception as e:
			# on error emit error result
			self.resultReady.emit(RequestResult(self.device_id, cmd.id, error=str(e), error_type=ErrorType.CONNECTION))
		return

	@Slot()
	def _handle_poll(self) -> None:
		"""
		Handles the polling of the device. Iterate over all active poll contexts.
		"""
		# Execute poll requests on timer timeout. This will call the execute_request method for each poll context.
		# TODO: This could lead to long downtimes if many poll contexts are active with long response times.
		# This could also lead to overlapping calls if the response time is longer than the polling interval.
		# Future solutions could implement individual timers for each poll context or a more complex scheduling system
		for ctx, _ in list(self._poll_contexts):
			self.execute_request(ctx)
		return


class WorkerHandler(QObject):
	"""
	Handler for the device worker. This creates the thread and places the worker.
	This handles the results, connection and cleanup.
	"""
	# Signal for receiving the result from the worker
	receivedResult = Signal(RequestResult)
	# Signal for requesting a task from the worker
	requestWorker = Signal(DeviceRequest)
	# Signal emitted when the handler has finished shutting down
	handlerFinished = Signal(str)

	def __init__(self, device_id: str, driver_instance: object,
				 profile_instance: DeviceProfile) -> None:
		"""Constructor method
		"""
		super().__init__()
		# save own device ID and device instance
		self.device_id = device_id
		self.driver = driver_instance

		# create thread and worker
		self._thread = QThread()
		self._worker = LabSyncWorker(device_id, driver_instance, profile_instance)
		# move worker to new thread
		self._worker.moveToThread(self._thread)

		# connect Signals for results and requests
		self._worker.resultReady.connect(self.handle_result)
		self.requestWorker.connect(self._worker.execute_request)
		self._thread.finished.connect(self._on_thread_finished)

		# start thread
		self._thread.start()
		return

	def send_request(self, cmd: DeviceRequest) -> None:
		"""
		Sends the request to the device worker. Checks if the device ID from the request matches the requested device ID.
		Otherwise, returns an error signal.
		:return: None
		"""
		# Don't do anything is the thread is not running
		if not self._thread.isRunning():
			return

		# Check requested device ID and emit error if not matching
		request_device_id = cmd.device_id
		if not request_device_id == self.device_id or request_device_id is None:
			self.receivedResult.emit(RequestResult(self.device_id, cmd.id,
												   error=f"Request device_id: {request_device_id} is not valid",
												   error_type=ErrorType.TASK))
			return
		# Emit the request to the worker
		else:
			self.requestWorker.emit(cmd)
			return

	def handle_result(self, result: RequestResult) -> None:
		"""
		Handles the result of the worker. This passes the result to the controller.
		:param result: Result from the worker
		:type result: RequestResult
		:return: None
		"""
		# Pass the result to the LabSyncController
		self.receivedResult.emit(result)
		if result.request_id.startswith(RequestType.QUIT.value):
			# If the result is from a QUIT request, stop the thread and wait for close.
			self._thread.quit()
			self._thread.wait()
		return

	def start_shutdown(self) -> None:
		"""
		Non-blocking shutdown request. Called by MainWindow.closeEvent
		:return: None
		"""
		# Don't do anything is the thread is not running
		if not self._thread.isRunning():
			# Immediately emit finished signal
			self.handlerFinished.emit(self.device_id)
			return

		# Generate QUIT request to stop all active polls
		self.requestWorker.emit(DeviceRequest(
			device_id=self.device_id,
			cmd_type=RequestType.STOP_POLL
		))

		# Generate QUIT request to stop the worker and thread
		self.requestWorker.emit(DeviceRequest(
			device_id=self.device_id,
			cmd_type=RequestType.QUIT
		))
		return

	def _on_thread_finished(self) -> None:
		self.handlerFinished.emit(self.device_id)
		return

	@property
	def is_connected(self) -> bool:
		"""Returns the connection status of the device"""
		return getattr(self.driver, "status", False) == ConnectionStatus.CONNECTED
