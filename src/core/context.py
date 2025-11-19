"""
Module for creating and managing all device Context during runtime.
@author: Merlin Schmidt
@date: 2025-19-10
@file: src.core.context.py
@note:
"""

from dataclasses import dataclass, field
from PySide6.QtCore import QThread, QObject, QMetaObject
from PySide6.QtWidgets import QWidget

from src.backend.connection_status import ConnectionStatus
from src.core.labsync_worker import WorkerHandler

from enum import Enum, auto
from typing import Any, Optional, Dict

class RequestType(Enum):
	"""Defines the intent of the command"""
	# reading data from a timer
	POLL = "POLL"
	# reading / writing data via user input
	SET = "SET"

class ErrorType(Enum):
	"""defines the severity and category of an error"""
	CONNECTION = auto()
	READ = auto()
	WRITE = auto()
	CRITICAL = auto()
	TIMEOUT = auto()

@dataclass(frozen=True)
class DeviceRequest:
	"""
	A request sent from LabSync to the worker.
	frozen=True makes this class immutable (for thread safety)
	"""
	device_id: str
	parameter: str
	cmd_type: RequestType
	value: Any = None

	@property
	def id(self) -> str:
		"""
		Generates a unique request ID.
		FORMAT: POLL/SET_DEVICE_PARAMETER
		"""
		return f"{self.cmd_type.value}_{self.device_id}_{self.parameter}"

@dataclass
class RequestResult:
	"""
	A response sent from the worker to LabSync.
	"""
	command_id: str
	device_id: str

	value: Any = None
	error: Optional[str] = None
	error_type: Optional[ErrorType] = None

	@property
	def is_success(self) -> bool:
		return self.error is None

class Parameter:
	"""
	Represents one controllable setting on a device.
	"""
	# the key used in the backend / frontend -> (device, parameter)
	key: tuple

	# the name of the driver method
	method: str = None
	handler: WorkerHandler = None

	# Validation types
	min_value: float = None
	max_value: float = None
	unit: str = ""
	data_type: type = float

	def validate(self, value: Any) -> bool:
		"""
		Checks if the value is within the limits

		:param value: value to check
		:type value: Any
		:return: If the value is within the limits or not (True/False)
		:rtype: bool
		"""
		if self.data_type in [int, float] and (self.min_value is None or value is not None):
			if value < self.min_value or value > self.max_value:
				return False
		return True

class DeviceProfile:
	"""
	A collection of the parameters for a specific device
	"""
	def __init__(self) -> None:
		"""Constructor method
		"""
		# Stores (device, parameter) -> Parameter object
		self._params: Dict[tuple, Parameter] = {}
		# Stores Device -> Handler object
		self._handlers: Dict[str, WorkerHandler] = {}
		return

	def add(self, param: Parameter) -> None:
		self._params[param.key] = param

		if param.key and len(param.key) > 0:
			device_name = param.key[0]
			if param.handler is not None:
				self._handlers[device_name] = param.handler
		return

	@property
	def devices(self) -> Dict[str, WorkerHandler]:
		"""Access device handlers directly."""
		return self._handlers

	@property
	def parameters(self) -> Dict[tuple, Parameter]:
		"""Access parameter objects directly."""
		return self._params

@dataclass
class DeviceContext:
	"""
	Holds the entire lifecycle state of a worker.
	"""

	device_id: str
	profile: DeviceProfile

	driver: object
	worker: QObject
	thread: QThread

	widgets: Dict[str, QWidget] = field(default_factory=dict)

	def is_connected(self) -> bool:
		"""Save check for connection status"""
		if hasattr(self.driver, "status"):
			state = self.driver.status
			return state == ConnectionStatus.CONNECTED
		else:
			return False

	def send_request(self, cmd: DeviceRequest) -> None:
		QMetaObject.invokeMethod(
			self.worker,
			"execute_request",
			Qt.QueuedConnection,
			cmd
		)

	def cleanup(self) -> None:
		"""Stops the thread cleanly"""
		if self.thread.isRunning():
			self.thread.quit()
			self.thread.wait()

class DeviceError(Exception):
	"""Base class for all device exceptions"""
	pass

class DeviceConnectionError(DeviceError):
	"""Raised when opening the serial port fails"""
	def __init__(self, device_id: str, original_error: Exception=None):
		self.device_id = device_id
		msg = f"Could not connect to device {device_id}"
		if original_error:
			msg += f" Reason: {original_error}"
		super().__init__(msg)

class DeviceRequestError(DeviceError):
	"""Raised when the handling of a request fails"""
	def __init__(self, device_id: str, request_id: str, original_error: Exception=None):
		self.device_id = device_id
		self.request = request_id
		msg = f"Something went wrong for {device_id} and request {request_id}"
		if original_error:
			msg += f" Reason: {original_error}"
		super().__init__(msg)
