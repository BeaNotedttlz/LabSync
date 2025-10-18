from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QDoubleValidator, Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QSpinBox, QLabel, QPushButton, QCheckBox, QSpacerItem

from Classes.Widgets.fields import _create_combo_box, _create_input_field
from utils import UIParameterError


class LaserWidgetNormal(QWidget):
	apply_signal_laser1 = Signal(float, int, bool)
	apply_signal_laser2 = Signal(float, int, bool)
	freq_gen_apply_ch1 = Signal(int, str, float, float, str, bool, int)
	freq_gen_apply_ch2 = Signal(int, str, float, float, str, bool, int)

	modulation_modes = ["Standby", "CW", "Digital", "Analog"]
	control_modes = ["ACC", "APC"]
	lockmodes = ["indep", "master", "slave", "off"]
	channels = ["1", "2", "3", "4"]

	def __init__(self) -> None:
		super().__init__()

		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		# creating and adding widgets to layout #

		self.modulation1 = _create_combo_box(layout, self.modulation_modes, "Modulation mode", 1, 0)
		self.modulation2 = _create_combo_box(layout, self.modulation_modes, "Modulation mode", 1, 2)


		self.control_mode1 = _create_combo_box(layout, self.control_modes, "Control mode", 3, 0)
		self.control_mode2 = _create_combo_box(layout, self.control_modes, "Control mode", 3, 2)

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

		self.frequency1 = _create_input_field(layout, "Modulation frequency", "0.0", "Hz", 7, 0)
		self.frequency1.setValidator(QDoubleValidator())
		self.frequency2 = _create_input_field(layout, "Modulation frequency", "0,0", "Hz", 7, 2)
		self.frequency2.setValidator(QDoubleValidator())

		self.lockmode1 = _create_combo_box(layout, self.lockmodes, "Lockmode", 9, 0)
		self.lockmode2 = _create_combo_box(layout, self.lockmodes, "Lockmode", 9, 2)

		self.channel1 = _create_combo_box(layout, self.channels, "TGA 1244 Channel", 11, 0)
		self.channel2 = _create_combo_box(layout, self.channels, "TGA 1244 Channel", 11, 2)
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

	@Slot()
	def _apply(self) -> None:
		op_mode_1 = self._mode_map(
			self.modulation_modes[self.modulation1.currentIndex()],
			self.control_modes[self.control_mode1.currentIndex()]
		)
		op_mode_2 = self._mode_map(
			self.modulation_modes[self.modulation2.currentIndex()],
			self.control_modes[self.control_mode2.currentIndex()]
		)
		wave_1 = self._map_waveform(
			self.modulation_modes[self.modulation1.currentIndex()]
		)
		wave_2 = self._map_waveform(
			self.modulation_modes[self.modulation2.currentIndex()]
		)

		power_1 = (self.spinbox1.value() // 5) * 5
		self.spinbox1.setValue(power_1)
		power_2 = (self.spinbox2.value() // 5) * 5
		self.spinbox2.setValue(power_2)
		frequency_1 = float(self.frequency1.text().replace(',', '.'))
		frequency_2 = float(self.frequency2.text().replace(',', '.'))

		channel_1 = int(self.channels[self.channel1.currentIndex()])
		channel_2 = int(self.channels[self.channel2.currentIndex()])


		lockmode_1 = self.lockmodes[self.lockmode1.currentIndex()]
		lockmode_2 = self.lockmodes[self.lockmode2.currentIndex()]

		output_1 = self.output1.isChecked()
		output_2 = self.output2.isChecked()

		self.apply_signal_laser1.emit(power_1, op_mode_1, output_1)
		self.apply_signal_laser2.emit(power_2, op_mode_2, output_2)
		self.freq_gen_apply_ch1.emit(channel_1, wave_1, frequency_1, power_1, lockmode_1, output_1, 1)
		self.freq_gen_apply_ch2.emit(channel_2, wave_2, frequency_2, power_2, lockmode_2, output_2, 2)

		return None


	def get_params(self, *argv, **kwargs) -> None:
		supported_params = {
			"op_mode_1": None,
			"op_mode_2": None,
			"power_1": "spinbox1",
			"power_2": "spinbox2",
			"frequency_1": "frequency1",
			"frequency_2": "frequency2",
		}
		if len(argv) == 1 and isinstance(argv[0], dict):
			kwargs.update(argv[0])
		elif argv:
			raise TypeError("Only dict or named parameters accepted!")

		for param, value in kwargs.items():
			if param not in supported_params:
				raise UIParameterError(param)
			if param == "op_mode_1":
				mod_index, co_index = self._reverse_mode_map(value)
				self.modulation1.setCurrentIndex(mod_index)
				self.control_mode1.setCurrentIndex(co_index)
				return None
			elif param == "op_mode_2":
				mod_index, co_index = self._reverse_mode_map(value)
				self.modulation2.setCurrentIndex(mod_index)
				self.control_mode2.setCurrentIndex(co_index)
				return None


			widget = getattr(self, supported_params[param])
			if hasattr(widget, "setValue"):
				widget.setValue(value)
			else:
				widget.clear()
				widget.insert(value)
			return None


	@staticmethod
	def _mode_map(modulation_mode, control_mode) -> int:
		if modulation_mode == "Standby":
			return 0
		elif modulation_mode == "CW":
			if control_mode == "ACC":
				return 1
			else:
				return 2
		elif modulation_mode == "Analog":
			return 4
		elif modulation_mode == "Digital":
			return 3
		return -1

	@staticmethod
	def _reverse_mode_map(op_mode) -> tuple:
		if op_mode == 0:
			return 0, 0
		elif op_mode == 1:
			return 1, 0
		elif op_mode == 2:
			return 1, 1
		elif op_mode == 3:
			return 2, 0
		else:
			return 3, 0

	@staticmethod
	def _map_waveform(modulation_mode) -> str:
		if modulation_mode == "Analog":
			return "sine"
		elif modulation_mode == "Digital":
			return "square"
		else:
			return "sine"