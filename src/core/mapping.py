"""
Module for the mapping of different parameters and values.
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/core/mapping.py
@note:
"""

from typing import Any, Callable, Optional, Dict
from dataclasses import dataclass

@dataclass
class Parameter:
	"""
	Represents one controllable setting on a device.

	:return: None
	:rtype: None
	"""
	# the key used in the backend / frontend -> (device, parameter)
	key: tuple

	# the name of the driver method
	method: str = None

	# Validation types
	min_value: Any = None
	max_value: Any = None
	unit: str = ""

	data_type: type = None

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

	:return: None
	:rtype: None
	"""
	def __init__(self) -> None:
		self._params: Dict[tuple, Parameter] = {}

	def add(self, param: Parameter) -> None:
		self._params[param.key] = param
		return

	def get(self, key: tuple) -> Parameter:
		return self._params[key]

	def get_all(self) -> Dict[tuple, Parameter]:
		return self._params