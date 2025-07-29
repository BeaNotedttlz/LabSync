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
		if isinstance(value, tuple):
			old = self._data[key][value[0]]
			if old != value[1]:
				self._data[key][value[0]] = value[1]
				for cb in self._listeners.get(key, []):
					cb(**{param_name: value})
				return None

		old = self._data[key]
		# only update parameter if changed #
		if old  != value:
			self._data[key] = value
			# notify all listeners of parameter #
			for cb in self._listeners.get(key, []):
				cb(**{param_name: value})
		return None

	def get_all_parameters(self) -> dict:
		return self._data

	def load_data_dict(self, new_data) -> None:
		if self._data.keys() != new_data.keys():
			raise KeyError
		else:
			# self._data = new_data
			keys = new_data.keys()
			for key in keys:
				if key[1] in ["current_position", "error_code", "firmware", "specs", "max_power", "emission", "output"]:
					continue
				self.set(key[0], key[1], new_data[key])
			return None

	# Function for adding listener #
	def add_listener(self, device_name: str, param_name: str, callback) -> None:
		if isinstance(param_name, tuple):
			for param in param_name:
				key = (device_name, param)
				self._listeners.setdefault(key, []).append(callback)
		else:
			key = (device_name, param_name)
			# append callback methods to list of key #
			self._listeners.setdefault(key, []).append(callback)
