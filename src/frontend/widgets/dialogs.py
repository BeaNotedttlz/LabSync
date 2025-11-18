"""
Module for creating and operating the PySide6 dialog window widgets
@author: Merlin Schmidt
@date: 2025-18-10
@file: src.frontend.widgets.dialogs.py
@note:
"""

from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import Qt
from PySide6.QtWidgets import (QWidget, QLabel, QPushButton,
							   QSpacerItem, QGridLayout, QCheckBox)
from src.frontend.widgets.utilities import create_input_field

class LaserInfoDialog(QWidget):
	"""
	Class for creating widgets and functionality of the laser info dialog.

	:param firmware: Laser firmware information
	:type firmware: list
	:param specs: Laser specifications information
	:type specs: list
	:param max_power: Laser maximum power information
	:type max_power: list
	:param error_byte: Laser error byte information
	:type error_byte: list
	:return: None
	:rtype: None
	"""
	def __init__(self, firmware: list, specs: list,
				 max_power: list, error_byte: list) -> None:
		"""Constructor method
		"""
		super().__init__()
		# create layout
		layout = QGridLayout()
		layout.setVerticalSpacing(10)
		self.setWindowTitle("Laser Info")
		self.setMinimumSize(600, 400)

		# create all widgets
		for i in [1, 2]:
			layout.addWidget(QLabel("Laser %d: " % i), 0, i - 1 if i == 1 else i + 1)
			layout.addWidget(QLabel("Model code: "), 1, i - 1 if i == 1 else i + 1)
			layout.addWidget(QLabel("Device id: "), 2, i - 1 if i == 1 else i + 1)
			layout.addWidget(QLabel("Firmware version: "), 3, i - 1 if i == 1 else i + 1)
			layout.addWidget(QLabel("Wavelenght: "), 4, i - 1 if i == 1 else i + 1)
			layout.addWidget(QLabel("Max power: "), 5, i - 1 if i == 1 else i + 1)
			layout.addWidget(QLabel("Status: "), 6, i - 1 if i == 1 else i + 1)

		layout.addWidget(QLabel(firmware[0][0]), 1, 1)
		layout.addWidget(QLabel(firmware[0][1]), 2, 1)
		layout.addWidget(QLabel(firmware[0][2]), 3, 1)
		layout.addWidget(QLabel(specs[0][0]), 4, 1)
		layout.addWidget(QLabel(str(max_power[0])), 5, 1)
		layout.addWidget(QLabel(error_byte[0]), 6, 1)

		layout.addWidget(QLabel(firmware[1][0]), 1, 4)
		layout.addWidget(QLabel(firmware[1][1]), 2, 4)
		layout.addWidget(QLabel(firmware[1][2]), 3, 4)
		layout.addWidget(QLabel(specs[1][0]), 4, 4)
		layout.addWidget(QLabel(str(max_power[1])), 5, 4)
		layout.addWidget(QLabel(error_byte[1]), 6, 4)

		# set layout
		self.setLayout(layout)

class PortSelectionDialog(QWidget):
	"""
	Class for creating widgets and functionality of the port selection dialog.

	:param stage_port: Stage port
	:type stage_port: str
	:param freq_gen_port: Frequency generation port
	:type freq_gen_port: str
	:param laser1_port: Laser 1 port
	:type laser1_port: str
	:param laser2_port: Laser 2 port
	:type laser2_port: str
	:param fsv_port: FSV port
	:type fsv_port: str
	:return: None
	:rtype: None
	"""
	# signals for functionality
	applySig = Signal(str, str, str, str, str)
	defaultSig = Signal(str, str, str, str, str)

	def __init__(self, stage_port: str, freq_gen_port: str, laser1_port: str, laser2_port: str, fsv_port: str) -> None:
		"""Constructor method
		"""
		super().__init__()

		# create layout and spacing
		layout = QGridLayout()
		layout.setVerticalSpacing(10)
		self.setWindowTitle("Port Selection")
		self.setMinimumSize(300, 400)

		# crea input fields
		self.stage_port = create_input_field(layout, "EcoVatio Port:", stage_port, "", 0, 0)
		self.stage_port.setAlignment(Qt.AlignLeft)
		self.freq_gen_port = create_input_field(layout, "TGA 1244 Port:", freq_gen_port, "", 2, 0)
		self.freq_gen_port.setAlignment(Qt.AlignLeft)
		self.laser1_port = create_input_field(layout, "Laser 1 Port:", laser1_port, "", 4, 0)
		self.laser1_port.setAlignment(Qt.AlignLeft)
		self.laser2_port = create_input_field(layout, "Laser 2 Port:", laser2_port, "", 6, 0)
		self.laser2_port.setAlignment(Qt.AlignLeft)
		self.fsv_port = create_input_field(layout, "FSV Port:", fsv_port, "", 8, 0)
		self.fsv_port.setAlignment(Qt.AlignLeft)

		# create apply button
		apply_button = QPushButton("Apply")
		def_button = QPushButton("Set as default")

		# set layout
		layout.addItem(QSpacerItem(100, 10), 7, 0)
		layout.addWidget(apply_button, 10, 0)
		layout.addWidget(def_button, 10, 1)

		self.setLayout(layout)
		apply_button.clicked.connect(self._apply_ports)
		def_button.clicked.connect(self._set_default)

	@Slot()
	def _apply_ports(self) -> None:
		"""
		Get all ports and emit signal to close

		:return: Only emits signal does not return anything
		:rtype: None
		"""
		stage = self.stage_port.text()
		freq_gen = self.freq_gen_port.text()
		laser1 = self.laser1_port.text()
		laser2 = self.laser2_port.text()
		fsv = self.fsv_port.text()

		self.applySig.emit(stage, freq_gen, laser1, laser2, fsv)
		return

	@Slot()
	def _set_default(self) -> None:
		"""
		Get all ports and emit signal to save and close

		:return: Only emits signal does not return anything
		:rtype: None
		"""
		stage = self.stage_port.text()
		freq_gen = self.freq_gen_port.text()
		laser1 = self.laser1_port.text()
		laser2 = self.laser2_port.text()
		fsv = self.fsv_port.text()

		self.defaultSig.emit(stage, freq_gen, laser1, laser2, fsv)
		return

class SettingsDialog(QWidget):
	"""
	Module for creating widgets and functionality of the settings dialog.

	:param username: Username
	:type username: str
	:param debug_mode: Enable / Disable debug mode
	:type debug_mode: bool
	:return: None
	:rtype: None
	"""
	# signals for functionality
	applySig = Signal(str, bool)

	def __init__(self,username: str, debug_mode: bool) -> None:
		"""Constructor method
		"""
		super().__init__()
		layout = QGridLayout()
		layout.setVerticalSpacing(10)
		self.setWindowTitle("Port Selection")
		self.setMinimumSize(300, 150)

		self.username = username
		self.debug_mode = debug_mode

		self.username_input = create_input_field(layout, "Username:", username, "", 0, 0)
		self.username_input.setAlignment(Qt.AlignLeft)
		self.debug_mode_box = QCheckBox("Debug Mode")
		self.apply_button = QPushButton("Apply")

		layout.addItem(QSpacerItem(10, 100), 4, 0)
		layout.addWidget(self.debug_mode_box, 5, 0)
		layout.addWidget(self.apply_button, 6, 0)

		self.setLayout(layout)
		self.apply_button.clicked.connect(self._apply)

	@Slot()
	def _apply(self) -> None:
		"""
		Get all settings and emit signal to close

		:return: Only emits signal does not return anything
		:rtype: None
		"""
		username = self.username_input.text()
		debug_mode = self.debug_mode_box.isChecked()

		self.applySig.emit(username, debug_mode)
		return
