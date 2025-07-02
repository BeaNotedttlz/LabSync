from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QDoubleValidator, Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QCheckBox, QSpacerItem, QLabel, QMessageBox

from Classes.Widgets.fields import _create_input_field, _create_output_field
from exceptions import UIParameterError, DeviceParameterError, ParameterOutOfRangeError

class StageWidgetExpert(QWidget):
	stop_signal = Signal()
	start_signal = Signal(float, float, float, float)

	def __init__(self) -> None:
		super().__init__()

		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		start_button = QPushButton("Start")
		stop_button = QPushButton("Stop")
		send_control_word = QPushButton("Send \n control word")
		self.sync = QCheckBox("Sync Accel. \n and Deaccel.")
		self.sync.setChecked(True)
		show_control_word = QPushButton("Get control word")

		layout.addWidget(QLabel("Stage Controls"), 0, 0)
		self.out_current_position = _create_output_field(layout, "Current position", "0.0", "mm", 1, 0)
		self.out_target_position = _create_output_field(layout, "Target position", "0.0", "mm", 3, 0)
		self.in_new_position = _create_input_field(layout, "New position", "0.0", "mm", 5, 0)
		self.in_new_position.setValidator(QDoubleValidator())
		self.in_speed = _create_input_field(layout, "Speed", "25.0", "mm/s", 7, 0)
		self.in_speed.setValidator(QDoubleValidator())
		layout.addItem(QSpacerItem(10, 100), 9, 0)
		layout.addWidget(start_button, 10, 0)
		layout.addWidget(stop_button, 11, 0)

		layout.addItem(QSpacerItem(200, 10), 0, 1)

		self.in_accell = _create_input_field(layout, "Acceleration", "501.30", "mm/s^2", 1, 2)
		self.in_accell.setValidator(QDoubleValidator())
		self.in_deaccell = _create_input_field(layout, "Deacceleration", "501.30", "mm/s^2", 3, 2)
		self.in_deaccell.setValidator(QDoubleValidator())
		self.in_control_word = _create_input_field(layout, "Control word", "0x3F", "", 7, 2)
		self.out_error_code = _create_output_field(layout, "Error code", "", "", 10, 2)
		self.out_error_code.setAlignment(Qt.AlignLeft)

		layout.addWidget(send_control_word, 9, 2)
		layout.addWidget(self.sync, 5, 2)
		layout.addWidget(show_control_word, 8, 3)
		self.setLayout(layout)

		# signal routing #
		stop_button.clicked.connect(self.stop_signal.emit)
		start_button.clicked.connect(self._start)
		self.in_new_position.returnPressed.connect(self._write_target_pos)

	@Slot()
	def _write_target_pos(self) -> None:
		self.out_target_position.clear()
		self.out_target_position.setText(self.in_new_position.text())
		return None

	def get_params(self, **kwargs) -> None:
		supported_params = {
			"position" : "out_target_position",
			"speed" : "in_speed",
			"accell" : "in_accell",
			"deaccell": "in_deaccell",
		}

		for param, value in kwargs.items():
			if param not in supported_params:
				raise UIParameterError(param)

			widget = getattr(self, supported_params[param])
			widget.setText(value)
		return None

	@Slot()
	def _start(self) -> None:
		try:
			pos = float(self.out_target_position.text().replace(",", "."))
			speed = float(self.in_speed.text().replace(",", "."))
			accell = float(self.in_accell.text().replace(",", "."))
			deaccell = float(self.in_deaccell.text().replace(",", "."))

			self.start_signal.emit(
				pos,
				speed,
				accell,
				deaccell
			)
		except DeviceParameterError as e:
			print(e)
			return None
		except ParameterOutOfRangeError as e:
			QMessageBox.information(
				self,
				"Parameter out of range",
				str(e)
			)
			return None
