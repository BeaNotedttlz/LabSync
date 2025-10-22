from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QSpacerItem, QGridLayout, QCheckBox
from Classes.Widgets.fields import _create_input_field

class LaserInfoWidget(QWidget):
	def __init__(
			self,
			firmware=[["","",""],["","",""]],
			specs=["",""],
			max_power=["",""],
			error_byte=["Not connected","Not connected"],
	) -> None:
		super().__init__()
		layout = QGridLayout()
		layout.setVerticalSpacing(10)
		self.setWindowTitle("Laser Info")
		self.setMinimumSize(600, 400)

		for i in [1, 2]:
			layout.addWidget(QLabel("Laser %d: " % i), 0, i - 1 if i == 1 else i + 1)
			layout.addWidget(QLabel("Model code: "), 1, i - 1 if i == 1 else i + 1)
			layout.addWidget(QLabel("Device id: "), 2, i - 1 if i == 1 else i + 1)
			layout.addWidget(QLabel("Firmware version: "), 3, i - 1 if i == 1 else i + 1)
			layout.addWidget(QLabel("Wavelenght: "), 4, i - 1 if i == 1 else i + 1)
			layout.addWidget(QLabel("Max power: "), 5, i - 1 if i == 1 else i + 1)
			layout.addWidget(QLabel("Status: "), 6, i - 1 if i == 1 else i + 1)

		layout.addWidget(QLabel(firmware[0][0]), 1, 1)
		layout.addWidget(QLabel(firmware[0][1]), 2, 1)
		layout.addWidget(QLabel(firmware[0][2]), 3, 1)
		layout.addWidget(QLabel(specs[0][0]), 4, 1)
		layout.addWidget(QLabel(str(max_power[0])), 5, 1)
		layout.addWidget(QLabel(error_byte[0]), 6, 1)

		layout.addWidget(QLabel(firmware[1][0]), 1, 4)
		layout.addWidget(QLabel(firmware[1][1]), 2, 4)
		layout.addWidget(QLabel(firmware[1][2]), 3, 4)
		layout.addWidget(QLabel(specs[1][0]), 4, 4)
		layout.addWidget(QLabel(str(max_power[1])), 5, 4)
		layout.addWidget(QLabel(error_byte[1]), 6, 4)

		self.setLayout(layout)

class PortSelectionWidget(QWidget):
	apply_signal = Signal(str, str, str, str, str)
	default_signal = Signal(str, str, str, str, str)

	def __init__(
			self,
			stage_port,
			freq_gen_port,
			laser1_port,
			laser2_port,
			fsv_port,
			parent=None
	) -> None:
		super().__init__(parent, Qt.Window)
		layout = QGridLayout()
		layout.setVerticalSpacing(10)
		self.setWindowTitle("Port Selection")
		self.setMinimumSize(300, 400)

		self.stage_port = _create_input_field(layout, "EcoVatio Port:", stage_port, "", 0, 0)
		self.stage_port.setAlignment(Qt.AlignLeft)
		self.freq_gen_port = _create_input_field(layout, "TGA 1244 Port:", freq_gen_port, "", 2, 0)
		self.freq_gen_port.setAlignment(Qt.AlignLeft)
		self.laser1_port = _create_input_field(layout, "Laser 1 Port:", laser1_port, "", 4, 0)
		self.laser1_port.setAlignment(Qt.AlignLeft)
		self.laser2_port = _create_input_field(layout, "Laser 2 Port:", laser2_port, "", 6, 0)
		self.laser2_port.setAlignment(Qt.AlignLeft)
		self.fsv_port = _create_input_field(layout, "FSV Port:", fsv_port, "", 8, 0)
		self.fsv_port.setAlignment(Qt.AlignLeft)

		apply_button = QPushButton("Apply")
		def_button = QPushButton("Set as default")

		layout.addItem(QSpacerItem(100, 10), 7, 0)
		layout.addWidget(apply_button, 10, 0)
		layout.addWidget(def_button, 10, 1)

		self.setLayout(layout)
		apply_button.clicked.connect(self._apply_ports)
		def_button.clicked.connect(self._set_default)

	@Slot()
	def _apply_ports(self) -> None:
		stage = self.stage_port.text()
		freq_gen = self.freq_gen_port.text()
		laser1 = self.laser1_port.text()
		laser2 = self.laser2_port.text()
		fsv = self.fsv_port.text()

		self.apply_signal.emit(stage, freq_gen, laser1, laser2, fsv)
		return None

	@Slot()
	def _set_default(self) -> None:
		stage = self.stage_port.text()
		freq_gen = self.freq_gen_port.text()
		laser1 = self.laser1_port.text()
		laser2 = self.laser2_port.text()
		fsv = self.fsv_port.text()

		self.default_signal.emit(stage, freq_gen, laser1, laser2, fsv)
		return None

class SettingsWidget(QWidget):
	apply_signal = Signal(str, bool)
	def __init__(self,username: str, debug_mode: bool, parent=None) -> None:
		super().__init__()
		layout = QGridLayout()
		layout.setVerticalSpacing(10)
		self.setWindowTitle("Port Selection")
		self.setMinimumSize(300, 150)

		self.username = username
		self.debug_mode = debug_mode

		self.username_input = _create_input_field(layout, "Username:", username, "", 0, 0)
		self.username_input.setAlignment(Qt.AlignLeft)
		self.debug_mode_box = QCheckBox("Debug Mode")
		self.apply_button = QPushButton("Apply")

		layout.addItem(QSpacerItem(10, 100), 4, 0)
		layout.addWidget(self.debug_mode_box, 5, 0)
		layout.addWidget(self.apply_button, 6, 0)

		self.setLayout(layout)
		self.apply_button.clicked.connect(self._apply)

	@Slot()
	def _apply(self) -> None:
		username = self.username_input.text()
		debug_mode = self.debug_mode_box.isChecked()

		self.apply_signal.emit(username, debug_mode)
		return None
