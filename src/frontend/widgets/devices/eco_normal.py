"""
Module for creating and operating the PySide6 EcoVario normal mode widgets.
@author: Merlin Schmidt
@date: 2025-20-10
@file: src/frontend/widgets/devices/eco_normal.py
@note:
"""
from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QDoubleValidator, Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QSpacerItem, QLabel, QMessageBox

from src.frontend.widgets.utilities import create_input_field, create_output_field
from typing import Dict, Any

class StageWidgetNormal(QWidget):
	"""
	Create EcoVario normal mode widgets and functionality.
	:return: None
	"""
	sendRequest = Signal(Dict[tuple, Any])
	sendUpdate = Signal(Dict[tuple, Any], str)

	def __init__(self, device_id: str) -> None:
		super().__init__()
		self.device_id = device_id

		start_button = QPushButton("Start")
		stop_button = QPushButton("Stop")

		# creating layout #
		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		# creating and adding widgets to layout #
		layout.addWidget(QLabel("Stage Controls"), 0, 0)
		self.out_current_position = create_output_field(layout, "Current position", "0.0", "mm", 1, 0)
		self.out_target_position = create_output_field(layout, "Target position", "0.0", "mm", 3, 0)
		self.in_new_position = create_input_field(layout, "New position", "0.0", "mm", 5, 0)
		self.in_new_position.setValidator(QDoubleValidator())
		self.in_speed = create_input_field(layout, "Speed", "25.0", "mm/s", 7, 0)
		self.in_speed.setValidator(QDoubleValidator())
		layout.addItem(QSpacerItem(10, 100), 9, 0)
		layout.addWidget(start_button, 10, 0)
		layout.addWidget(stop_button, 11, 0)
		layout.addItem(QSpacerItem(10, 40), 12, 0)
		self.out_error_code = create_output_field(layout, "Error code", "", "", 13, 0)
		self.out_error_code.setAlignment(Qt.AlignLeft)

		self.setLayout(layout)
		start_button.clicked.connect(self._start)
		stop_button.clicked.connect(self._stop)
		self.in_new_position.returnPressed.connect(self._send_update)
		self.in_speed.editingFinished.connect(self._send_update)

	@Slot()
	def _start(self) -> None:
		"""
		Sends all stage parameters as Device requests as start signal
		:return: None
		"""
		try:
			pos = float(self.out_target_position.text().replace(",", "."))
			vel = float(self.in_speed.text().replace(",", "."))
			accell = 501.30
			deaccell = 501.30

			parameters = {
				(self.device_id, "target_pos"): pos,
				(self.device_id, "target_vel"): vel,
				(self.device_id, "target_acc"): accell,
				(self.device_id, "target_deacc"): deaccell,
				(self.device_id, "START"): None
			}

			self.sendRequest.emit(parameters)
			return
		except Exception as e:
			QMessageBox.warning(
				self,
				"UI Error",
				f"Something went wrong:\n{e}"
			)
			return

	@Slot()
	def _stop(self) -> None:
		"""
		Sends stop signal to the controller
		:return: None
		"""
		parameters = {
			(self.device_id, "STOP"): None
		}
		self.sendRequest.emit(parameters)
		return

	@Slot(dict)
	def get_update(self, parameters: Dict[tuple, Any]) -> None:
		"""
		Gets updated parameters from the controller and shows them in the UI.
		:param parameters: Parameters from the controller.
		:type parameters: Dict[str, Any]
		:return: None
		"""
		supproted_parameters = {
			"target_pos": "out_target_position",
			"target_vel": "in_speed",
			"target_acc": "in_accel",
			"target_deacc": "in_deaccel",
			"current_pos": "out_current_position",
			"error_code": "out_error_code"
		}
		for key, parameter in parameters.items():
			if not key[1] in supproted_parameters:
				QMessageBox.warning(
					self,
					"UI Error",
					f"something went wrong:\n{parameter} not supported."
				)
				return
			else:
				widget = getattr(self, supproted_parameters[key[1]])
				widget.setText(parameter)
				return

	@Slot()
	def _send_update(self) -> None:
		speed = self.in_speed.text().replace(",", ".")
		pos = self.out_target_position.text().replace(",", ".")

		self.out_target_position.setText(pos)

		update = {
			(self.device_id, "target_pos"): pos,
			(self.device_id, "target_vel"): speed,
		}
		self.sendUpdate.emit(update, "expert")
		return