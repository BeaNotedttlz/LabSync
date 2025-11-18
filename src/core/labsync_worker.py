"""
Module for creating and handling the workers for the blocking device communication.
This allows for single device commands and loop calls of methods
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/core/labsync_worker.py
@note:
"""

from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer
from src.backend.connection_status import ConnectionStatus
from typing import Any

class LabSyncWorker(QThread):
	"""
	Class for creating the device worker and running the blocking operations.

	:param device_instance: Instance of the device backend
	:type device_instance: object
	:param poll_method: Device method of the device backend. This defaults to None
	:type poll_method: str | None
	:param poll_interval: Intervall for each call of the poll method
	:type poll_interval: int
	:return: None
	:rtype: None
	"""
	# create signals for functionality
	# signal when the result of the command is ready
	resultReady = Signal(str, object)
	# signal when error occurred during a operation
	errorOccurred = Signal(str)
	# signal when the status of the device connection changed
	statusChanged = Signal(bool)

	def __init__(self, device_instance: object, poll_method: str=None,
				 poll_interval: int=500) -> None:
		"""Constructor method
		"""
		super().__init__()
		# save device and poll parameters to instance
		self.device = device_instance
		self.poll_method = poll_method
		self.poll_interval = poll_interval

		# make timer and connect the timeout signal
		self.timer = QTimer()
		self.timer.timeout.connect(self._process_poll)

	@Slot(str, int)
	def request_connection(self, port: str, baudrate: int | None) -> None:
		"""
		Request a connection to the device.

		:param port: Port of the serial device
		:type port: str
		:param baudrate: Baud rate of the serial device
		:type baudrate: int
		:return: None
		:rtype: None
		"""
		try:
			# try to open the device
			if baudrate is None:
				self.device.open_port(port)
			else:
				self.device.open_port(port, baudrate)
			self.statusChanged.emit(True)

			if self.poll_method:
				# start timer if a poll method exists
				self.timer.start(self.poll_interval)
			return
		except Exception as e:
			self.errorOccurred.emit(str(e))

	@Slot()
	def request_disconnection(self) -> None:
		"""
		Request a disconnection to the device.

		:return: None
		:rtype: None
		"""
		try:
			# stop the timer
			self.timer.stop()
			# close the serial port
			self.device.close_port()
			self.statusChanged.emit(False)
		except Exception as e:
			self.errorOccurred.emit(str(e))

	def _process_poll(self) -> None:
		"""
		Process the poll method.

		:return: None
		:rtype: None
		"""
		if self.device.status == ConnectionStatus.DISCONNECTED:
			# if the device is disconnected stop the timer
			# this is to check if the device suddenly disconnected to not span errors
			self.timer.stop()
			return
		else:
			# execute the task of the poll
			self.execute_task("POLL", self.poll_method, [], {})
			return

	@Slot(str, str, list, dict)
	def execute_task(self, request_id: str, method: str, args: list, kwargs: dict) -> None:
		"""
		Execute a task of the serial device. This is the blocking operation in the thread.

		:param request_id: The ID of the request. This is to identify the data
		:type request_id: str
		:param method: Method to run
		:type method: str
		:param args: Arguments to run
		:type args: list
		:param kwargs: Arguments to run
		:type kwargs: dict
		:raises AttributeError: If the device does not have the method specified to run
		:return: None
		:rtype: None
		"""
		if self.device.status == ConnectionStatus.DISCONNECTED:
			if request_id == "POLL":
				# stop the timer if the deviec is disconnected
				self.errorOccurred.emit(request_id)
			# dont execute the task if the device is disconnected
			return

		try:
			if not hasattr(self.device, method):
				# check if the device has the desired attribute
				raise AttributeError(f"Unknown method '{method}'")
			# get the actual method of the device
			method = getattr(self.device, method)
			# run the task and get the result
			result = method(*args, **kwargs)
			# emit the result signal
			self.resultReady.emit(request_id, result)
		except Exception as e:
			self.errorOccurred.emit(str(e))

class WorkerHandler(QObject):
	"""
	Class for handling the workers for the blocking device communication.

	:param device_instance: Instance of the device backend
	:type device_instance: object
	:param port: Port of the serial device
	:type port: str
	:param baudrate: Baud rate of the serial device
	:type baudrate: int
	:param poll_method: Device method of the device backend. This defaults to None
	:type poll_method: str | None
	"""
	# create signals for functionality
	# send a operation to the worker
	sendToWorker = Signal(str, str, list, dict)
	# request connection to the worker
	connectSig = Signal(str, object)
	# request disconnection to the worker
	disconnectSig = Signal()

	# get new polling data
	newPollData = Signal(object)
	# get new task data
	taskData = Signal(str, object)
	# notify if the connection has changed
	connectionChanged = Signal(bool)
	# notify if an error occurred
	errorMessage = Signal(str)

	def __init__(self, device_instance: object, port: str, baudrate: int | None,
				 poll_method: str=None) -> None:
		"""Constructor method
		"""
		super().__init__()
		# save port and baudrate
		self.port = port
		self.baudrate = baudrate
		# create the thread of the worker
		self.thread = QThread()
		# create worker instance
		self.worker = LabSyncWorker(device_instance, poll_method)
		# move the worker to the new thread
		self.worker.moveToThread(self.thread)

		# connect the signals to the worker
		self.connectSig.connect(self.worker.request_connection)
		self.disconnectSig.connect(self.worker.request_disconnection)
		self.sendToWorker.connect(self.worker.execute_task)

		# connect signals for result and error handling
		self.worker.resultReady.connect(self._handle_result)
		self.worker.statusChanged.connect(self.connectionChanged)
		self.worker.errorOccurred.connect(self.errorMessage)

		# handle the finishing of the worker / thread
		self.thread.finished.connect(self.thread.deleteLater)
		self.thread.start()

		# inital connection request of the device
		self.connect_device()

	@Slot(str, object)
	def _handle_result(self, request_id: str, result: Any) -> None:
		"""
		Handle the result of the worker.

		:param request_id: ID of the request. This is to identify the data.
		:type request_id: str
		:param result: The actual result of the worker.
		:type result: Any
		:return: Only emits a signal and does not return anything
		:rtype: None
		"""
		if request_id == "POLL":
			# emit the poll result signal
			self.newPollData.emit(result)
		else:
			# emit the data result on any other request
			self.taskData.emit(request_id, result)
		return

	def connect_device(self) -> None:
		"""
		Request a connection to the serial device using the worker.

		:return: None
		:rtype: None
		"""
		self.connectSig.emit(self.port, self.baudrate)
		return

	def disconnect_device(self) -> None:
		"""
		Request a disconnection to the serial device using the worker.

		:return: None
		:rtype: None
		"""
		self.disconnectSig.emit()
		return

	def request_task(self, request_id: str, method: str, *args, **kwargs) -> None:
		"""
		Request a task.

		:param request_id: ID of the request. This is to identify the data.
		:type request_id: str
		:param method: Method to be executed
		:type method: str
		:param args: Arguments to run
		:type args: list
		:param kwargs: Arguments to run
		:type kwargs: dict
		:return: None
		:rtype: None
		"""
		self.sendToWorker.emit(request_id, method, list(args), kwargs)
		return

	def cleanup(self) -> None:
		"""
		Cleanup method to handle closing of the application.
		This is to ensure all threads are closed before closing the application.

		:return: None
		:rtype: None
		"""
		self.disconnect_device()
		self.thread.quit()
		self.thread.wait()

