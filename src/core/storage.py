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
			# --- FIX IS HERE ---
			# Worker returns (Value, Channel), so we unpack in that order
			actual_value, channel_idx = value

			# create nested dict of the key if not exists
			if key not in self._cache or not isinstance(self._cache[key], dict):
				self._cache[key] = {}

			current_channel_val = self._cache[key].get(channel_idx, None)

			if current_channel_val != actual_value:
				self._cache[key][channel_idx] = actual_value
				if emit_signal:
					# Ensure the signal matches the cache structure: (Channel, Value)
					# NOTE: Check if your UI expects (Channel, Value) or (Value, Channel).
					# Usually UI slots prefer (Channel, Value) to index lists easily.
					self.valueChanged.emit(device_id, parameter, (channel_idx, actual_value))

		else:
			# Standard scalar handling
			if self._cache.get(key, None) != value:
				self._cache[key] = value
				if emit_signal:
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
		success, error = LabFileParser.save(filepath, self._cache)

		if not success:
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
		new_data, error = LabFileParser.load(filepath)

		if not new_data:
			raise IOError(f"Could not load .lab file from {filepath}") from error

		for (device, parameter), value in new_data.items():
			if isinstance(value, dict):
				for ch_idx, ch_val in value.items():
					self.set_value(device, parameter, (ch_idx, ch_val), emit_signal=True)
			else:
				self.set_value(device, parameter, value, emit_signal=True)
		return


