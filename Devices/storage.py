class ParameterStorage():
	def __init__(self):
		# Dict for saving values to keys #
		self._data = {}
		# Dict for saving listener callback methods #
		self._listeners = {}

	# Function for adding parameter to storage #
	def add_parameter(self, device_name: str, param_name: str, inital_value):
		# generate key #
		key = (device_name, param_name)
		if key in self._data:
			# check if key already exists -> debug only #
			raise KeyError(f"key {key} already registered")
		# Add key and inital value #
		self._data[key] = inital_value

	# Function for getting value from storage #
	def get(self, device_name: str, param_name: str):
		# generate key #
		key = (device_name, param_name)
		return self._data[key]

	# Function for setting value in storage #
	def set(self, device_name: str, param_name: str, value):
		# generate Key #
		key = (device_name, param_name)
		# get old value #
		old = self._data.get(key)

		if old != value:
			# only update on value change #
			self._data[key] = value
			# notify all listeners of param #
			for cb in self._listeners.get(key, []):
				cb(param_name, value)

	# Function for adding listeners to param #
	def add_listener(self, device_name: str, param_name: str, callback):
		# Generate key #
		key = ( device_name, param_name)
		# add callback to list of key #
		self._listeners.setdefault(key, []).append(callback)
