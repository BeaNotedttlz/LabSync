from cmath import phase

from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QCheckBox, QLabel

from Classes.Widgets.fields import _create_combo_box, _create_input_field
from exceptions import UIParameterError


class FrequencyGeneratorWidgetExpet(QWidget):
	apply_signal = Signal(int, str, float, float, float, float, str, str, bool)

	waveforms = ["sine", "square", "triang", "dc"]
	inputmodes = ["Amp+Offset", "Low+High"]
	lockmodes = ["indep", "master", "slave", "off"]

	def __init__(self, channel) -> None:
		super().__init__()
		self.channel = channel

		# creating layout #
		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		# creating and adding widgets to layout #
		apply_button = QPushButton("Apply")
		self.output = QCheckBox("Set active")

		# creating layout and adding widgets to layout #
		layout = QGridLayout()
		layout.setVerticalSpacing(15)


		self.waveform = _create_combo_box(layout, self.waveforms, "Waveform", 1, 0)

		self.input_mode = _create_combo_box(layout, self.inputmodes, "Inputmode", 3, 0)
		self.amplitude = _create_input_field(layout, "Amp/Low", "0.0", "V", 5, 0)
		self.amplitude.setValidator(QDoubleValidator())
		self.offset = _create_input_field(layout, "Offset/High", "0.0", "V", 7, 0)
		self.offset.setValidator(QDoubleValidator())
		self.frequency = _create_input_field(layout, "Frequency", "0.0", "Hz", 9, 0)
		self.frequency.setValidator(QDoubleValidator())
		self.phase = _create_input_field(layout, "Pahse", "0.0", "Deg", 11, 0)
		self.phase.setValidator(QDoubleValidator())

		self.lockmode = _create_combo_box(layout, self.lockmodes, "Lockmode", 13, 0)

		layout.addWidget(QLabel("Channel " + str(self.channel) + ":"), 0, 0)
		layout.addWidget(self.output, 15, 0)
		layout.addWidget(apply_button, 16, 0)
		self.setLayout(layout)

		apply_button.clicked.connect(self._apply)

	@Slot()
	def _apply(self) -> None:
		waveform = self.waveforms[self.waveform.currentIndex()]
		amplitude = float(self.amplitude.text().replace(",", "."))
		offset = float(self.offset.text().replace(",", "."))
		phase = float(self.phase.text().replace(",", "."))
		frequency = float(self.frequency.text().replace(",", "."))
		lockmode = self.lockmodes[self.lockmode.currentIndex()]
		inputmode = self.inputmodes[self.input_mode.currentIndex()]
		output = self.output.isChecked()

		self.apply_signal.emit(
			self.channel,
			waveform,
			amplitude,
			offset,
			phase,
			frequency,
			inputmode,
			lockmode,
			output
		)
		return None

	def get_params(self, **kwargs) -> None:
		supported_params = {
			"waveform": "waveform",
			"amplitude": "amplitude",
			"offset": "offset",
			"phase": "phase",
			"frequency": "frequency",
			"lockmode": "lockmode",
			"output": "output"
		}
		for param, value in kwargs.items():
			if param not in supported_params:
				raise UIParameterError(param)
			if param == "waveform":
				idx = self._map_wave(value)
				self.waveform.setCurrentIndex(idx)
				return None
			elif param == "inputmode":
				idx = self._map_input(value)
				self.input_mode.setCurrentIndex(idx)
				return None
			elif param == "lockmode":
				idx = self._map_lock(value)
				self.lockmode.setCurrentIndex(idx)
				return None

			widget = getattr(self, supported_params[param])
			widget.clear()
			widget.insert(value)
			return None

	@staticmethod
	def _map_wave(waveform) -> int:
		if waveform == "sine":
			return 0
		elif waveform == "square":
			return 1
		elif waveform == "triang":
			return 2
		else:
			return 3

	@staticmethod
	def _map_lock(lockmode) -> int:
		if lockmode == "indep":
			return 0
		elif lockmode == "master":
			return 1
		elif lockmode == "slave":
			return 2
		else:
			return 3

	@staticmethod
	def _map_input(inputmode) -> int:
		if inputmode == "Amp+Offset":
			return 0
		else:
			return 1


# import pytest
# from pytestqt.qtbot import QtBot
#
# def test_apply(qtbot: QtBot):
# 	test = FrequencyGeneratorWidgetExpet(channel=1)
#
# 	with qtbot.wait_signal(test.apply_signal, timeout=100) as blocker:
# 		test._apply()
# 		assert blocker.args == [1, "sine", 0.0, 0.0, 0.0, 0.0, "Amp+Offset", "indep", False]

