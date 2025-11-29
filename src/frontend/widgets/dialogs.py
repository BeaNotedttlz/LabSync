"""
Module for creating and operating the PySide6 dialog window widgets.
@author: Merlin Schmidt
@date: 2025-18-10
@file: src.frontend.widgets.dialogs.py
@note:
"""

from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import Qt
from PySide6.QtWidgets import (QWidget, QLabel, QPushButton, QProgressBar,
							   QSpacerItem, QGridLayout, QCheckBox, QDialog,
							   QGroupBox, QVBoxLayout, QHBoxLayout)
from src.frontend.widgets.utilities import create_input_field
from typing import Dict, Any

class LaserInfoDialog(QDialog):
	class SingleLaserWidget(QWidget):
		def __init__(self, laser_name: str="Laser", parent=None) -> None:
			super().__init__(parent)

			self.group = QGroupBox(laser_name)

			self.model_code = QLabel("Model Code: Not connected")
			self.device_id = QLabel("Device ID: Not connected")
			self.firmware = QLabel("Firmware Version: Not connected")
			self.wavelength = QLabel("Operation Wavelength: Not connected")
			self.max_power = QLabel("Maximum Power: Not connected")
			self.status = QLabel("Device Stats: Not connected")
			layout = QVBoxLayout()
			layout.addWidget(self.model_code)
			layout.addWidget(self.device_id)
			layout.addWidget(self.firmware)
			layout.addWidget(self.wavelength)
			layout.addWidget(self.max_power)
			layout.addWidget(self.status)

			self.group.setLayout(layout)

			main_layout = QVBoxLayout()
			main_layout.addWidget(self.group)
			self.setLayout(main_layout)
			return

		def update_data(self, data: Dict[str, Any]) -> None:
			# Convert dict to a list
			# This is done because the data will always be the same and the keys can be ignored
			data_list = []
			for key, data in data.items():
				data_list.append(data)

			self.model_code.setText("Model Code: " + str(data_list[0]))
			self.device_id.setText("Device ID :" + str(data_list[1]))
			self.firmware.setText(str(data_list[2]))
			self.wavelength.setText(str(data_list[3]))
			self.max_power.setText(str(data_list[4]))
			self.status.setText(str(data_list[5]))
			return

	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		# set window information
		self.setWindowTitle("Laser Information")
		self.setFixedSize(600, 400)

		# set layout
		layout = QHBoxLayout()

		self.laser1_widget = self.SingleLaserWidget(laser_name="Laser 1")
		self.laser2_widget = self.SingleLaserWidget(laser_name="Laser 2")

		layout.addWidget(self.laser1_widget)
		layout.addWidget(self.laser2_widget)

		self.setLayout(layout)
		return

	@Slot(object)
	def update_info(self, data:Dict[str, dict]) -> None:
		if "Laser1" in data:
			self.laser1_widget.update_data(data["Laser1"])

		if "Laser2" in data:
			self.laser2_widget.update_data(data["Laser2"])

		return

class PortSelectionDialog(QDialog):

	applyPorts = Signal(str, str, str, str, str)
	defaultPorts = Signal(str, str, str, str, str)

	def __init__(self, parent=None) -> None:
		"""Constructor method
		"""
		super().__init__(parent)
		self.setWindowTitle("Port Selection")
		self.setFixedSize(300, 400)

		layout = QGridLayout()

		# crea input fields
		self.stage_port = create_input_field(layout, "EcoVatio Port:", "", "", 0, 0)
		self.stage_port.setAlignment(Qt.AlignLeft)
		self.freq_gen_port = create_input_field(layout, "TGA 1244 Port:", "", "", 2, 0)
		self.freq_gen_port.setAlignment(Qt.AlignLeft)
		self.laser1_port = create_input_field(layout, "Laser 1 Port:", "", "", 4, 0)
		self.laser1_port.setAlignment(Qt.AlignLeft)
		self.laser2_port = create_input_field(layout, "Laser 2 Port:", "", "", 6, 0)
		self.laser2_port.setAlignment(Qt.AlignLeft)
		self.fsv_port = create_input_field(layout, "FSV Port:", "", "", 8, 0)
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
		return

	@Slot()
	def _apply_ports(self) -> None:
		"""
		Get all ports and emit signal to save and close
		:return: None
		"""
		stage = self.stage_port.text()
		freq_gen = self.freq_gen_port.text()
		laser1 = self.laser1_port.text()
		laser2 = self.laser2_port.text()
		fsv = self.fsv_port.text()

		self.applyPorts.emit(stage, freq_gen, laser1, laser2, fsv)
		return

	@Slot()
	def _set_default(self) -> None:
		"""
		Get all ports and save to default file
		:return: None
		"""
		stage = self.stage_port.text()
		freq_gen = self.freq_gen_port.text()
		laser1 = self.laser1_port.text()
		laser2 = self.laser2_port.text()
		fsv = self.fsv_port.text()

		self.defaultPorts.emit(stage, freq_gen, laser1, laser2, fsv)
		return

	@Slot(object)
	def get_current_ports(self, current_ports: Dict[str, str]) -> None:
		"""
		Get the currently set device ports and show in the dialog
		:return: None
		"""
		# TODO no baudrate -> add baudrate selection?
		self.stage_port.setText(current_ports["EcoVario"][0])
		self.freq_gen_port.setText(current_ports["TGA1244"][0])
		self.laser1_port.setText(current_ports["Laser1"][0])
		self.laser2_port.setText(current_ports["Laser2"][0])
		self.fsv_port.setText(current_ports["FSV3000"])
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
		self.debug_mode_box.setChecked(debug_mode)
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
