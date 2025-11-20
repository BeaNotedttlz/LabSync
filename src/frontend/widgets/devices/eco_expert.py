"""
Module for creating and operating the PySide6 EcoVario expert mode widgets.
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/frontend/widgets/devices/eco_expert.py
@note:
"""

from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QDoubleValidator, Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QCheckBox, QSpacerItem, QLabel, QMessageBox

from src.frontend.widgets.utilities import create_input_field, create_output_field
from typing import Dict, Any
from src.core.context import DeviceRequest, RequestType

class StageWidgetExpert(QWidget):
	"""
	Create EcoVario expert mode widgets and functionality.
	:return: None
	"""
	sendRequest = Signal(DeviceRequest)
	sendUpdate = Signal(dict)

	def __init__(self, device_id: str) -> None:
		super().__init__()
		self.device_id = device_id

		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		start_button = QPushButton("Start")
		stop_button = QPushButton("Stop")
		home_stage_button = QPushButton("Home Stage \n to position")
		self.sync = QCheckBox("Sync Accel. \n and Deaccel.")
		self.sync.setChecked(True)
		reset_error_button = QPushButton("Reset \n Error")

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

		layout.addItem(QSpacerItem(200, 10), 0, 1)

		self.in_accell = create_input_field(layout, "Acceleration", "501.30", "mm/s^2", 1, 2)
		self.in_accell.setValidator(QDoubleValidator())
		self.in_deaccell = create_input_field(layout, "Deacceleration", "501.30", "mm/s^2", 3, 2)
		self.in_deaccell.setValidator(QDoubleValidator())
		self.out_error_code = create_output_field(layout, "Error code", "", "", 10, 2)
		self.out_error_code.setAlignment(Qt.AlignLeft)

		layout.addWidget(home_stage_button, 9, 2)
		layout.addWidget(self.sync, 5, 2)
		layout.addWidget(reset_error_button, 8, 2)
		self.setLayout(layout)

		# signal routing #
		stop_button.clicked.connect(self._stop)
		start_button.clicked.connect(self._start)

		self.in_new_position.returnPressed.connect(self._send_update)
		self.in_speed.editingFinished.connect(self._send_update)
		return

	@Slot()
	def _start(self) -> None:
		"""
		Sends all stage parameters as Device requests as start signal
		:return:
		"""
		try:
			pos = float(self.out_target_position.text().replace(",", "."))
			vel = float(self.in_speed.text().replace(",", "."))
			accell = float(self.in_accell.text().replace(",", "."))
			deaccell = float(self.in_deaccell.text().replace(",", "."))

			parameters = {
				"target_pos": pos,
				"target_vel": vel,
				"target_acc": accell,
				"target_deacc": deaccell,
				"START": None
			}
			for key, value in parameters.items():
				cmd = DeviceRequest(
					device_id=self.device_id,
					cmd_type=RequestType.SET,
					parameter=key,
					value=value
				)
				self.sendRequest.emit(cmd)
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
		cmd = DeviceRequest(
			device_id=self.device_id,
			cmd_type=RequestType.SET,
			parameter="STOP",
			value=None
		)
		self.sendRequest.emit(cmd)
		return

	@Slot()
	def get_update(self, parameters: Dict[str, Any]) -> None:
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
			"current_pos": "out_current_position"
		}
		for key, parameter in parameters.items():
			if not key in supproted_parameters:
				QMessageBox.warning(
					self,
					"UI Error",
					f"something went wrong:\n{parameter} not supported."
				)
				return
			else:
				widget = getattr(self, supproted_parameters[key])
				widget.setText(parameter)
				return

	@Slot()
	def _send_update(self) -> None:
		speed = self.in_speed.text().replace(",", ".")
		pos = self.out_target_position.text().replace(",", ".")

		update = {
			"target_pos": pos,
			"target_vel": speed,
		}
		self.sendUpdate.emit(update)
		return

