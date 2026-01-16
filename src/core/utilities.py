"""
Module for proving general utility classes.
@autor: Merlin Schmidt
@date: 2025-15-10
@file: scr/core/utils.py
"""
import os, json, tempfile
from typing import Any
import math

# Checking files #
class FilesUtils:
	"""
	FileUtils class for handling general file storage operations.
	This includes the settings file and the device ports.

	:param file_path: general file path of all save files. This is usually the dir of the __main__ file.
	:type file_path: str
	:param file_name: Files names to create. This defaults to 'settings.json' for the settings file
	:type file_name: str
	:return: None
	:rtype: None
	"""
	def __init__(self, file_path: str, file_name: str = "settings.json") -> None:
		"""Constructor method
		"""
		# default settings parameters
		self.default_settings = {
			"version": "2.5.2",
			"username": "",
			"debug_mode": False,
		}
		self.default_ports = {
			"EcoVario": ["COM0", 9600],
			"Laser1": ["COM1", 500000],
			"Laser2": ["COM2", 500000],
			"TGA1244": ["COM3", 9600],
			"FSV3000": ["COM4", None]
		}
		# save file name to self
		self.filename = file_name
		# create folder and settings paths
		self.ports_path = os.path.join(file_path, "ports", "default_ports.json")
		self.ports_folder = os.path.join(file_path, "ports")
		os.makedirs(self.ports_folder, exist_ok=True)
		self.folder = os.path.join(file_path, "settings")
		self.settings_path = os.path.join(file_path, "settings", self.filename)
		os.makedirs(self.folder, exist_ok=True)

		# Read Settings but discard result
		# this ensures that the settings file is created if it does not exist
		_ = self.read_settings()
		return

	def read_settings(self) -> dict | None:
		"""
		Read the settings file and return a specific settin.
		:return: The settings dictionary, Returns the default on reading error and None otherwise
		:rtype: dict | None
		"""
		# Create settings file if it does not exist
		if not os.path.exists(self.settings_path):
			with open(self.settings_path, "w", encoding="utf-8") as f:
				# dump default settings
				json.dump(self.default_settings, f, indent=4)

		try:
			# Try to read settings file
			with open(self.settings_path, "r", encoding="utf-8") as f:
				data = json.load(f)
			# Return the data
			return data
		except (json.decoder.JSONDecodeError, OSError):
			# On Error return default settings
			# TODO: This should probably notify the user that their settings file was corrupted
			return self.default_settings.copy()
		except KeyError:
			# Otherwise return None
			return None

	def edit_settings(self, setting: str, value: Any) -> None:
		"""
		Edit a specific setting and save it to the file.

		:param setting: Setting to edit
		:type setting: str
		:param value: Value to save
		:type value: Any
		:return: None
		:rtype: None
		"""
		# Read the current settigns
		data = self.read_settings()
		# Edit the specific setting
		data[setting] = value

		# Atomic write
		fd, tmp_path = tempfile.mkstemp(dir=self.folder, prefix="settings_", text=True)
		try:
			with os.fdopen(fd, "w", encoding="utf-8") as f:
				# Create temp file and write data
				json.dump(data, f, indent=2)
				f.flush()
				os.fsync(f.fileno())
			# Replace original file with temp file
			os.replace(tmp_path, self.settings_path)
		except (json.decoder.JSONDecodeError, OSError):
			# TODO: PortSetError?
			raise PortSetError
		finally:
			# Remove temp file if it still exists
			if os.path.exists(tmp_path):
				try:
					os.remove(tmp_path)
				except OSError:
					pass
		return

	def read_port_file(self) -> dict:
		"""
		Read the default port file.

		:return: The contents of the port file
		:rtype: dict
		"""
		# read port file and return contents

		try:
			# Try to read ports file
			with open(self.ports_path, "r", encoding="utf-8") as f:
				ports = json.load(f)
			return ports
		except (json.decoder.JSONDecodeError, OSError):
			# On error recreate default ports file and return default ports
			# TODO: This should probably notify the user that their ports file was corrupted
			with open(self.ports_path, "w", encoding="utf-8") as f:
				json.dump(self.default_ports.copy(), f, indent=2)
				f.close()
			return self.default_ports.copy()

	def set_ports(self, stage: list, laser1: list, laser2: list, freq_gen: list, fsv: list, set_def:bool=False) -> None:


		if set_def:
			# For setting default ports, just overwrite with default ports
			# TODO: Why do I need this?
			with open(self.ports_path, "w", encoding="utf-8") as f:
				json.dump(self.default_ports.copy(), f, indent=2)
				f.close()
			return
		# Create new ports dictionary
		ports = {
			"EcoVario": stage,
			"Laser1": laser1,
			"Laser2": laser2,
			"TGA1244": freq_gen,
			"FSV3000": fsv
		}
		# Atomic write
		fd, tmp_path = tempfile.mkstemp(dir=self.ports_folder, prefix="ports_", text=True)
		try:
			with os.fdopen(fd, "w", encoding="utf-8") as f:
				json.dump(ports, f, indent=2)
				f.flush()
				os.fsync(f.fileno())
			os.replace(tmp_path, self.ports_path)
		except (json.decoder.JSONDecodeError, OSError):
			raise PortSetError
		finally:
			if os.path.exists(tmp_path):
				try:
					os.remove(tmp_path)
				except OSError:
					pass
		return

# Exception classes #
class ParameterNotSetError(Exception):
	def __init__(self, message) -> None:
		self.message = message
		super().__init__(self.message)
	def __str__(self) -> str:
		return self.message

class DeviceParameterError(Exception):
	def __init__(self, message) -> None:
		self.message = message
		super().__init__(self.message)
	def __str__(self) -> str:
		return self.message

class ParameterOutOfRangeError(Exception):
	def __init__(self, message) -> None:
		self.message = message
		super().__init__(self.message)
	def __str__(self) -> str:
		return self.message

class UIParameterError(Exception):
	def __init__(self, message) -> None:
		self.message = message
		super().__init__(self.message)

	def __str__(self) -> str:
		return self.message

class PortSetError(Exception):
	def __init__(self, message) -> None:
		self.message = message
		super().__init__(self.message)

	def __str__(self) -> str:
		return self.message

class DeviceConnectionError(Exception):
	def __init__(self, message) -> None:
		self.message = message
		super().__init__(self.message)

	def __str__(self) -> str:
		return self.message

class DeviceTaskError(Exception):
	def __init__(self, message) -> None:
		self.message = message
		super().__init__(self.message)

	def __str__(self) -> str:
		return self.message

class ValueHandler:
	"""
	Utility class for handling value comparisons.
	THis is mainly used for checking if two float values are different within a certain tolerance.
	"""
	@staticmethod
	def check_values(value_1: float, value_2: float) -> bool:
		"""
		Check if two values are different, considering float tolerance.
		:param value_1: First value to check
		:type value_1: float
		:param value_2: Second value to check
		:type value_2: float
		:return: True if values are different, False otherwise
		:rtype: bool
		"""
		if value_1 is None:
			# If value 1 is None, consider them different
			return True

		if isinstance(value_2, float) and isinstance(value_1, float):
			# For float values, use isclose with a tolerance
			# Return True if they are not close
			return not math.isclose(value_1, value_2, abs_tol=1e-4)

		# For other types, use direct comparison
		return value_1 != value_2