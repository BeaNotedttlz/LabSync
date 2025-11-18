

from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer
from src.backend.connection_status import ConnectionStatus
from typing import Any, Dict, List

class LabSyncWorker(QThread):

	resultReady = Signal(str, object)
	errorOccurred = Signal(str)
	statusChanged = Signal(bool)

	def __init__(self, device_instance: object, poll_method: str=None,
				 poll_interval: int=500) -> None:
		super().__init__()
		self.device = device_instance
		self.poll_method = poll_method
		self.poll_interval = poll_interval

		self.timer = QTimer()
		self.timer.timeout.connect(self._process_poll)

	@Slot(str, int)
	def reqest_connection(self, port: str, baudrate: int) -> None:
		try:
			self.device.open_port(port, baudrate)
			self.statusChanged.emit(True)

			if self.poll_method:
				self.timer.start(self.poll_interval)
			return
		except Exception as e:
			self.errorOccurred.emit(str(e))

	@Slot()
	def request_disconnection(self) -> None:
		try:
			self.timer.stop()
			self.device.close_port()
			self.statusChanged.emit(False)
		except Exception as e:
			self.errorOccurred.emit(str(e))

	def _process_poll(self) -> None:
		if self.device.status == ConnectionStatus.DISCONNECTED:
			self.timer.stop()
			return
		else:
			self.execute_task("POLL", self.poll_method, [], {})
			return

	@Slot(str, str, list, dict)
	def execute_task(self, request_id: str, method: str, args: list, kwargs: dict) -> None:
		if self.device.status == ConnectionStatus.DISCONNECTED:
			if request_id == "POLL":
				self.errorOccurred.emit(request_id)
			return

		try:
			if not hasattr(self.device, method):
				raise AttributeError(f"Unknown method '{method}'")

			method = getattr(self.device, method)

			result = method(*args, **kwargs)

			self.resultReady.emit(request_id, result)
		except Exception as e:
			self.errorOccurred.emit(str(e))

class WorkerHandler(QObject):

	sendToWorker = Signal(str, str, list, dict)
	connectSig = Signal(str, int)
	disconnectSig = Signal()

	newPollData = Signal(object)
	taskData = Signal(str, object)
	connectionChanged = Signal(bool)
	errorMessage = Signal(str)

	def __init__(self, device_instance: object, port: str, baudrate: int,
				 poll_method: str=None) -> None:
		super().__init__()
		self.port = port
		self.baudrate = baudrate

		self.thread = QThread()
		self.worker = LabSyncWorker(device_instance, poll_method)
		self.worker.moveToThread(self.thread)

		self.connectSig.connect(self.worker.reqest_connection)
		self.disconnectSig.connect(self.worker.request_disconnection)
		self.sendToWorker.connect(self.worker.execute_task)

		self.worker.resultReady.connect(self._handle_result)
		self.worker.statusChanged.connect(self.connectionChanged)
		self.worker.errorOccurred.connect(self.errorMessage)

		self.thread.finished.connect(self.thread.deleteLater)
		self.thread.start()

		self.connect_device()

	@Slot(str, object)
	def _handle_result(self, request_id: str, result: Any) -> None:
		if request_id == "POLL":
			self.newPollData.emit(result)
		else:
			self.taskData.emit(request_id, result)

		return

	def connect_device(self) -> None:
		self.connectSig.emit(self.port, self.baudrate)
		return

	def disconnect_device(self) -> None:
		self.disconnectSig.emit()
		return

	def request_task(self, request_id: str, method: str, *args, **kwargs) -> None:
		self.sendToWorker.emit(request_id, method, list(args), kwargs)
		return

	def cleanup(self) -> None:
		self.disconnect_device()
		self.thread.quit()
		self.thread.wait()

