"""
Module for storing device parameters and their respective values.
The values are generally stored dynamically in dictionaries. This is generally only called by the Param descriptor class.
Additionally listeners for update signals are supported
@autor: Merlin Schmidt
@date: 2024-06-10
@file: Devices/Storage.py
@note: Use at your own risk.
"""
from collections.abc import Iterable
from typing import Any

class ParameterStorage:
	"""
	ParameterStorage class for storing device parameters.

	:return: None
	:rtype: None
	"""
	def __init__(self):
		# initialize storage and listener dictionaries
		self._storage = {}
		self._listeners = {}

	def new_parameter(self, device: str, parameter: str, init_value: Any=None) -> None:
		"""
		Add new parameter to the storage.

		:param device: Device name. This is mostly used to allow for multiple parameters with the same name.
		:type device: str
		:param parameter: Parameter name. This must match the Attribute name.
		:type parameter: str
		:param init_value: Initial value of the new parameter. This defaults to None
		:type init_value: None | any
		:raises KeyError: If the new parameter already exists.
		:return: None
		:rtype: None
		"""
		# generate key
		key = (device, parameter)
		if key not in self._storage:
			# add new parameter to storage
			self._storage[key] = init_value
			return None
		else:
			# raise error if key already exists
			raise KeyError(f"Parameter {parameter} for device {device} already exists.")

	def new_listener(self, device: str, parameter: str, callback) -> None:
		"""
		Add new listener to parameter.

		:param device: Device name. This is mostly used to allow for multiple parameters with the same name.
		:type device: str
		:param parameter: Parameter name. This must match the Attribute name.
		:type parameter: str
		:param callback: Callback method to call if the parameter changed.
		:type callback: callback
		:raises KeyError: If the listener already exists
		:return: None
		:rtype: None
		"""
		# generate key
		key = (device, parameter)
		if key not in self._listeners:
			# for adding multiple listeners at once
			# they can be passed as a iterable
			if isinstance(callback, Iterable):
				for cb in callback:
					# add listener and callback method
					self._listeners.setdefault(key, []).append(cb)
			else:
				# add listener and callback method
				self._listeners.setdefault(key, []).append(callback)

	def get_parameter(self, device: str, parameter: str) -> Any:
		"""
		Get parameter value from the storage.

		:param device: Device name. This is mostly used to allow for multiple parameters with the same name.
		:type device: str
		:param parameter: Parameter name. This must match the Attribute name.
		:type parameter: str
		:raises KeyError: If the parameter does not exist.
		:return: Returns the current value of the selected parameter
		:rtype: Any
		"""
		# generate key
		key = (device, parameter)
		if key in self._storage:
			# return value if key exists
			return self._storage[key]
		else:
			raise KeyError(f"Parameter {parameter} for device {device} does not exist.")

	def set_parameter(self, device: str, parameter: str, value: Any) -> None:
		"""
		Set new parameter value in the storage.

		:param device: Device name. This is mostly used to allow for multiple parameters with the same name.
		:type device: str
		:param parameter: Parameter name. This must match the Attribute name.
		:type parameter: str
		:param value: New value of the parameter
		:type value: Any
		:raises KeyError: If the parameter does not exist.
		:return: None
		:rtype: None
		"""
		# generate key
		key = (device, parameter)
		if key in self._storage:
			# update value if key exists
			self._storage[key] = value
			# notify listeners of change
			self._notify_listeners(device, parameter, value)
			return None
		else:
			raise KeyError(f"Parameter {parameter} for device {device} does not exist.")

	def _notify_listeners(self, device: str, parameter: str, value: Any) -> None:
		"""


		:param device: Device name. This is mostly used to allow for multiple parameters with the same name.
		:type device: str
		:param parameter: Parameter name. This must match the Attribute name.
		:type parameter: str
		:param value: New value of the parameter
		:type value: Any
		:return: None
		:rtype: None
		"""
		key = (device, parameter)
		if key in self._listeners:
			for callback in self._listeners[key]:
				callback(**{parameter: value})
			return None
		else:
			return None

	def get_all(self) -> dict:
		"""
		Get the full storage dictionary. This is used to save the parameters in the LabSync application

		:return: The storage dictionary
		:rtype: dict
		"""
		return self._storage

	def load_all(self, parameters: dict) -> None:
		"""
		Load the full storage dictionary. This is used to load the parameters in the LabSync application.
		Since just loading the dictionary from the file can lead to errors and unexpected behaviour,
		each key is loaded individually. However this is less efficient.

		:param parameters: The full parameter storage dictionary
		:type parameters: dict
		:raises KeyError: If unsupported parameter is being loaded
		:return: None
		:rtype: None
		"""
		for key in parameters.keys():
			if key in self._storage:
				self._storage[key] = parameters[key]
				self._notify_listeners(key[0], key[1], parameters[key])
			else:
				raise KeyError(f"Parameter {key} does not exist in storage.")

