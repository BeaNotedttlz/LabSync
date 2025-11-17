"""
Module defining the Parameter descriptor and Parameter storage for device parameters.
The values are generally stored dynamically in dictionaries. This is generally only called by the Param descriptor class.
Additionally listeners for update signals are supported
@author: Merlin Schmidt
@date: 2025-15-10
@file: /src/core/storage.py
"""

from collections.abc import Iterable
from typing import Any, Callable
Callback = Callable[[Any], Any]

class Parameter:
	"""
	Descriptor class for device parameters.

	:param name: Name of the device parameter in storage.
	:type name: str.
	:param method: Optional method to call when parameter is set. Defaults to None
	:type method: str or None
	:param default: Default value for the parameter. Defaults to None
	:type default: any
	:param type: Expected type of the parameter value. Defaults to None
	:type type: type or None
	:return Parameter descriptor instance.
	:rtype: Parameter
	"""
	def __init__(self, name: str, method = None, default=None, type=None):
		"""Constructor method
		"""
		self.name = name
		self.method = method
		self.default = default
		self.type = type

	def __set_name__(self, owner, attr_name):
		"""
		Called when the descriptor is asgigned to an attribute in the owner class.

		:param owner: Owner class where the descriptor is assigned.
		:type owner: object
		:param attr_name: Name of the attribute in the owner class.
		:type attr_name: str
		:return: None
		:rtype: None
		"""
		self.attr_name = attr_name

	def __get__(self, obj, obj_type=None):
		"""
		Gets the parameter value from the storage.

		:param obj: owner object instance.
		:type obj: object
		:param obj_type: owner class type.
		:type obj_type: type
		:return: self object or parameter value from storage.
		:rtype: any
		"""
		# if accessed through class, return the descriptor itself
		if obj_type is None:
			return self
		else:
			# accessed through instance, return the parameter value from storage
			return obj.storage.get_parameter(obj.name, self.name)

	def __set__(self, obj, value):
		"""
		Sets the parameter value in the storage.

		:param obj: owner object instance.
		:type obj: object
		:param value: parameter value to set.
		:type value: any
		:raises ValueError: if the value type does not match the expected type.
		:return: None
		:rtype: None
		"""
		if isinstance(value, self.type) or isinstance(value, None):
			# single value assignment if types match
			old_value = obj.storage.get_parameter(obj.name, self.name)
			if old_value != value:
				# only update value on change
				if self.method is not None:
					# call method on owner object if specified
					getattr(obj, self.method)(value)
				# update storage
				obj.storage.set_parameter(obj.name, self.name, value)
		elif isinstance(value, tuple):
			# tuple assignment for indexed parameters
			old_dict = obj.storage.get_parameter(obj.name, self.name)
			idx = value[0]
			value = value[1]

			if old_dict[idx] != value:
				# only update value on change
				if self.method is not None:
					# call method on owner object if specified
					getattr(obj, self.method)(idx, value)
				# update storage
				old_dict[idx] = value
				obj.storage.set_parameter(obj.name, self.name, old_dict)
		else:
			# type mismatch
			raise ValueError(f"Expected type {self.type} for parameter {self.name}, got {type(value)} instead.")



class ParameterStorage:
	"""
	ParameterStorage class for saving and handling device parameters.

	:return: None
	:rtype: None
	"""
	def __ini__(self) -> None:
		# initialize storage and listener dicts
		self.__storage = dict()
		self.__listeners = dict()

	def new_parameter(self, device: str, name: str, init_value: Any=None) -> None:
		"""
		Add new parameter to the storage.

		:param device: Device name. This is mostly used to allow for multiple parameters with the same name.
		:type device: str
		:param name: Parameter name. This must match the Attribute name.
		:type name: str
		:param init_value: Initial value of the new parameter. This defaults to None
		:type init_value: None | any
		:raises KeyError: If the new parameter already exists.
		:return: None
		:rtype: None
		"""
		# generate key
		key = (device, name)
		if key not in self.__storage:
			# add new parameter to storage
			self.__storage[key] = init_value
			return None
		else:
			raise KeyError(f"Parameter {name} for device {device} already exists.")

	def new_listener(self, device: str, name: str, callback: Callback) -> None:
		"""
		Add new listener to parameter.

		:param device: Device name. This is mostly used to allow for multiple parameters with the same name.
		:type device: str
		:param name: Parameter name. This must match the Attribute name.
		:type name: str
		:param callback: Callback method to call if the parameter changed.
		:type callback: callback
		:raises KeyError: If the listener already exists
		:return: None
		:rtype: None
		"""
		# generate key
		key = (device, name)
		if key not in self.__listeners:
			# for adding mutiple liestners at once
			# they can be passes as an iterable
			if isinstance(callback, Iterable):
				for cb in callback:
					self.__listeners.setdefault(key, []).append(cb)
			else:
				self.__listeners.setdefault(key, []).append(callback)

	def get_parameter(self, device: str, name: str) -> Any:
		"""
		Get parameter value from the storage.

		:param device: Device name. This is mostly used to allow for multiple parameters with the same name.
		:type device: str
		:param name: Parameter name. This must match the Attribute name.
		:type name: str
		:raises KeyError: If the parameter does not exist.
		:return: Returns the current value of the selected parameter
		:rtype: Any
		"""
		# generate key
		key = (device, name)
		if key in self.__storage:
			return self.__storage[key]
		else:
			raise KeyError(f"Parameter {name} for device {device} does not exist.")

	def set_parameter(self, device: str, name: str, value: Any) -> None:
		"""
		Set new parameter value in the storage.

		:param device: Device name. This is mostly used to allow for multiple parameters with the same name.
		:type device: str
		:param name: Parameter name. This must match the Attribute name.
		:type name: str
		:param value: New value of the parameter
		:type value: Any
		:raises KeyError: If the parameter does not exist.
		:return: None
		:rtype: None
		"""
		# generate key
		key = (device, name)
		if key in self.__storage:
			# update value if key exists
			self.__storage[key] = value
			# notify listeners
			self._notify_listeners(device, name, value)
		else:
			raise KeyError(f"Parameter {name} for device {device} does not exist.")


	def _notify_listeners(self, device: str, name: str, value: Any) -> None:
		"""
		Notify listeners about changes.

		:param device: Device name. This is mostly used to allow for multiple parameters with the same name.
		:type device: str
		:param name: Parameter name. This must match the Attribute name.
		:type name: str
		:param value: New value of the parameter
		:type value: Any
		:return: None
		:rtype: None
		"""
		key = (device, name)
		if key in self.__listeners:
			for callback in self.__listeners[key]:
				callback(**{name: value})
			return None
		else:
			return None

	def get_all(self) -> dict:
		"""
		Get the full storage dictionary. This is used to save the parameters in the LabSync application

		:return: The storage dictionary
		:rtype: dict
		"""
		return self.__storage

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
			if key in self.__storage:
				self.__storage[key] = parameters[key]
				self._notify_listeners(key[0], key[1], parameters[key])
			else:
				raise KeyError(f"Parameter {key} does not exist in storage.")