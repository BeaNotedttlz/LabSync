class ParameterStorage():
	def __init__(self):
		self._data = {}
		self._listeners = {}

	def add_parameter(self, device_name: str, param_name: str, inital_value):
		key = (device_name, param_name)
		if key in self._data:
			raise KeyError(f"key {key} already registered")
		self._data[key] = inital_value

	def get(self, device_name: str, param_name: str):
		return self._data[(device_name, param_name)]

	def set(self, device_name: str, param_name: str, value):
		key = (device_name, param_name)
		old = self._data.get(key)
		if old != value:
			self._data[key] = value
			for cb in self._listeners.get(key, []):
				cb(param_name, value)

	def add_listener(self, device_name: str, param_name: str, callback):
		key = ( device_name, param_name)
		self._listeners.setdefault(key, []).append(callback)
