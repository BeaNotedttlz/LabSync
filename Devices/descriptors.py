'''
Descriptor class

This class handles what happens when a attribute is called or set
this generalizes the setting and getting of values from the parameter storage class
e.g.:
self.frequency -> __get__
self.frequency = 10.0 -> __set__
'''
class Param():
	def __init__(self, name: str, default, type) -> None:
		# set name and default value #
		self.name = name
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

	def __set__(self, obj, value):
		# set new value in storage
		if isinstance(value, self.type):
			obj.storage.set(obj.name, self.name, value)
		raise ValueError
