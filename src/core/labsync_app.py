"""
Main application for controlling backend and frontend of the LabSync application.
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/core/labsync_app.py
@note:
"""

from src.core.labsync_worker import WorkerHandler
from src.backend.devices.eco_connect import EcoConnect

from src.frontend.main_window import MainWindow

from PySide6.QtCore import QObject, QEvent, Signal, Slot
from PySide6.QtWidgets import (QApplication)

from src.core.storage import InstrumentCache
from src.core.utilities import (FilesUtils, SignalHandler,
								UIParameterError, DeviceParameterError,
								ParameterOutOfRangeError, ParameterNotSetError)


class LabSync(QObject):
	"""
	LabSync class for handling the core logic between frontend and backend.

	:return: None
	:rtype: None
	"""

	def __init__(self, app, _file_dir: str) -> None:
		super().__init__()

		self.cache = InstrumentCache()
		self.file_utility = FilesUtils(_file_dir, file_name="settings.json")

		self.file_dir = _file_dir
		self.simulate = None

		self.main_window = MainWindow(app)
		self.main_window.requestClose.connect(self._cleanup_backend)

	def _cleanup_backend(self) -> None:
		# close all workers and devices
		return



