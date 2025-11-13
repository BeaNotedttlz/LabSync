"""
Module defining the Parameter descriptor for device parameters.
@author: Merlin Schmidt
@date: 2024-06-10
@file: Devices/Descriptors.py
@note: Use at your own risk.
"""

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
		"""
		if isinstance(value, self.type):
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