from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QCheckBox, QLabel, QSpacerItem

from Classes.Widgets.fields import _create_input_field, _create_combo_box
from src.utils import UIParameterError


class LaserWidgetExpert(QWidget):
	apply_signal = Signal(float, int, bool)

	modulation_modes = ["Standby", "CW", "Digital", "Analog"]
	control_modes = ["ACC", "APC"]

	def __init__(self, index, max_power=1) -> None:
		super().__init__()
		self.index = index
		self.max_power = max_power

		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		# creating and adding widgets to layout #
		apply_button = QPushButton("Apply")
		self.if_active = QCheckBox("Set active")

		self.laser_power_percent = _create_input_field(layout, "Setpoint λ-" + str(self.index), "0.0", "%", 1, 0)
		self.laser_power_percent.setValidator(QDoubleValidator())
		self.laser_power_absolute = _create_input_field(layout, "Setpoint λ-" + str(self.index), "0.0", "mW", 3,
														0)
		self.laser_power_absolute.setValidator(QDoubleValidator())


		self.operating_mode = _create_combo_box(layout, self.modulation_modes, "Modulation mode", 5, 0)

		self.control_mode = _create_combo_box(layout, self.control_modes, "Control mode", 7, 0)

		layout.addWidget(QLabel("λ-" + str(self.index)), 0, 0)
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

	@Slot()
	def _apply(self) -> None:
		temp_power = float(self.laser_power_percent.text().replace(",", "."))
		operating_mode = self.operating_mode.currentIndex()
		control_mode = self.control_mode.currentIndex()
		op_mode = self._reverse_map_modes(operating_mode, control_mode)
		emission = self.if_active.isChecked()

		self.apply_signal.emit(
			temp_power,
			op_mode,
			emission
		)

		return None

	def _calc_power(self, from_percent: bool) -> None:
		if from_percent:
			self.laser_power_absolute.clear()
			power = float(self.laser_power_percent.text().replace(",", "."))
			power = power * self.max_power / 100
			self.laser_power_absolute.setText(str(power))
			return None
		else:
			self.laser_power_percent.clear()
			power = float(self.laser_power_absolute.text().replace(",", "."))
			power = power / self.max_power * 100
			self.laser_power_percent.setText(str(power))
			return None


	def get_params(self, *argv, **kwargs) -> None:
		supported_params = {
			"temp_power": "laser_power_percent",
			"op_mode": "_map_modes",
			"max_power": "max_power",
		}
		if len(argv) == 1 and isinstance(argv[0], dict):
			kwargs.update(argv[0])
		elif argv:
			raise TypeError("Only dict or named parameters accepted!")

		for param, value in kwargs.items():
			if param not in supported_params:
				raise UIParameterError(param)
			if param == "max_power":
				self.max_power = value
				continue
			if param == "op_mode":
				self._map_modes(value)
			else:
				widget = getattr(self, supported_params[param])
				widget.clear()
				widget.insert(str(value))
				self._calc_power(True)

	def _map_modes(self, op_mode) -> None:
		if op_mode == 0:
			self.operating_mode.setCurrentIndex(0)
			self.control_mode.setCurrentIndex(0)
		elif op_mode == 1:
			self.operating_mode.setCurrentIndex(1)
			self.control_mode.setCurrentIndex(0)
		elif op_mode == 2:
			self.operating_mode.setCurrentIndex(1)
			self.control_mode.setCurrentIndex(1)
		elif op_mode == 3:
			self.operating_mode.setCurrentIndex(2)
			self.control_mode.setCurrentIndex(0)
		else:
			self.operating_mode.setCurrentIndex(3)
			self.control_mode.setCurrentIndex(0)

	@staticmethod
	def _reverse_map_modes(op_mode, control_mode) -> int:
		if op_mode == 0:
			return 0
		elif op_mode == 1:
			if control_mode == 0:
				return 1
			else:
				return 2
		elif op_mode == 2:
			return 3
		else:
			return 4



