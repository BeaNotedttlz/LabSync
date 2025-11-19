"""
Module for proving general utility classes.
@autor: Merlin Schmidt
@date: 2025-15-10
@file: scr/core/utils.py
"""


import os, platform, subprocess, json, tempfile
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
		# save file name to self
		self.filename = file_name
		# create folder and settings paths
		self.ports_path = os.path.join(file_path, "ports", "default_ports.json")
		self.folder = os.path.join(file_path, "settings")
		self.settings_path = os.path.join(file_path, "settings", self.filename)
		os.makedirs(self.settings_path, exist_ok=True)
		return

	def read_settings(self) -> dict | None:
		"""
		Read the settings file and return a specific settin.

		:param setting: Setting want to be read
		:type setting: str
		:return: The settings dictionary, Returns the default on reading error and None otherwise
		:rtype: dict | None
		"""
		if not os.path.exists(self.settings_path):
			with open(self.settings_path, "w", encoding="utf-8") as f:
				json.dump(self.default_settings, f, indent=4)

		try:
			with open(self.settings_path, "r", encoding="utf-8") as f:
				data = json.load(f)

			return data
		except (json.decoder.JSONDecodeError, OSError):
			return self.default_settings.copy()
		except KeyError:
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
		data = self.read_settings()
		data[setting] = value

		fd, tmp_path = tempfile.mkstemp(dir=self.folder, prefix="settings_", text=True)
		try:
			with os.fdopen(fd, "w", encoding="utf-8") as f:
				json.dump(data, f, indent=2)
				f.flush()
				os.fsync(f.fileno())
			os.replace(tmp_path, self.settings_path)
		finally:
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


		with open(self.ports_path, "r", encoding="utf-8") as f:
			ports = json.load(f)
		return ports

	def set_ports(self, stage: str, TGA: str, laser1: str, laser2: str, fsv: str) -> dict:
		"""
		Update the new ports and save to ports file.

		:param stage: New stage port
		:type stage: str
		:param TGA: New TGA port
		:type TGA: str
		:param laser1: New Laser1 port
		:type laser1: str
		:param laser2: New Laser2 port
		:type laser2: str
		:param fsv: New FSV port
		:type fsv: str
		:return: The new contents of the ports file
		:rtype: dict
		"""
		# create ports dir and dict for device ports
		ports_dir = os.path.join(self.ports_path, "files", "ports", "default_ports.json")
		ports = {
			"stage": stage,
			"TGA": TGA,
			"laser1": laser1,
			"laser2": laser2,
			"fsv": fsv
		}
		# save contents to file and return new contents
		with open(ports_dir, "w", encoding="utf-8") as f:
			json.dump(ports, f, indent=2)
		return ports

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

class ValueHandler:
	@staticmethod
	def check_values(value_1: float, value_2: float) -> bool:
		if value_1 is None:
			return True

		if isinstance(value_2, float) and isinstance(value_1, float):
			return not math.isclose(value_1, value_2, abs_tol=1e-4)

		return value_1 != value_2