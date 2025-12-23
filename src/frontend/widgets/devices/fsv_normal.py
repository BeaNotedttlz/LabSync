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
	sendRequest = Signal(object)
	saveDataRequest = Signal(object)

	sweep_types = ["Sweep", "FFT"]
	meas_types = ["Single", "Average"]
	units = ["dBm", "dBmV"]

	def __init__(self, device_id: str) -> None:
		super().__init__()
		self.device_id = device_id

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
		start_button.clicked.connect(self._start_measurement)
		self.meas_type.currentIndexChanged.connect(self._toggle_avg_count)
		self._toggle_avg_count(self.meas_type.currentIndex())
		return

	@Slot()
	def _start_measurement(self) -> None:
		center_frequency = float(self.center_frequency.text().replace(",", "."))
		span = float(self.span.text().replace(",", "."))
		bandwidth = float(self.bandwidth.text().replace(",", "."))
		sweep_points = int(self.sweep_points.text())
		avg_count = int(self.avg_count.text())
		sweep_type = self.sweep_types[self.sweep_type.currentIndex()]
		meas_type = self.meas_types[self.meas_type.currentIndex()]
		unit = self.units[self.unit.currentIndex()]

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
		if self.meas_types[index] == "Average":
			self.avg_count.show()
		else:
			self.avg_count.hide()
		return

	@Slot()
	def _get_save_path(self) -> None:
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
		supported_params = {
			"center_frequency": "center_frequency",
			"span": "span",
			"bandwidth": "bandwidth",
			"sweep_points": "sweep_points",
			"sweep_type": "sweep_type",
			"meas_type": "meas_type",
			"unit": "unit",
		}
		for key, parameter in parameters.items():
			if not key[1] in supported_params:
				pass
			else:
				if key[1] == "sweep_type":
					idx = self._map_sweep_type(parameter)
					self.sweep_type.setCurrentIndex(idx)
				elif key[1] == "meas_type":
					idx = self._map_meas_type(parameter)
					self.meas_type.setCurrentIndex(idx)
				elif key[1] == "unit":
					idx = self._map_unit(parameter)
					self.unit.setCurrentIndex(idx)
				else:
					widget = getattr(self, supported_params[key[1]])
					widget.clear()
					widget.setText(parameter)
			return

	@staticmethod
	def _map_sweep_type(value: str) -> int:
		if value == "Sweep":
			return 0
		else:
			return 1

	@staticmethod
	def _map_meas_type(value: str) -> int:
		if value == "single":
			return 0
		else:
			return 1

	@staticmethod
	def _map_unit(value: str) -> int:
		if value == "dBm":
			return 0
		else:
			return 1


