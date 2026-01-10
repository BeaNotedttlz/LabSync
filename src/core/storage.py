"""
Module for storing device parameters dynamically on runtime. This will then be used to save and load a preset.
@author: Merlin Schmidt
@date: 2025-02-12
@file: src/core/storage.py
@note:
"""

from typing import Any, Dict, Tuple
from PySide6.QtCore import QObject, Signal
from src.core.lab_parser import LabFileParser

class InstrumentCache(QObject):

	valueChanged = Signal(str, str, object)

	def __init__(self, parent=None) -> None:
		"""Constructor method
		"""
		super().__init__(parent)
		# Parameter storage cache, dynamically created on runtime
		self._cache: Dict[Tuple[str, str], Any] = {}
		# Key is tuple: (device_id, parameter_name)
		return

	def get_value(self, device_id: str, parameter: str) -> Any | None:
		"""
		Get the value of a device and parameter from the cache.
		:param device_id: Device ID
		:type device_id: str
		:param parameter: Parameter name
		:type parameter: str
		:return: The value in the cache for the given key or None if not found
		:rtype: Any | None
		"""
		key = (device_id, parameter)
		return self._cache.get(key, None)

	def set_value(self, device_id: str, parameter: str, value: Any, emit_signal: bool = False) -> None:
		key = (device_id, parameter)

		# check the value is a tuple -> nested dict for the frequency generator
		if isinstance(value, tuple):
			# Worker returns (Value, Channel) -> unpack into actual value and channel index
			# TODO: This can be refactored to (channel, value) for better indexing.
			actual_value, channel_idx = value

			# create nested dict of the key if not exists
			if key not in self._cache or not isinstance(self._cache[key], dict):
				self._cache[key] = {}

			# Get the current value for this channel
			current_channel_val = self._cache[key].get(channel_idx, None)

			# Update only if the value changed
			if current_channel_val != actual_value:
				# Store new value
				self._cache[key][channel_idx] = actual_value
				if emit_signal:
					# Only emit the changed signal if specified
					self.valueChanged.emit(device_id, parameter, (channel_idx, actual_value))

		else:
			# Standard scalar handling
			if self._cache.get(key, None) != value:
				# Update only if the value changed
				self._cache[key] = value
				if emit_signal:
					# Only emit the changed signal if specified
					self.valueChanged.emit(device_id, parameter, value)

		return

	def save_cache(self, filepath: str) -> None:
		"""
		Save the current device states to a custom .lab file.
		This logic is intentionally exported to the InstrumentCache class to allow easy access from other modules.
		:param filepath: Filepath to save the .lab file
		:type filepath: str
		:return: None
		"""
		# Use LabFileParser to save the current cache
		# This does not create an instance of LabFileParser, just uses its static methods
		success, error = LabFileParser.save(filepath, self._cache)

		if not success:
			# Raise and IOError if saving failed
			raise IOError(f"Could not save .lab file to {filepath}") from error
		return

	def load_cache(self, filepath: str) -> None:
		"""
		Load device states from a custom .lab file.
		This logic is intentionally exported to the InstrumentCache class to allow easy access from other modules.
		:param filepath: Filepath to load the .lab file from
		:type filepath: str
		:return: None
		"""
		# Use LabFileParser to load the .gnt file
		# This does not create an instance of LabFileParser, just uses its static methods
		new_data, error = LabFileParser.load(filepath)

		if not new_data:
			# Raise and IOError if loading failed
			raise IOError(f"Could not load .lab file from {filepath}") from error

		for (device, parameter), value in new_data.items():
			# Check if the value is a dict (for nested parameters)
			# For all parameters the emit_signal flag will be set to update the UI with the new values
			if isinstance(value, dict):
				# Iterate through each channel and set the value
				for ch_idx, ch_val in value.items():
					self.set_value(device, parameter, (ch_idx, ch_val), emit_signal=True)
			else:
				# Standard value setting
				self.set_value(device, parameter, value, emit_signal=True)
		return


