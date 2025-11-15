"""
Module for proving general utility classes.
@autor: Merlin Schmidt
@date: 2025-15-10
@file: scr/core/utils.py
"""

from PySide6.QtCore import QObject
import os, platform, subprocess, json, tempfile
from typing import Any

class SignalHandler(QObject):
	"""
	SignalHandler class for handling general PySide6 Signals and Slots.

	:return: None
	:rtype: None
	"""
	def __init__(self) -> None:
		"""Constructor method
		"""
		# inherit QObject __init__
		super().__init__()

	@staticmethod
	def route(sender, signal_name, receiver, slot) -> None:
		"""
		Routing method for connecting Signals to Slots.
		This also allows for the connection of signals and slots from different instances.

		:param sender: Signal sender instance
		:type sender: Instance
		:param signal_name: Name of the signal from the sender instance
		:type signal_name: str
		:param receiver: Slot receiver instance
		:type: receiver: Instance
		:param slot: Name of the slot from the receiver instance
		:type slot: str
		:return: None
		:rtype: None
		"""
		signal = getattr(sender, signal_name)
		slot = getattr(receiver, slot)
		signal.connect(slot)
		return None

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
		# get current operating system from user
		self.system = platform.system()
		# create folder and settings paths
		# Generally the settings path is hidden
		self.folder = os.path.join(file_path, "settings" if self.system == "Windows" else ".settings")
		self.settings_path = os.path.join(self.folder, self.filename)
		os.makedirs(self.folder, exist_ok=True)

		# Hide settings path for Windows operating system
		if self.system == "Windows":
			try:
				subprocess.run(["attrib", "+H", self.folder], check=True)
			except Exception:
				pass

		# create settings file
		# This is usually only needed on the first run
		_ = self._ensure_hidden_settings()

	def _ensure_hidden_settings(self) -> dict:
		"""
		Ensure there is a hidden settings file in the application dir

		:return: The contents of the settings file. Either the default settings on error or the actually read data
		:rtype: dict
		"""
		# check if the hidden settings file exists
		if not os.path.exists(self.settings_path):
			# if not dump default settings
			with open(self.settings_path, "w", encoding="utf-8") as f:
				json.dump(self.default_settings, f, indent=2)
		try:
			# open settings file and read data
			with open(self.settings_path, "r", encoding="utf-8") as f:
				data = json.load(f)
			# return read data
			return data
		except (json.JSONDecodeError, OSError):
			# on error return default data
			return self.default_settings.copy()

	def read_settings(self, setting: str) -> Any:
		"""
		Read a specific setting.

		:param setting: Desired setting to retrieve value
		:type setting: str
		:return: The value of the desired setting
		:rtype: Any
		"""
		# get all settings
		settings = self._ensure_hidden_settings()
		# return only [setting]
		value = settings[setting]
		return value

	def edit_settings(self, setting_name: str, value: Any) -> dict:
		"""
		Edit a specific setting and save to file.

		:param setting_name: Desired setting to edit
		:type setting_name: str
		:param value: New value
		:type value: Any
		:return: The new contents of the settings file
		:rtype: dict
		"""
		# get current settings and current value
		settings = self._ensure_hidden_settings()
		settings[setting_name] = value

		# Atomic write
		fd, tmp_path = tempfile.mkstemp(dir=self.folder, prefix="settings_", text=True)
		try:
			with os.fdopen(fd, "w", encoding="utf-8") as f:
				json.dump(settings, f, indent=2)
				f.flush()
				os.fsync(f.fileno())
			os.replace(tmp_path, self.settings_path)
		finally:
			if os.path.exists(tmp_path):
				try:
					os.remove(tmp_path)
				except OSError:
					pass

		return settings

	def read_port_file(self) -> dict:
		"""
		Read the default port file.

		:return: The contents of the port file
		:rtype: dict
		"""
		# read port file and return contents
		ports_dir = os.path.join(self.cwd, "files", "ports", "default_ports.json")
		with open(ports_dir, "r", encoding="utf-8") as f:
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
		ports_dir = os.path.join(self.cwd, "files", "ports", "default_ports.json")
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