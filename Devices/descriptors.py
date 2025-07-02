'''
Descriptor class

This class handles what happens when a attribute is called or set
this generalizes the setting and getting of values from the parameter storage class
e.g.:
self.frequency -> __get__
self.frequency = 10.0 -> __set__
'''


class Param():
	def __init__(self, name: str, method, default, type) -> None:
		# set name and default value #
		self.name = name
		self.method = method
		self.default = default
		self.type = type

	def __set_name__(self, owner, attr_name):
		# is called when accesing param #
		self.attr_name = attr_name

	def __get__(self, obj, objtype=None):
		if obj is None:
			# return descriptor on class call
			return self
		# return storage value on attribute call #
		return obj.storage.get(obj.name, self.name)

	def __set__(self, obj, value=None):
		# set new value in storage
		if isinstance(value, self.type):
			current = obj.storage.get(obj.name, self.name)
			if current == value:
				return None

			if self.method is not None:
				getattr(obj, self.method)(value)
			return obj.storage.set(obj.name, self.name, value)

		if self.type is dict and isinstance(value, tuple):
			key = value[0]
			value = value[1]
			current_dict = obj.storage.get(obj.name, self.name)
			if current_dict[key] == value:
				return None

			current_dict[key] = value
			if self.method is not None:
				getattr(obj, self.method)(key, value)
			return obj.storage.set(obj.name, self.name, current_dict)
		raise ValueError