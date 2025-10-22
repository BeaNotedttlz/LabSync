"""
utils.py provides necessary utility functions for LabSync application.
"""

from PySide6.QtCore import QObject
import os, platform, subprocess, json, tempfile

from sympy import false


# SignalHandler class #
class SignalHandler(QObject):
	def __init__(self) -> None:
		super().__init__()

	def route(self, sender, signal_name, receiver, slot) -> None:
		signal = getattr(sender, signal_name)
		slot = getattr(receiver, slot)
		signal.connect(slot)
		return None

# Checking files #
class FilesUtils:
	def __init__(self, file_path: str, file_name: str = "settings.json"):
		self.default_settings = {
			"version": "2.5.2",
			"username": "",
			"debug_mode": False,
		}
		self.filename = file_name
		self.system = platform.system()
		self.folder = os.path.join(file_path, "settings" if self.system == "Windows" else ".settings")
		self.settings_path = os.path.join(self.folder, self.filename)
		os.makedirs(self.folder, exist_ok=True)

		if self.system == "Windows":
			try:
				subprocess.run(["attrib", "+H", self.folder], check=True)
			except Exception:
				pass

		_ = self._ensure_hidden_settings()

	def _ensure_hidden_settings(self) -> dict:
		if not os.path.exists(self.settings_path):
			with open(self.settings_path, "w", encoding="utf-8") as f:
				json.dump(self.default_settings, f, indent=2)
		try:
			with open(self.settings_path, "r", encoding="utf-8") as f:
				data = json.load(f)
			return data
		except (json.JSONDecodeError, OSError):
			return self.default_settings.copy()

	def read_settings(self, setting:str):
		settings = self._ensure_hidden_settings()
		value = settings[setting]
		return value

	def edit_settings(self, setting_name: str, value) -> dict:
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
		ports_dir = os.path.join(self.cwd, "files", "ports", "default_ports.json")
		with open(ports_dir, "r", encoding="utf-8") as f:
			ports = json.load(f)
		return ports

	def set_ports(self, stage: str, TGA: str, laser1: str, laser2: str, fsv: str):
		ports_dir = os.path.join(self.cwd, "files", "ports", "default_ports.json")
		ports = {
			"stage": stage,
			"TGA": TGA,
			"laser1": laser1,
			"laser2": laser2,
			"fsv": fsv
		}
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