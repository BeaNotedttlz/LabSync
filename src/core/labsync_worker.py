"""
Module for creating and handling the workers for the blocking device communication.
This allows for single device commands and loop calls of methods
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/core/labsync_worker.py
@note:
"""
from typing import Optional, Any

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
		self._poll_context: Optional[DeviceRequest] = None
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
		if cmd.cmd_type == RequestType.CONNECT:
			self._connect_device(cmd)
		elif cmd.cmd_type == RequestType.DISCONNECT or cmd.cmd_type == RequestType.QUIT:
			self._disconnect_device(cmd)
		elif cmd.cmd_type == RequestType.START_POLL:
			self._poll_context = cmd
			self._timer.start(cmd.value if cmd.value else 500)
		elif cmd.cmd_type == RequestType.STOP_POLL:
			self._timer.stop()
			self._poll_context = None
		else:
			try:
				param_def = self.profile.parameters[cmd.parameter]
			except KeyError as e:
				self.resultReady.emit(RequestResult(self.device_id, cmd.id, error=str(e)))
				return
			try:
				if cmd.cmd_type == RequestType.SET:
					if not param_def.method:
						raise ValueError(f"Parameter '{cmd.parameter}' has no method to call.")

					method_to_call = getattr(self.driver, param_def.method)
					if isinstance(cmd.value, list):
						method_to_call(cmd.value[0], cmd.value[1])
					elif cmd.value is None:
						method_to_call()
					else:
						method_to_call(cmd.value)
					result_val = cmd.value
					self.resultReady.emit(RequestResult(self.device_id, cmd.id, value=result_val))
				elif cmd.cmd_type == RequestType.POLL:
					if not param_def.method:
						raise ValueError(f"Parameter '{cmd.parameter}' has no method to call.")

					method_to_call = getattr(self.driver, param_def.method)
					result_val = method_to_call()

					self.resultReady.emit(RequestResult(self.device_id, cmd.id, value=result_val))
			except Exception as e:
				self.resultReady.emit(RequestResult(self.device_id, cmd.id, error=str(e), error_type=ErrorType.TASK))

	def _connect_device(self, cmd: DeviceRequest) -> None:
		"""
		handler for connecting to the serial port of the device.
		:param cmd: Connection request. The port and baudrate should be in the value of the request
		:type cmd: DeviceRequest
		:return: None
		"""
		try:
			self.driver.open_port(cmd.value[0], cmd.value[1])
			self.resultReady.emit(RequestResult(self.device_id, cmd.id, value=True))
			return
		except DeviceConnectionError as e:
			self.resultReady.emit(RequestResult(self.device_id, cmd.id, error=str(e), error_type=ErrorType.CONNECTION))
			return

	def _disconnect_device(self, cmd: DeviceRequest) -> None:
		"""
		handler for disconnecting from the serial port of the device.
		:param cmd: Disconnection request.
		:type cmd: DeviceRequest
		:return:
		"""
		if self._timer.isActive():
			self._timer.stop()
			self._poll_context = None

		try:
			self.driver.close_port()
			self.resultReady.emit(RequestResult(self.device_id, cmd.id, value=False))
		except Exception as e:
			self.resultReady.emit(RequestResult(self.device_id, cmd.id, error=str(e), error_type=ErrorType.CONNECTION))
		return

	@Slot()
	def _handle_poll(self) -> None:
		"""
		Handles the polling of the device. This Slot will be called each time after the timer timeouts.
		:return: None
		"""
		if self._poll_context is not None:
			self.execute_request(self._poll_context)
		else:
			pass


class WorkerHandler(QObject):
	"""
	Handler for the device worker. This creates the thread and places the worker.
	This handles the results, connection and cleanup.
	"""
	# Signal for receiving the result from the worker
	receivedResult = Signal(RequestResult)
	# Signal for requesting a task from the worker
	requestWorker = Signal(DeviceRequest)

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
		Otherwise returns an error signal.
		:return: None
		"""
		# dont do anything is the thread is not running
		if not self._thread.isRunning():
			return

		request_device_id = cmd.device_id
		if not request_device_id == self.device_id or request_device_id is None:
			self.receivedResult.emit(RequestResult(self.device_id, cmd.id,
												   error=f"Request device_id: {request_device_id} is not valid",
												   error_type=ErrorType.TASK))
			return
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
		self.receivedResult.emit(result)
		if result.request_id.startswith(RequestType.QUIT.value):
			self._thread.quit()
			self._thread.wait()
		return

	def start_shutdown(self) -> None:
		"""
		Non-blocking shutdown request. Called by MainWindow.closeEvent
		:return: None
		"""
		if not self._thread.isRunning():
			self.handlerFinished.emit(self.device_id)
			return

		self.requestWorker.emit(DeviceRequest(
			device_id=self.device_id,
			cmd_type=RequestType.STOP_POLL
		))

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
