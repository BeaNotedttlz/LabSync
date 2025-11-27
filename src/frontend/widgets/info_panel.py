"""
Module for creating and operating the PySide6 info panel widgets.
@author: Merlin Schmidt
@date: 2025-18-10
@file: src.frontend.widgets.info_panel.py
@note:
"""

from PySide6.QtCore import Signal, Qt, Slot
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QLabel, QFrame

class InfoPanelWidget(QWidget):
	"""
	Class for creating the widgets and functionality of the info panel.

	:return: None
	:rtype: None
	"""
	# create signals for functionality
	updatePort = Signal(str, bool)
	laserInfoSig = Signal()

	def __init__(self) -> None:
		"""Constructor method
		"""
		super().__init__()
		self.info_states = {
			0: ["Moving", "Not Moving"],
			1: ["Emission off", "Emission on"],
			2: ["Closed", "Open", "Error"]
		}
		self.indicators = {}

		self.layout = QGridLayout()
		self.layout.setVerticalSpacing(5)

		laser_button = QPushButton("Laser info")
		laser_button.clicked.connect(self.laserInfoSig.emit)

		self._create_status_indicator("EcoVarioStatus", "Stage :", self.info_states[0], 0, 0)
		self._create_status_indicator("Laser1Status", "Laser 1:", self.info_states[1], 1, 0)
		self._create_status_indicator("Laser2Status", "Laser 2:", self.info_states[1], 2, 0)
		self.layout.addWidget(laser_button, 3, 0)

		self._create_port_indicator("EcoVario", "EcoVario port:", self.info_states[2], 4, 0)
		self._create_port_indicator("TGA1244", "TGA 1244 port:", self.info_states[2], 6, 0)
		self._create_port_indicator("Laser1", "Laser 1 port", self.info_states[2], 8, 0)
		self._create_port_indicator("Laser2", "Laser 2 port:", self.info_states[2], 10, 0)
		self._create_port_indicator("FSV3000", "FSV3000 Port:", self.info_states[2], 12, 0)
		self.setLayout(self.layout)

		self.indicators["EcoVario"]["buttons"][0].clicked.connect(lambda: self._update_device_port_status("EcoVario", True))
		self.indicators["EcoVario"]["buttons"][1].clicked.connect(lambda: self._update_device_port_status("EcoVario", False))

		self.indicators["TGA1244"]["buttons"][0].clicked.connect(lambda: self._update_device_port_status("TGA1244", True))
		self.indicators["TGA1244"]["buttons"][1].clicked.connect(lambda: self._update_device_port_status("TGA1244", False))

		self.indicators["Laser1"]["buttons"][0].clicked.connect(lambda: self._update_device_port_status("Laser1", True))
		self.indicators["Laser1"]["buttons"][1].clicked.connect(lambda: self._update_device_port_status("Laser1", False))
		self.indicators["Laser2"]["buttons"][0].clicked.connect(lambda: self._update_device_port_status("Laser2", True))
		self.indicators["Laser2"]["buttons"][1].clicked.connect(lambda: self._update_device_port_status("Laser2", False))

		self.indicators["FSV3000"]["buttons"][0].clicked.connect(lambda: self._update_device_port_status("FSV3000", True))
		self.indicators["FSV3000"]["buttons"][1].clicked.connect(lambda: self._update_device_port_status("FSV3000", False))

	def _create_status_indicator(self, name: str, label: str, status: list, row: int, column: int) -> None:
		label = QLabel(label)
		label.setAlignment(Qt.AlignRight)
		status_label = QLabel(status[0])
		indicator = QFrame()
		indicator.setFixedSize(14, 14)
		indicator.setStyleSheet("background-color: red")

		self.layout.addWidget(label, row, column)
		self.layout.addWidget(indicator, row, column + 1, alignment=Qt.AlignRight)
		self.layout.addWidget(status_label, row, column + 2)

		indicator_data = {
			"frame": indicator,
			"status": status_label,
			"text": status
		}

		self.indicators[name] = indicator_data
		return None

	def _update_device_port_status(self, device_id: str, status: bool) -> None:
		self.updatePort.emit(device_id, status)
		return

	def _create_port_indicator(self, name: str, label: str, status: list, row: int, column: int) -> None:
		label = QLabel(label)
		label.setAlignment(Qt.AlignRight)
		status_label = QLabel(status[0])
		indicator = QFrame()
		indicator.setFixedSize(14, 14)
		indicator.setStyleSheet("background-color: red")

		open_button = QPushButton("Open")
		open_button.setFixedSize(60, 30)
		close_button = QPushButton("Close")
		close_button.setFixedSize(60, 30)

		self.layout.addWidget(label, row, column)
		self.layout.addWidget(indicator, row, column + 1, alignment=Qt.AlignRight)
		self.layout.addWidget(status_label, row, column + 2)
		self.layout.addWidget(open_button, row + 1, column)
		self.layout.addWidget(close_button, row + 1, column + 1)

		indicator_data = {
			"frame": indicator,
			"status": status_label,
			"text": status,
			"buttons": [open_button, close_button]
		}

		self.indicators[name] = indicator_data
		return None

	@Slot(str, bool)
	def update_indicator(self, name: str, state: bool) -> None:
		current_indicator = self.indicators[name]
		if state:
			current_indicator["frame"].setStyleSheet("background-color: green")
			current_indicator["status"].setText(current_indicator["text"][1])
			return None
		else:
			current_indicator["frame"].setStyleSheet("background-color: red")
			current_indicator["status"].setText(current_indicator["text"][0])
			return None

