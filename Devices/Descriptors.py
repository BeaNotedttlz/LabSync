'''
Descriptor class

This class handles what happens when a attribute is called or set
this generalizes the setting and getting of values from the parameter storage class
e.g.:
self.frequency -> __get__
self.frequency = 10.0 -> __set__
'''
class Parameter:
	def __init__(self, name: str, method = None, default=None, type=None):
		self.name = name
		self.method = method
		self.default = default
		self.type = type

	def __set_name__(self, owner, attr_name):
		self.attr_name = attr_name

	def __get__(self, obj, obj_type=None):
		if obj_type is None:
			return self
		else:
			return obj.storage.get_parameter(obj.name, self.name)

	def __set__(self, obj, value):
		if isinstance(value, self.type):
			old_value = obj.storage.get_parameter(obj.name, self.name)
			if old_value != value:
				if self.method is not None:
					getattr(obj, self.method)(value)
				obj.storage.set_parameter(obj.name, self.name, value)
		elif isinstance(value, tuple):
			old_dict = obj.storage.get_parameter(obj.name, self.name)
			idx = value[0]
			value = value[1]

			if old_dict[idx] != value:
				if self.method is not None:
					getattr(obj, self.method)(idx, value)
				old_dict[idx] = value
				obj.storage.set_parameter(obj.name, self.name, old_dict)
		else:
			raise ValueError(f"Expected type {self.type} for parameter {self.name}, got {type(value)} instead.")