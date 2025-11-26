"""
Module for creating and operating the PySide6 LuxX+ expert mode widgets.
@author: Merlin Schmidt
@date: 2025-21-10
@file: src/frontend/widgets/devices/luxx_expert.py
@note:
"""
from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QDoubleValidator, Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QCheckBox, QPushButton, QSpacerItem, QLabel, QMessageBox

from src.frontend.widgets.utilities import create_input_field, create_combo_box
from typing import Dict, Any

class LaserWidgetExpert(QWidget):
	"""
	Create LuxX+ expert mode widgets and functionality.
	:return: None
	"""
	sendRequest = Signal(Dict[tuple, Any])

	modulation_types = ["Standby", "CW", "Digital", "Analog"]
	control_modes = ["ACC", "APC"]

	def __init__(self, device_id: str, laser_index: int, max_power: float=1.0) -> None:
		"""Constructor method
		"""
		super().__init__()
		self.device_id = device_id
		self.laser_index = laser_index
		self.max_power = max_power

		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		# creating and adding widgets to layout #
		apply_button = QPushButton("Apply")
		self.if_active = QCheckBox("Set active")

		self.laser_power_percent = create_input_field(layout, "Setpoint λ-" + str(self.laser_index),
													  "0.0", "%", 1, 0)
		self.laser_power_percent.setValidator(QDoubleValidator())
		self.laser_power_absolute = create_input_field(layout, "Setpoint λ-" + str(self.laser_index),
													   "0.0", "mW", 3, 0)
		self.laser_power_absolute.setValidator(QDoubleValidator())


		self.modulation_mode = create_combo_box(layout, self.modulation_types,
											   "Modulation mode", 5, 0)

		self.control_mode = create_combo_box(layout, self.control_modes,
											 "Control mode", 7, 0)

		layout.addWidget(QLabel("λ-" + str(self.laser_index)), 0, 0)
		layout.addItem(QSpacerItem(10, 80), 9, 0)
		layout.addWidget(self.if_active, 10, 0)
		layout.addWidget(apply_button, 11, 0)
		self.setLayout(layout)

		apply_button.clicked.connect(self._apply)
		self.laser_power_percent.returnPressed.connect(
			lambda: self._calc_power(True)
		)
		self.laser_power_absolute.returnPressed.connect(
			lambda: self._calc_power(False)
		)
		return

	@Slot()
	def _apply(self) -> None:
		"""
		Sends all laser parameters as a Device request.
		:return: None
		"""
		temp_power = float(self.laser_power_percent.text().replace(",", "."))
		modulation = self.modulation_mode.currentIndex()
		modulation = self.modulation_types[modulation]
		control_mode = self.control_mode.currentIndex()
		control_mode = self.control_modes[control_mode]
		emission = self.if_active.isChecked()

		operating_mode = self._map_operating_mode(modulation, control_mode)

		parameters = {
			(self.device_id, "temp_power"): temp_power,
			(self.device_id, "operating_mode"): operating_mode,
			(self.device_id, "emission_status"): emission
		}

		self.sendRequest.emit(parameters)
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

	@Slot()
	def _calc_power(self, called_from_percent: bool) -> None:
		"""
		Calculated the laser power for either input fields
		:param called_from_percent: Flag if called from percent of absolute
		:type called_from_percent: bool
		:return: None
		"""
		if called_from_percent:
			self.laser_power_absolute.clear()
			power = float(self.laser_power_percent.text().replace(",", "."))
			power = power * self.max_power / 100
			self.laser_power_absolute.setText(str(power))
		else:
			self.laser_power_percent.clear()
			power = float(self.laser_power_absolute.text().replace(",", "."))
			power = power / self.max_power * 100
			self.laser_power_percent.setText(str(power))
		return

	@Slot(dict)
	def get_update(self, parameters: Dict[str, Any]) -> None:
		"""
		Gets updated parameters from the controller and shows them in the UI.
		:param parameters: Parameters from the controller
		:type parameters: Dict[str, Any]
		:return: None
		"""
		supported_parameters = {
			"temp_power": "laser_power_percent",
			"operating_mode": None,
			"emission_status": "if_active"
		}
		for key, parameter in parameters.items():
			if key[1] not in supported_parameters:
				QMessageBox.warning(
					self,
					"UI Error",
					f"something went wrong:\n{parameter} not supported."
				)
				return
			if key[1] == "operating_mode":
				modulation, control = self._map_ui_modes(parameter)
				self.modulation_mode.setCurrentIndex(modulation)
				self.control_mode.setCurrentIndex(control)
			elif key[1] == "emission_status":
				continue
			else:
				widget = getattr(self, supported_parameters[key[1]])
				widget.clear()
				widget.setText(parameter)
		return

	@staticmethod
	def _map_ui_modes(operating_mode: int) -> tuple:
		if operating_mode == 0:
			return 0, 0
		elif operating_mode == 1:
			return 1, 0
		elif operating_mode == 2:
			return 1, 1
		elif operating_mode == 3:
			return 2, 0
		else:
			return 3, 0