"""
utils.py provides necessary utility functions for LabSync application.
"""

from PySide6.QtCore import QObject
import os, pathlib, platform, subprocess, tempfile, json

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
	def __init__(self):
		self.default_settings = {
			"version": 2.5,
			"usnername": "",
			"simulate_devices": False,
		}

	def ensure_hidden_settings(self, filename: str = "settings.json") -> dict:
		system = platform.system()
		cwd = os.getcwd()

		if system == "Windows":
			folder =os.path.join(cwd, "settings")
		else:
			folder = os.path.join(cwd, ".settings")

		os.makedirs(folder, exist_ok=True)

		settings_path = os.path.join(folder, filename)

		if not os.path.exists(settings_path):
			with open(settings_path, "w", encoding="utf-8") as f:
				json.dump(self.default_settings, f, indent=2)

		if system == "Windows":
			try:
				subprocess.run(["attrib", "+H", folder], check=True)
			except Exception as e:
				print(f"Warning: could not hide folder ({e})")

		try:
			with open(settings_path, "r", encoding="utf-8") as f:
				data = json.load(f)
			return data
		except (json.JSONDecodeError, OSError):
			# fallback if corrupted
			return self.default_settings.copy()
