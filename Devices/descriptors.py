class Param():
	def __init__(self, name, default) -> None:
		self.name = name
		self.default = default

	def __set_name__(self, owner, attr_name):
		self.attr_name = attr_name

	def __get__(self, obj, objtype=None):
		if obj is None:
			return self
		return obj._storage.get(obj.name, self.name)

	def __set__(self, obj, value):
		obj._storage.set(obj.name, self.name, value)
