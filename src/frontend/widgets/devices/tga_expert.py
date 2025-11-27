"""
Module for creating and operating the PySide6 TGA1244 expert mode widgets.
@author: Merlin Schmidt
@date: 2025-20-10
@file: src/frontend/widgets/devices/tga_expert.py
@note:
"""
from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QCheckBox, QLabel, QMessageBox

from src.frontend.widgets.utilities import create_input_field, create_combo_box
from typing import Dict, Any

class FrequencyGeneratorWidget(QWidget):
	"""
	Create TGA1244 expert mode widgets and functionality.
	:return: None
	"""
	sendRequest = Signal(object)

	wave_forms = ["sine", "square", "triang", "dc"]
	input_modes = ["Amp+Offset", "Low+High"]
	lock_modes = ["indep", "maser", "slave", "off"]

	def __init__(self, device_id: str, channel_index = int) -> None:
		super().__init__()
		self.device_id = device_id
		self.channel_index = channel_index

		# creating layout #
		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		# creating and adding widgets to layout #
		apply_button = QPushButton("Apply")
		self.output = QCheckBox("Set active")

		# creating layout and adding widgets to layout #
		layout = QGridLayout()
		layout.setVerticalSpacing(15)


		self.waveform = create_combo_box(layout, self.wave_forms, "Waveform", 1, 0)

		self.input_mode = create_combo_box(layout, self.input_modes, "Inputmode", 3, 0)
		self.amplitude = create_input_field(layout, "Amp/Low", "0.0", "V", 5, 0)
		self.amplitude.setValidator(QDoubleValidator())
		self.offset = create_input_field(layout, "Offset/High", "0.0", "V", 7, 0)
		self.offset.setValidator(QDoubleValidator())
		self.frequency = create_input_field(layout, "Frequency", "0.0", "Hz", 9, 0)
		self.frequency.setValidator(QDoubleValidator())
		self.phase = create_input_field(layout, "Pahse", "0.0", "Deg", 11, 0)
		self.phase.setValidator(QDoubleValidator())

		self.lockmode = create_combo_box(layout, self.lock_modes, "Lockmode", 13, 0)

		layout.addWidget(QLabel("Channel " + str(self.channel_index) + ":"), 0, 0)
		layout.addWidget(self.output, 15, 0)
		layout.addWidget(apply_button, 16, 0)
		self.setLayout(layout)

		apply_button.clicked.connect(self._apply)

	@Slot()
	def _apply(self) -> None:
		"""
		Sends all frequency generator parameters as a Device request
		:return: None
		"""
		try:
			wave_form = self.wave_forms[self.waveform.currentIndex()]
			input_mode = self.input_modes[self.input_mode.currentIndex()]
			lock_mode = self.lock_modes[self.lockmode.currentIndex()]
			amplitude = float(self.amplitude.text().replace(",", "."))
			offset = float(self.offset.text().replace(",", "."))
			phase = float(self.phase.text().replace(",", "."))
			frequency = float(self.frequency.text().replace(",", "."))
			output = self.output.isChecked()
		except Exception as e:
			QMessageBox.warning(
				self,
				"UI Error",
				f"Something went wrong:\n{e}"
			)
			return
		if input_mode == "Low+High":
			amplitude = offset - amplitude
			offset = (offset + amplitude) / 2

		parameters = {
			(self.device_id, "waveform"): (wave_form, self.channel_index),
			(self.device_id, "lockmode"): (lock_mode, self.channel_index),
			(self.device_id, "frequency"): (frequency, self.channel_index),
			(self.device_id, "amplitude"): (amplitude, self.channel_index),
			(self.device_id, "offset"): (offset, self.channel_index),
			(self.device_id, "phase"): (phase, self.channel_index),
			(self.device_id, "output"): (output, self.channel_index)
		}

		self.sendRequest.emit(parameters)
		return

	@Slot(dict)
	def get_update(self, parameters: Dict[str, Any]) -> None:
		"""
		Gets updated parameters from the controller and shows them in the UI.
		:param parameters: Parameters from the controller.
		:type parameters: Dict[str, Any]
		:return: None
		"""
		supported_parameters = {
			"waveform": "waveform",
			"lockmode": "lockmode",
			"frequency": "frequency",
			"amplitude": "amplitude",
			"offset": "offset",
			"phase": "phase",
			"output": "output",
		}
		for key, parameter in parameters.items():
			channel_index = parameter[0]
			actual_value = parameter[1]
			if key[1] not in supported_parameters:
				QMessageBox.warning(
					self,
					"UI Error",
					f"something went wrong:\n{parameter} not supported."
				)
				return
			if not channel_index == self.channel_index:
				QMessageBox.warning(
					self,
					"UI Error",
					"The request and device index does not match"
				)
				return
			if key[1] == "waveform":
				idx = self._map_wave(actual_value)
				self.waveform.setCurrentIndex(idx)
			elif key[1] == "lockmode":
				idx = self._map_lock(actual_value)
				self.lockmode.setCurrentIndex(idx)
			elif key[1] == "output":
				continue
			else:
				widget = getattr(self, supported_parameters[key[1]])
				widget.clear()
				widget.insert(str(actual_value))
		return

	@staticmethod
	def _map_wave(waveform) -> int:
		"""
		Maps the waveform to the corresponding index in the UI.
		:param waveform: Waveform
		:type waveform: str
		:return: Index of the waveform in the UI
		:rtype: int
		"""
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
		"""
		Maps the lockmode to the corresponding index in the UI
		:param lockmode: Lockmode
		:type lockmode: str
		:return: Index of the lockmode in the UI
		:rtype: int
		"""
		if lockmode == "indep":
			return 0
		elif lockmode == "master":
			return 1
		elif lockmode == "slave":
			return 2
		else:
			return 3
