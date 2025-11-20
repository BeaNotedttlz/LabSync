"""
Module for creating and handling the workers for the blocking device communication.
This allows for single device commands and loop calls of methods
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/core/labsync_worker.py
@note:
"""
from typing import Optional

from PySide6.QtCore import QTimer, QThread, QObject, Signal, Slot
from src.core.context import DeviceConnectionError, DeviceRequestError, ErrorType
from src.core.context import DeviceRequest, RequestResult, RequestType, DeviceProfile

class LabSyncWorker(QObject):
	resultReady = Signal(RequestResult)

	def __init__(self, device_id: str, driver: object, profile: DeviceProfile) -> None:
		super().__init__()
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

		if cmd.cmd_type == RequestType.CONNECT:
			self._connect_device(cmd)
		elif cmd.cmd_type == RequestType.DISCONNECT:
			self._disconnect_device(cmd)
		elif cmd.cmd_type == RequestType.START_POLL:
			self._poll_context = cmd
			self._timer.start()
		elif cmd.cmd_type == RequestType.STOP_POLL:
			self._timer.stop()
			self._poll_context = None
		else:
			try:
				param_def = self.profile.parameters[(self.device_id, cmd.parameter)]
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
					else:
						method_to_call(cmd.value)
					result_val = cmd.value
					self.resultReady.emit(RequestResult(self.device_id, cmd.id, value=result_val))
				elif cmd.cmd_type == RequestType.POLL:
					if not param_def.method:
						raise ValueError(f"Parameter '{cmd.parameter}' has no method to call.")

					method_to_call = getattr(self.driver, param_def.method)
					result_val = method_to_call(cmd.value)

					self.resultReady.emit(RequestResult(self.device_id, cmd.id, value=result_val))
			except Exception as e:
				self.resultReady.emit(RequestResult(self.device_id, cmd.id, error=str(e), error_type=ErrorType.TASK))

	def _connect_device(self, cmd: DeviceRequest) -> None:
		try:
			self.driver.open_port(cmd.value[0], cmd.value[1])
			self.resultReady.emit(RequestResult(self.device_id, cmd.id, value=True))
			return
		except DeviceConnectionError as e:
			self.resultReady.emit(RequestResult(self.device_id, cmd.id, error=str(e), error_type=ErrorType.CONNECTION))
			return

	def _disconnect_device(self, cmd: DeviceRequest) -> None:
		if self._timer.isActive():
			self._timer.stop()
			self._poll_context = None

		try:
			self.driver.close_port()
			self.resultReady.emit(RequestResult(self.device_id, cmd.id, value=True))
		except Exception as e:
			self.resultReady.emit(RequestResult(self.device_id, cmd.id, error=str(e), error_type=ErrorType.CONNECTION))
		return

	@Slot()
	def _handle_poll(self) -> None:
		if self._poll_context is not None:
			self.execute_request(self._poll_context)
		else:
			pass


class WorkerHandler(QObject):
	receivedResult = Signal(RequestResult)
	requestWorker = Signal(DeviceRequest)

	def __init__(self, device_id: str, driver_instance: object,
				 profile_instance: DeviceProfile) -> None:
		super().__init__()
		self.device_id = device_id
		self.driver = driver_instance

		self.thread = QThread()
		self._worker = LabSyncWorker(device_id, driver_instance, profile_instance)

		self._worker.moveToThread(self.thread)

		self.requestWorker.connect(self._worker.execute_request)
		self._worker.resultReady.connect(self.receivedResult)

		self.thread.start()
		return

	def send_command(self, cmd: DeviceRequest) -> None:

		if not self.thread.isRunning():
			return
		self.requestWorker.emit(cmd)
		return

	@property
	def is_connected(self) -> bool:
		return getattr(self.driver, "status", False) == ConnectionStatus.CONNECTED

	def stop(self) -> None:
		if self.thread.isRunning():
			self.thread.quit()
			self.thread.wait()

		return