"""
Module for creating and operating the PySide6 Laser normal mode widgets.
@author: Merlin Schmidt
@date: 2025-21-10
@file: src/frontend/widgets/devices/luxx_normal.py
@note:
"""
from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QDoubleValidator, Qt
from PySide6.QtWidgets import (QWidget, QGridLayout,
							   QCheckBox, QPushButton, QSpacerItem,
							   QLabel, QSpinBox)

from src.frontend.widgets.utilities import create_input_field, create_combo_box
from typing import Dict, Any


class LaserWidgetNormal(QWidget):
	"""
	Create Normal mode widgets and functionality.
	"""
	sendRequest = Signal(Dict[tuple, Any])
	sendUpdate = Signal(Dict[tuple, Any])

	modulation_modes = ["Standby", "CW", "Digital", "Analog"]
	control_modes = ["ACC", "APC"]
	lock_modes = ["indep", "master", "slave", "off"]
	freq_gen_channels = ["1", "2", "3", "4"]

	def __init__(self) -> None:
		"""Constructor method
		"""
		super().__init__()

		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		# creating and adding widgets to layout #

		self.modulation1 = create_combo_box(layout, self.modulation_modes, "Modulation mode", 1, 0)
		self.modulation2 = create_combo_box(layout, self.modulation_modes, "Modulation mode", 1, 2)

		self.control_mode1 = create_combo_box(layout, self.control_modes, "Control mode", 3, 0)
		self.control_mode2 = create_combo_box(layout, self.control_modes, "Control mode", 3, 2)

		self.spinbox1 = QSpinBox()
		self.spinbox1.setMinimum(5)
		self.spinbox1.setMaximum(100)
		self.spinbox1.setSingleStep(5)
		self.spinbox1.setAlignment(Qt.AlignRight)

		self.spinbox2 = QSpinBox()
		self.spinbox2.setMinimum(5)
		self.spinbox2.setMaximum(100)
		self.spinbox2.setSingleStep(5)
		self.spinbox2.setAlignment(Qt.AlignRight)

		self.frequency1 = create_input_field(layout, "Modulation frequency", "0.0", "Hz", 7, 0)
		self.frequency1.setValidator(QDoubleValidator())
		self.frequency2 = create_input_field(layout, "Modulation frequency", "0,0", "Hz", 7, 2)
		self.frequency2.setValidator(QDoubleValidator())

		self.lockmode1 = create_combo_box(layout, self.lock_modes, "Lockmode", 9, 0)
		self.lockmode2 = create_combo_box(layout, self.lock_modes, "Lockmode", 9, 2)

		self.channel1 = create_combo_box(layout, self.freq_gen_channels, "TGA 1244 Channel", 11, 0)
		self.channel2 = create_combo_box(layout, self.freq_gen_channels, "TGA 1244 Channel", 11, 2)
		self.channel2.setCurrentIndex(1)

		self.output1 = QCheckBox("Set active \n λ-1")
		self.output2 = QCheckBox("Set active \n λ-2")

		apply_button = QPushButton("Apply")

		layout.addWidget(QLabel("Laser Controls"), 0, 1)
		layout.addWidget(QLabel("Power 1"), 5, 0)
		layout.addWidget(self.spinbox1, 6, 0)
		layout.addWidget(QLabel("%"), 6, 1)
		layout.addWidget(QLabel("Power 2"), 5, 2)
		layout.addWidget(self.spinbox2, 6, 2)
		layout.addWidget(QLabel("%"), 6, 3)

		layout.addItem(QSpacerItem(10, 80), 13, 0)
		layout.addWidget(self.output1, 14, 0)
		layout.addWidget(self.output2, 14, 2)
		layout.addWidget(apply_button, 15, 1)
		self.setLayout(layout)

		apply_button.clicked.connect(self._apply)
		return

	@Slot()
	def _apply(self) -> None:
		"""
		Sends all device parameters as a Device request.
		:return: None
		"""
		op_mode_1 = self._map_operating_mode(
			self.modulation_modes[self.modulation1.currentIndex()],
			self.control_modes[self.control_mode1.currentIndex()]
		)
		op_mode_2 = self._map_operating_mode(
			self.modulation_modes[self.modulation2.currentIndex()],
			self.control_modes[self.control_mode2.currentIndex()]
		)
		wave_1 = self._map_waveforms(
			self.modulation_modes[self.modulation1.currentIndex()]
		)
		wave_2 = self._map_waveforms(
			self.modulation_modes[self.modulation2.currentIndex()]
		)

		power_1 = (self.spinbox1.value() // 5) * 5
		self.spinbox1.setValue(power_1)
		power_2 = (self.spinbox2.value() // 5) * 5
		self.spinbox2.setValue(power_2)
		frequency_1 = float(self.frequency1.text().replace(',', '.'))
		frequency_2 = float(self.frequency2.text().replace(',', '.'))

		channel_1 = int(self.freq_gen_channels[self.channel1.currentIndex()])
		channel_2 = int(self.freq_gen_channels[self.channel2.currentIndex()])


		lockmode_1 = self.lock_modes[self.lockmode1.currentIndex()]
		lockmode_2 = self.lock_modes[self.lockmode2.currentIndex()]

		output_1 = self.output1.isChecked()
		output_2 = self.output2.isChecked()

		ch1_parameters = {
			("TGA1244","waveform"): wave_1,
			("TGA1244","frequency"): frequency_1,
			("TGA1244","lockmode"): lockmode_1,
			("TGA1244","output"): output_1,
			("Laser1","operating_mode"): op_mode_1,
			("Laser1","temp_power"): power_1,
		}
		self.sendRequest.emit(ch1_parameters)
		self.sendUpdate.emit(ch1_parameters)
		ch2_parameters = {
			("TGA1244","waveform"): wave_2,
			("TGA1244","frequency"): frequency_2,
			("TGA1244","lockmode"): lockmode_2,
			("TGA1244","output"): output_2,
			("Laser2","operating_mode"): op_mode_2,
			("Laser2","temp_power"): power_2,
		}
		self.sendRequest.emit(ch2_parameters)
		self.sendUpdate.emit(ch2_parameters)
		return

	@staticmethod
	def _map_operating_mode(modulation: str, control: str) -> int:
		"""
		Maps the desired modulation and control mode to the single digit ROM operating mode.
		:param modulation: Selected modulation mode
		:type modulation: str
		:param control: Selected control mode
		:type control: str
		:return: The corresponding operating mode in ROM
		:rtype: int
		"""
		if modulation == "Standby":
			return 0
		elif modulation == "Digital":
			return 3
		elif modulation == "Analog":
			return 4
		elif modulation == "CW" and control == "ACC":
			return 1
		else:
			return 2

	@staticmethod
	def _map_waveforms(modulation_mode) -> str:
		"""
		Maps the frequency generator waveform to the desired modulation mode.
		:param modulation_mode: Selected modulation mode.
		:type modulation_mode: str
		:return: The corresponding waveform
		:rtype: str
		"""
		if modulation_mode == "Digital":
			return "square"
		else:
			return "sine"