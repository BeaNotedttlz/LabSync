import os

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QWidget, QSpacerItem, QLabel, QPushButton, QGridLayout, QMessageBox, QComboBox, \
	QFileDialog

from Classes.Widgets.fields import _create_input_field, _create_combo_box
from Exceptions import UIParameterError
from os import path
from pathlib import Path


class FsvNormalWidget(QWidget):
	start_signal = Signal(str, str, str, float, float, str, float, str, int, int)

	sweep_types = ["Sweep", "FFT"]
	meas_types = ["Single", "Average"]
	units = ["dBm", "dBmV"]

	def __init__(self):
		super().__init__()
		self.file_path = os.path.join(Path.home(), "Documents")
		start_button = QPushButton("Start")

		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		layout.addWidget(QLabel("FSV Controls"), 0, 0)
		self.center_frequency = _create_input_field(layout, "Center Frequency", "1000.0", "Hz", 1, 0)
		self.center_frequency.setValidator(QDoubleValidator())
		self.span = _create_input_field(layout, "Span", "1000.0", "Hz", 3, 0)
		self.span.setValidator(QDoubleValidator())
		self.bandwidth = _create_input_field(layout, "Bandwidth", "100.0", "Hz", 5, 0)
		self.bandwidth.setValidator(QDoubleValidator())
		self.sweep_points = _create_input_field(layout, "Sweep points", "2001", "", 3, 2)
		self.sweep_points.setValidator(QDoubleValidator())
		self.sweep_type = _create_combo_box(layout, self.sweep_types, "Sweep type", 1, 2)
		self.meas_type = _create_combo_box(layout, self.meas_types, "Measurement type", 8, 2)
		self.avg_count = _create_input_field(layout, "Average count", "64", "", 10, 2)
		self.unit = _create_combo_box(layout, self.units, "Unit", 5, 2)

		layout.addItem(QSpacerItem(200, 10), 0, 1)
		layout.addItem(QSpacerItem(10, 70), 7, 0)
		layout.addWidget(start_button, 8, 0)
		# self.save_path = _create_input_field(layout, "Save path", "", "", 9, 0)
		save_button = QPushButton("Select save path")
		layout.addWidget(save_button, 9, 0)
		self.fig_name = _create_input_field(layout, "Figure name", "", "", 11, 0)
		self.fig_name.setAlignment(Qt.AlignLeft)
		fig_text = QLabel("Leave this empty to not save Figure from Data")
		fig_text.setAlignment(Qt.AlignLeft)
		layout.addWidget(fig_text, 12, 1)

		self.setLayout(layout)
		start_button.clicked.connect(self._start_measurement)
		self.meas_type.currentIndexChanged.connect(self._toggle_avg_count)
		self._toggle_avg_count(self.meas_type.currentIndex())
		save_button.clicked.connect(self._get_save_path)

	def get_params(self, *argv, **kwargs) -> None:
		supported_params = {
			"center_frequency": "center_frequency",
			"span": "span",
			"bandwidth": "bandwidth",
			"sweep_points": "sweep_points",
			"sweep_type": "sweep_type",
			"meas_type": "meas_type",
			"unit": "unit",
		}

		#TODO meas_type is not stored in storage, so it is not saved into file
		# This means it cant be loaded from file! -> FIX!!!!!

		if len(argv) == 1 and isinstance(argv[0], dict):
			kwargs.update(argv[0])
		elif argv:
			raise TypeError("Only dict or named parameters accepted!")

		for param, value in kwargs.items():
			if param not in supported_params:
				raise UIParameterError(param)
			if param == "sweep_type":
				idx = self._map_sweep_type(value)
				self.sweep_type.setCurrentIndex(idx)
			elif param == "meas_type":
				idx = self._map_meas_type(value)
				self.meas_type.setCurrentIndex(idx)
			elif param == "unit":
				idx = self._map_unit(value)
				self.unit.setCurrentIndex(idx)
			else:
				widget = getattr(self, supported_params[param])
				widget.setText(str(value))

	def _start_measurement(self) -> None:
		center_frequency = float(self.center_frequency.text().replace(",", "."))
		span = float(self.span.text().replace(",", "."))
		bandwidth = float(self.bandwidth.text().replace(",", "."))
		sweep_points = int(self.sweep_points.text())
		avg_count = int(self.avg_count.text())
		sweep_type = self.sweep_types[self.sweep_type.currentIndex()]
		meas_type = self.meas_types[self.meas_type.currentIndex()]
		unit = self.units[self.unit.currentIndex()]
		save_path = self.file_path
		fig_name = self.fig_name.text()

		self.start_signal.emit(
			meas_type,
			fig_name,
			save_path,
			center_frequency,
			span,
			sweep_type,
			bandwidth,
			unit,
			sweep_points,
			avg_count
		)

	def _toggle_avg_count(self, index: int) -> None:
		if self.meas_types[index] == "Average":
			self.avg_count.show()
		else:
			self.avg_count.hide()

	def _get_save_path(self) -> None:
		file_path = QFileDialog.getExistingDirectory(
		    self,
		    "Select Directory",
		)
		if file_path:
			self.file_path = file_path

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



