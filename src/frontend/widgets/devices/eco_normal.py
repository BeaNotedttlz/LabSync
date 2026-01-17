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
	"""
	# Send request signal to the controller
	sendRequest = Signal(object)
	# Send update signal to the main application
	sendUpdate = Signal(object, str)

	def __init__(self, device_id: str) -> None:
		"""Constructor method
		"""
		super().__init__()
		# Store the device ID
		self.device_id = device_id

		# creating buttons
		start_button = QPushButton("Start")
		stop_button = QPushButton("Stop")

		# creating layout
		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		# creating and adding widgets to layout
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
		return

	@Slot()
	def _start(self) -> None:
		"""
		Sends all stage parameters as Device requests as start signal
		:return: None
		"""
		try:
			# Read and convert input values
			pos = float(self.out_target_position.text().replace(",", "."))
			vel = float(self.in_speed.text().replace(",", "."))
			# For the normal mode, we use fixed acceleration and deacceleration values
			# These
			accell = 501.30
			deaccell = 501.30

			# Store parameters in a dictionary
			parameters = {
				(self.device_id, "target_pos"): pos,
				(self.device_id, "target_vel"): vel,
				(self.device_id, "target_acc"): accell,
				(self.device_id, "target_deacc"): deaccell,
				(self.device_id, "START"): None
			}
			# Emit the parameters to the controller
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
		# generate stop request
		parameters = {
			(self.device_id, "STOP"): None
		}
		self.sendRequest.emit(parameters)
		return

	@Slot(object)
	def get_update(self, parameters: Dict[tuple, Any]) -> None:
		"""
		Gets updated parameters from the controller and shows them in the UI.
		:param parameters: Parameters from the controller.
		:type parameters: Dict[str, Any]
		:return: None
		"""
		# define supported parameters and their corresponding UI elements
		supproted_parameters = {
			"target_pos": "out_target_position",
			"target_vel": "in_speed",
			"current_pos": "out_current_position",
			"error_code": "out_error_code"
		}
		# update UI elements with received parameters
		for key, parameter in parameters.items():
			if not key[1] in supproted_parameters:
				pass
			else:
				# get the corresponding widget
				widget = getattr(self, supproted_parameters[key[1]])
				# update the widget with the new parameter value
				widget.setText(str(parameter))
		return

	@Slot()
	def _send_update(self) -> None:
		"""
		Sends updated parameters to the controller
		:return: None
		"""
		# Read and format input values
		speed = self.in_speed.text().replace(",", ".")
		pos = self.in_new_position.text().replace(",", ".")

		# Update the target position output field
		self.out_target_position.clear()
		self.out_target_position.setText(pos)

		# Create update dictionary and emit it to the MainWindow
		update = {
			(self.device_id, "target_pos"): pos,
			(self.device_id, "target_vel"): speed,
		}
		self.sendUpdate.emit(update, "normal")
		return