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
		self._listeners = {}

	def new_parameter(self, device: str, parameter: str, init_value=None):
		key = (device, parameter)
		if key not in self._storage:
			self._storage[key] = init_value
		else:
			raise KeyError(f"Parameter {parameter} for device {device} already exists.")

	def new_listener(self, device: str, parameter: str, callback):
		key = (device, parameter)
		if key not in self._listeners:
			if isinstance(callback, Iterable):
				for cb in callback:
					self._listeners.setdefault(key, []).append(cb)
			else:
				self._listeners.setdefault(key, []).append(callback)

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
		if key in self._listeners:
			for callback in self._listeners[key]:
				callback(**{parameter: value})
		else:
			pass
			#raise KeyError(f"No listeners for parameter {parameter} of device {device}.")

	def get_all(self) -> dict:
		return self._storage

	def load_all(self, parameters: dict) -> None:
		for key in parameters.keys():
			if key in self._storage:
				self._storage[key] = parameters[key]
				self._notify_listeners(key[0], key[1], parameters[key])
			else:
				raise KeyError(f"Parameter {key} does not exist in storage.")

