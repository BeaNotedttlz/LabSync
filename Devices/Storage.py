'''
Parameter storage class

This class handles the storage of values in a dictionary
each method is called by the descriptor class "Param"
Aditional method for adding callback methods to send update signal
'''
from collections.abc import Iterable
class ParameterStorage:

	def __init__(self):
		self._storage = {}
		self._listners = {}

	def new_parameter(self, device: str, parameter: str, init_value=None):
		key = (device, parameter)
		if key not in self._storage:
			self._storage[key] = init_value
		else:
			raise KeyError(f"Parameter {parameter} for device {device} already exists.")

	def new_listener(self, device: str, parameter: str, callback):
		key = (device, parameter)
		if key not in self._listners:
			if isinstance(callback, Iterable):
				for cb in callback:
					self._listners.setdefault(cb, []).append(cb)
			else:
				self._listners.setdefault(key, []).append(callback)

	def get_parameter(self, device: str, parameter: str):
		key = (device, parameter)
		if key in self._storage:
			return self._storage[key]
		else:
			raise KeyError(f"Parameter {parameter} for device {device} does not exist.")

	def set_parameter(self, device: str, parameter: str, value):
		key = (device, parameter)
		if key in self._storage:
			self._storage[key] = value
			self._notify_listeners(device, parameter, value)
		else:
			raise KeyError(f"Parameter {parameter} for device {device} does not exist.")

	def _notify_listeners(self, device, parameter, value):
		key = (device, parameter)
		if key in self._listners:
			for callback in self._listners[key]:
				callback(value)
		else:
			raise KeyError(f"No listeners for parameter {parameter} of device {device}.")



