"""
Module for creating and managing all device Context during runtime.
@author: Merlin Schmidt
@date: 2025-19-10
@file: src.core.context.py
@note:
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional, Dict

# Request and Error types
class RequestType(Enum):
	"""Defines the intent of the request"""
	# set a singular valur
	SET = "SET"
	# query a singular value
	POLL = "POLL"
	# start polling a value
	START_POLL = "START_POLL"
	# stop polling a value
	STOP_POLL = "STOP_POLL"
	# connect to device
	CONNECT = "CONN"
	# disconnect device
	DISCONNECT = "DISCONN"

class ErrorType(Enum):
	"""Defines the type and severity of the error"""
	# connection error
	CONNECTION = auto()
	# read or write error
	TASK = auto()
	# critical application error
	CRITICAL = auto()
	# device timeout error
	TIMEOUT = auto()

# Requests
# Device worker requests
@dataclass(frozen=True)
class DeviceRequest:
	"""
	A request from LabSync sent to the worker.
	frozen=True makes this class immutable (for thread safety)
	"""
	# Device ID ("EcoVario", "Laser1", "Laser2", "TGA1244", "FSV3000")
	device_id: str
	# Type of the command
	cmd_type: RequestType
	# Parameter name (e.g. "frequency")
	parameter: Optional[str] = ""
	# value of the request
	value: Optional[Any] = None

	@property
	def id(self) -> str:
		"""
		Generates a unique request ID
		FORMAT: POLL/SET_DEVICE_PARAMETER
		:return: The unique device request ID
		:rtype: str
		"""
		return f"{self.cmd_type.value}_{self.device_id}_{self.parameter}"

@dataclass
class RequestResult:
	"""
	A response sent from the worker after request.
	"""
	# device ID
	device_id: str
	# ID of the request
	request_id: str

	# value of the return
	value: Optional[Any] = None
	# potential error
	error: Optional[str] = None
	# type of the error
	error_type: Optional[ErrorType] = None

	@property
	def is_success(self) -> bool:
		return self.error is None

# UI requests
@dataclass
class UIRequest:
	# Device ID
	device_id: str
	# parameter
	parameter: str
	# type of request
	cmd_type: RequestType
	# value
	value: Optional[Any] = None

# Device Parameters and profiles
@dataclass
class Parameter:
	"""
	Represents one controllable setting on a device.
	"""
	# the key used in the backend / frontend -> (device, parameter)
	key: str

	# the name of the driver method
	method: str = None

	# validation types
	min_value: float = None
	max_value: float = None
	unit: str = ""
	data_type: type = float

	def validate(self, value: Any) -> bool:
		"""
		Checks if the given value is within the limits

		:param value: Value to be checked
		:type value: Any
		:return: Returns True if the value is within the limits otherwise falls
		:rtype: bool
		"""
		if self.data_type in [int, float] and (self.min_value is None or value is not None):
			if value < self.min_value or value > self.max_value:
				return False
		return True

class DeviceProfile:
	"""
	A collection of the parameter for a specific device.
	"""
	def __init__(self) -> None:
		"""Constructor method
		"""
		# Stores parameter -> Parameter object
		self._params: Dict[str, Parameter] = {}
		return

	@property
	def parameters(self) -> Dict[str, Parameter]:
		"""Access parameter handlers directly"""
		return self._params.copy()

	def add(self, param: Parameter) -> None:
		if not param.key in self._params:
			self._params[param.key] = param
		else:
			raise KeyError(f"{param.key} already exists")
		return

# Custom device exceptions on the DeviceError base exception
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
