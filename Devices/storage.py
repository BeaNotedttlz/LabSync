## class for saving parameters of devices ##
class ParameterStorage():
	def __init__(self) -> None:
		# create parameter dict and listener dict #
		self.parameter = {}
		self.listeners = {}

	# Function for adding parameter with inital value (mostly to set storage type e.g. float) #
	def _add_parameter(self, device_name: str, parameter_name: str, init_value) -> None:
		# create key and check if key already exists #
		key = (device_name, parameter_name)
		if key not in self.parameter:
			self.parameter[key] = init_value
		else:
			# return AttributeError if key already exists #
			raise AttributeError(f"Key: {key} already exists!")

	# Function for setting parameter a different value #
	def _set_parameter(self, device_name: str, parameter_name: str, val) -> None:
		# create key and check if key exists #
		key = (device_name, parameter_name)
		if key in self.parameter:
			self.parameter[key] = val
			# notify listeners that a value has changed #
			#self._notify_listener(device_name, val, parameter_name)
		else:
			# return AttributeError if key doesnt exist #
			raise AttributeError(f"Key: {key} not in saved paramters!")

	# Function of getting value of a specific parameter #
	def _get_parameter(self, device_name: str, parameter_name: str) -> str:
		# create key and check if key exists #
		key = (device_name, parameter_name)
		if key in self.parameter:
			return self.parameter[key]
		else:
			# return AttributeError if key doesnt exist #
			raise AttributeError(f"Key: {key} not in saved paramters!")

	# Function for reading all parameters of a device #
	def _get_all_parameters(self, device_name: str) -> dict:
		device_parameters = {}
		for (device, parameter), value in self.parameter.items():
			if device == device_name:
				device_parameters[parameter] = value

		return device_parameters

	# Function for adding listener to parameter #
	def _add_listener(self, device_name: str, receiver, listener: str, parameter_name: str="None") -> None:
		# create key and check if key exists #
		key = (device_name, parameter_name)
		if key in self.listeners:
			self.listeners[key].append([receiver, listener])
		else:
			# if not add new key and add listener #
			self.listeners[key] = []
			self.listeners[key].append([receiver, listener])

	# Function for notifing listeners if value has changed #
	def _notify_listener(self, device_name: str, value, parameter_name: str) -> None:
		# create key and check if key exists #
		key = (device_name, parameter_name)
		if key in self.listeners:
			for obj, method in self.listeners[key]:
				getattr(obj, method)(parameter_name, value)

		# Fallback if no specific parameter was set, but all parameters #
		elif (device_name, "None") in self.listeners:
			for obj, method in self.listeners[device_name, "None"]:
				getattr(obj, method)(parameter_name, value)

		# if neither, return AttributeError #
		else:
			raise AttributeError(f"Key: {key} not saved as listener!")



