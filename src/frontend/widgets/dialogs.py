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
	"""
	Dialog to show information about connected lasers.
	"""
	class SingleLaserWidget(QWidget):
		"""
		Nested class to create the widget for a single laser.
		Note that this is generally not a good practice, but it is done here to keep the code organized.
		"""
		def __init__(self, laser_name: str="Laser", parent=None) -> None:
			"""Constructor method
			"""
			super().__init__(parent)

			# make group box
			self.group = QGroupBox(laser_name)

			# create labels
			# The labels are initialized with "Not connected" text
			self.model_code = QLabel("Model Code: Not connected")
			self.device_id = QLabel("Device ID: Not connected")
			self.firmware = QLabel("Firmware Version: Not connected")
			self.wavelength = QLabel("Operation Wavelength: Not connected")
			self.max_power = QLabel("Maximum Power: Not connected")
			self.status = QLabel("Device Stats: Not connected")
			# set layout
			layout = QVBoxLayout()
			# add widgets to layout
			layout.addWidget(self.model_code)
			layout.addWidget(self.device_id)
			layout.addWidget(self.firmware)
			layout.addWidget(self.wavelength)
			layout.addWidget(self.max_power)
			layout.addWidget(self.status)

			# set layout to group box
			self.group.setLayout(layout)

			# set main layout
			main_layout = QVBoxLayout()
			main_layout.addWidget(self.group)
			self.setLayout(main_layout)
			return

		def update_data(self, data: Dict[str, Any]) -> None:
			"""
			Update the laser information labels with new data.
			:param data: New data dictionary
			:type data: Dict[str, Any]
			:return: None
			"""
			# Convert dict to a list
			# This is done because the data will always be the same and the keys can be ignored
			data_list = []
			for key, data in data.items():
				data_list.append(data)

			# Update labels
			self.model_code.setText("Model Code: " + str(data_list[0]))
			self.device_id.setText("Device ID :" + str(data_list[1]))
			self.firmware.setText(str(data_list[2]))
			self.wavelength.setText(str(data_list[3]))
			self.max_power.setText(str(data_list[4]))
			self.status.setText(str(data_list[5]))
			return

	def __init__(self, parent=None) -> None:
		"""Constructor method
		"""
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
		"""
		Update the laser information widgets with new data.
		:param data: New Data dictionary
		:type data: Dict[str, dict]
		:return: None
		"""
		# Update laser 1 data if available
		if "Laser1" in data:
			self.laser1_widget.update_data(data["Laser1"])

		# Update laser 2 data if available
		if "Laser2" in data:
			self.laser2_widget.update_data(data["Laser2"])
		return

class PortSelectionDialog(QDialog):
	"""
	Dialog to select the device ports for the connected devices.
	"""
	# Signal to apply the port changes
	applyPorts = Signal(str, str, str, str, str)
	# Signal to set the default ports
	defaultPorts = Signal(str, str, str, str, str)

	def __init__(self, parent=None) -> None:
		"""Constructor method
		"""
		super().__init__(parent)
		# Set window information
		self.setWindowTitle("Port Selection")
		self.setFixedSize(300, 400)

		# set layout
		layout = QGridLayout()

		# create input fields
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


class SettingsDialog(QDialog):
	"""
	Dialog to change application settings.
	"""
	# Signal to apply the settings changes
	applySettings = Signal(str, bool)

	def __init__(self, parent=None) -> None:
		"""Constructor method
		"""
		super().__init__(parent)

		# Set window information
		self.setWindowTitle("Settings")
		self.setMinimumSize(300, 150)

		# set layout
		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		# create input fields
		self.username_input = create_input_field(layout, "Username:", "", "", 0, 0)
		self.username_input.setAlignment(Qt.AlignLeft)
		self.debug_mode_box = QCheckBox("Debug Mode")
		self.debug_mode_box.setChecked(False)
		self.apply_button = QPushButton("Apply")

		layout.addItem(QSpacerItem(10, 100), 4, 0)
		layout.addWidget(self.debug_mode_box, 5, 0)
		layout.addWidget(self.apply_button, 6, 0)

		self.setLayout(layout)
		self.apply_button.clicked.connect(self._apply)
		return

	@Slot()
	def _apply(self) -> None:
		"""
		Get all settings and emit signal to close
		:return: Only emits signal does not return anything
		"""
		# get settings
		username = self.username_input.text()
		debug_mode = self.debug_mode_box.isChecked()

		# emit signal
		self.applySettings.emit(username, debug_mode)
		return

	def load_settings(self, settings: Dict[str, Any]) -> None:
		"""
		Get the currently set settings and show in the dialog
		:return: None
		"""
		try:
			# extract settings from dict
			username = settings["username"]
			debug_mode = settings["debug_mode"]
		except KeyError:
			# set default values
			username = ""
			debug_mode = False

		# set values in dialog
		self.username_input.setText(username)
		self.debug_mode_box.setChecked(debug_mode)
		return
