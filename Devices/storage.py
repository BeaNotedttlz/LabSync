'''
Parameter storage class

This class handles the storage of values in a dictionary
each method is called by the descriptor class "Param"
Aditional method for adding callback methods to send update signal
'''
class ParameterStorage():
	def __init__(self) -> None:
		# create data and listener dict #
		self._data = {}
		self._listeners = {}

	# Function for adding parameter #
	def add_parameter(self, device_name: str, param_name: str, init_value) -> None:
		key = (device_name, param_name)
		if key in self._data:
			raise KeyError
		self._data[key] = init_value

	# Function for getting parameter #
	def get(self, device_name: str, param_name: str):
		return self._data[(device_name, param_name)]

	# Function for setting parameter #
	def set(self, device_name: str, param_name: str, value) -> None:
		key = (device_name, param_name)
		# get current value #
		old = self._data[key]

		# only update parameter if changed #
		if old  != value:
			self._data[key] = value
			# notify all listeners of parameter #
			for cb in self._listeners.get(key, []):
				cb(param_name, value)

	# Function for adding listener #
	def add_listener(self, device_name: str, param_name: str, callback) -> None:
		key = (device_name, param_name)
		# append callback methods to list of key #
		self._listeners.setdefault(key, []).append(callback)
