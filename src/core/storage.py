

from typing import Any, Dict
from PySide6.QtCore import QObject, Signal

class InstrumentCache(QObject):
	"""
	Class for caching instrument parameters and respective values.
	This also checks if the values are the same.

	:return: None
	:rtype: None
	"""
	valueChanged = Signal(tuple)

	def __init__(self) -> None:
		"""Constructor method
		"""
		super().__init__()
		self._cache: Dict[tuple, Any] = {}

	def get_value(self, device: str, parameter: str) -> Any | None:
		"""
		Retrieves the value for the given parameter.

		:param device: The device name
		:type device: str
		:param parameter: Name of the parameter
		:type parameter: str
		:return: The current value of the parameter or None if the value isnt stored
		:rtype: Any | None
		"""
		# create key
		key = (device, parameter)
		if key in self._cache:
			# return current value
			return self._cache[key]
		else:
			return None

	def set_value(self, device: str, parameter: str, value: Any) -> None:
		"""
		Sets the value of the given parameter in the cache.
		If the value does not exist, it will be created.

		:param device: Device name
		:type device: str
		:param parameter: Parameter name
		:type parameter: str
		:param value: Value of the parameter to be set
		:type value: Any
		:return: None
		:rtype: None
		"""
		# generate key
		key = (device, parameter)
		if key in self._cache:
			# get the current value
			cached_value = self._cache[key]
			# check if the values are the same
			is_same = (cached_value == value)
			if not is_same:
				# only update cache if the value is different
				self._cache[key] = value
				self.valueChanged.emit(value)
				return
			else:
				# pass request otherwise
				pass
		else:
			# create value if it does not exists
			self._cache[key] = value
			self.valueChanged.emit(value)
			return

	def save_cache(self) -> Dict[tuple, Any]:
		# return copy of the cache
		return self._cache.copy()

	def load_preset(self, cache: Dict[tuple, Any]) -> None:
		# copy the preset into the cache
		for key, value in cache.items():
			# use the set method to send the update signal
			self.set_value(key[0], key[1], value)
		return



