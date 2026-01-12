"""
Module for creating and operating the PySide6 FSV3000 normal mode widgets.
@author: Merlin Schmidt
@date: 2025-24-10
@file: src/frontend/widgets/devices/fsv_normal.py
@note:
"""
from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (QWidget, QGridLayout,
							   QPushButton, QSpacerItem,
							   QLabel, QFileDialog, QMessageBox)

from src.frontend.widgets.utilities import create_input_field, create_combo_box
from typing import Dict, Any

class FsvNormalWidget(QWidget):
	"""
	Create FSV3000 normal mode widgets and functionality.
	"""
	# Request signal to send parameters to device handler
	sendRequest = Signal(object)
	# Signal to send data to be saved
	saveDataRequest = Signal(object)

	# Define possible device parameter options for combo boxes
	sweep_types = ["Sweep", "FFT"]
	meas_types = ["Single", "Average"]
	units = ["dBm", "dBmV"]

	def __init__(self, device_id: str) -> None:
		"""Constructor method
		"""
		super().__init__()
		# Store device ID
		self.device_id = device_id

		# creating and adding widgets to layout
		start_button = QPushButton("Start")
		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		layout.addWidget(QLabel("FSV Controls"), 0, 0)
		self.center_frequency = create_input_field(layout, "Center Frequency", "1000.0", "Hz", 1, 0)
		self.center_frequency.setValidator(QDoubleValidator())
		self.span = create_input_field(layout, "Span", "1000.0", "Hz", 3, 0)
		self.span.setValidator(QDoubleValidator())
		self.bandwidth = create_input_field(layout, "Bandwidth", "100.0", "Hz", 5, 0)
		self.bandwidth.setValidator(QDoubleValidator())
		self.sweep_points = create_input_field(layout, "Sweep points", "2001", "", 3, 2)
		self.sweep_points.setValidator(QDoubleValidator())
		self.sweep_type = create_combo_box(layout, self.sweep_types, "Sweep type", 1, 2)
		self.meas_type = create_combo_box(layout, self.meas_types, "Measurement type", 8, 2)
		self.avg_count = create_input_field(layout, "Average count", "64", "", 10, 2)
		self.unit = create_combo_box(layout, self.units, "Unit", 5, 2)

		layout.addItem(QSpacerItem(200, 10), 0, 1)
		layout.addItem(QSpacerItem(10, 70), 7, 0)
		layout.addWidget(start_button, 8, 0)

		self.setLayout(layout)
		# Connect button and combo box signals to their respective slots
		start_button.clicked.connect(self._start_measurement)
		self.meas_type.currentIndexChanged.connect(self._toggle_avg_count)
		self._toggle_avg_count(self.meas_type.currentIndex())
		return

	@Slot()
	def _start_measurement(self) -> None:
		"""
		Start measurement with current parameters
		:return: None
		"""
		# Retrieve and process input values, converting as necessary
		center_frequency = float(self.center_frequency.text().replace(",", "."))
		span = float(self.span.text().replace(",", "."))
		bandwidth = float(self.bandwidth.text().replace(",", "."))
		sweep_points = int(self.sweep_points.text())
		avg_count = int(self.avg_count.text())
		sweep_type = self.sweep_types[self.sweep_type.currentIndex()]
		meas_type = self.meas_types[self.meas_type.currentIndex()]
		unit = self.units[self.unit.currentIndex()]

		# Create parameter dictionary to send as request
		parameters = {
			(self.device_id,"center_freq"): center_frequency,
			(self.device_id,"freq_span"): span,
			(self.device_id,"bandwidth"):bandwidth,
			(self.device_id,"unit"): unit,
			(self.device_id,"sweep_type"): sweep_type,
			(self.device_id,"sweep_points"): sweep_points,
			(self.device_id,"avg_count"): avg_count,
			(self.device_id,"measurement_type"): meas_type
		}
		self.sendRequest.emit(parameters)
		return

	@Slot()
	def _toggle_avg_count(self, index: int) -> None:
		"""
		Helper method to show/hide average count input based on measurement type.
		:param index:
		:return:
		"""
		if self.meas_types[index] == "Average":
			# For average measurement, show average count input
			self.avg_count.show()
		else:
			# For single measurement, hide average count input
			self.avg_count.hide()
		return

	@Slot()
	def _get_save_path(self) -> None:
		"""
		Helper method to get save directory from user.
		:return: None
		"""
		# TODO: This is not necessary anymore since this will be implemented in the controller
		file_path = QFileDialog.getExistingDirectory(
		    self,
		    "Select Directory",
		)
		if file_path:
			self.file_path = file_path
			return
		else:
			QMessageBox.warning(self, "Warning", "Please select a directory")
			return

	@Slot(dict)
	def get_update(self, parameters: Dict[tuple, Any]) -> None:
		"""
		Gets updated parameters from the controller and shows them in the UI.
		:param parameters: Updated parameters from the controller
		:type parameters: Dict[str, Any]
		:return: None
		"""
		# Define supported parameters and their corresponding UI elements
		supported_params = {
			"center_frequency": "center_frequency",
			"span": "span",
			"bandwidth": "bandwidth",
			"sweep_points": "sweep_points",
			"sweep_type": "sweep_type",
			"meas_type": "meas_type",
			"unit": "unit",
		}
		# Iterate through received parameters and update UI accordingly
		for key, parameter in parameters.items():
			if not key[1] in supported_params:
				pass
			else:
				if key[1] == "sweep_type":
					# Map and set sweep type index
					idx = self._map_sweep_type(parameter)
					self.sweep_type.setCurrentIndex(idx)
				elif key[1] == "meas_type":
					# Map and set measurement type index
					idx = self._map_meas_type(parameter)
					self.meas_type.setCurrentIndex(idx)
				elif key[1] == "unit":
					# Map and set unit index
					idx = self._map_unit(parameter)
					self.unit.setCurrentIndex(idx)
				else:
					# Update text fields for other parameters
					widget = getattr(self, supported_params[key[1]])
					# Clear and set new value
					widget.clear()
					widget.setText(parameter)
			return

	@staticmethod
	def _map_sweep_type(value: str) -> int:
		"""
		Helper method to map sweep type string to corresponding index.
		:param value: Name of sweep type
		:type value: str
		:return: The corresponding index in the UI
		:rtype: int
		"""
		if value == "Sweep":
			return 0
		else:
			return 1

	@staticmethod
	def _map_meas_type(value: str) -> int:
		"""
		Helper method to map measurement type string to corresponding index.
		:param value: Name of measurement type
		:type value: str
		:return: The corresponding index in the UI
		:rtype: int
		"""
		if value == "single":
			return 0
		else:
			return 1

	@staticmethod
	def _map_unit(value: str) -> int:
		"""
		Helper method to map unit string to corresponding index.
		:param value: Name of unit
		:type value: str
		:return: The corresponding index in the UI
		:rtype: int
		"""
		if value == "dBm":
			return 0
		else:
			return 1


