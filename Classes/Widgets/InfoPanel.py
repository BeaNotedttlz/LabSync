from PySide6.QtCore import Signal, Qt, Slot
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QLabel, QFrame

class InfoPanelWidget(QWidget):
	laser_info_signal = Signal()
	stage_port_signal = Signal(bool)
	freq_gen_port_signal = Signal(bool)
	laser1_port_signal = Signal(bool)
	laser2_port_signal = Signal(bool)
	fsv_port_signal = Signal(bool)

	def __init__(self) -> None:
		super().__init__()
		self.info_states = {
			0: ["Moving", "Not Moving"],
			1: ["Emission off", "Emission on"],
			2: ["Closed", "Open", "Error"]
		}
		self.indicators = {}

		self.layout = QGridLayout()
		self.layout.setVerticalSpacing(5)

		laser_button = QPushButton("Laser info")
		laser_button.clicked.connect(self.laser_info_signal.emit)

		self._create_status_indicator("EcoVarioStatus", "Stage :", self.info_states[0], 0, 0)
		self._create_status_indicator("Laser1Status", "Laser 1:", self.info_states[1], 1, 0)
		self._create_status_indicator("Laser2Status", "Laser 2:", self.info_states[1], 2, 0)
		self.layout.addWidget(laser_button, 3, 0)

		self._create_port_indicator("EcoVarioPort", "EcoVario port:", self.info_states[2], 4, 0)
		self._create_port_indicator("TGAPort", "TGA 1244 port:", self.info_states[2], 6, 0)
		self._create_port_indicator("Laser1Port", "Laser 1 port", self.info_states[2], 8, 0)
		self._create_port_indicator("Laser2Port", "Laser 2 port:", self.info_states[2], 10, 0)
		self._create_port_indicator("FsvPort", "FSV3000 Port:", self.info_states[2], 12, 0)
		self.setLayout(self.layout)

		self.indicators["EcoVarioPort"]["buttons"][0].clicked.connect(lambda: self.stage_port_signal.emit(True))
		self.indicators["EcoVarioPort"]["buttons"][1].clicked.connect(lambda: self.stage_port_signal.emit(False))

		self.indicators["TGAPort"]["buttons"][0].clicked.connect(lambda: self.freq_gen_port_signal.emit(True))
		self.indicators["TGAPort"]["buttons"][1].clicked.connect(lambda: self.freq_gen_port_signal.emit(False))

		self.indicators["Laser1Port"]["buttons"][0].clicked.connect(lambda: self.laser1_port_signal.emit(True))
		self.indicators["Laser1Port"]["buttons"][1].clicked.connect(lambda: self.laser1_port_signal.emit(False))
		self.indicators["Laser2Port"]["buttons"][0].clicked.connect(lambda: self.laser2_port_signal.emit(True))
		self.indicators["Laser2Port"]["buttons"][1].clicked.connect(lambda: self.laser2_port_signal.emit(False))

		self.indicators["FsvPort"]["buttons"][0].clicked.connect(lambda: self.fsv_port_signal.emit(True))
		self.indicators["FsvPort"]["buttons"][1].clicked.connect(lambda: self.fsv_port_signal.emit(False))

	def _create_status_indicator(self, name: str, label: str, status: list, row: int, column: int) -> None:
		label = QLabel(label)
		label.setAlignment(Qt.AlignRight)
		status_label = QLabel(status[0])
		indicator = QFrame()
		indicator.setFixedSize(14, 14)
		indicator.setStyleSheet("background-color: red")

		self.layout.addWidget(label, row, column)
		self.layout.addWidget(indicator, row, column + 1, alignment=Qt.AlignRight)
		self.layout.addWidget(status_label, row, column + 2)

		indicator_data = {
			"frame": indicator,
			"status": status_label,
			"text": status
		}

		self.indicators[name] = indicator_data
		return None

	def _create_port_indicator(self, name: str, label: str, status: list, row: int, column: int) -> None:
		label = QLabel(label)
		label.setAlignment(Qt.AlignRight)
		status_label = QLabel(status[0])
		indicator = QFrame()
		indicator.setFixedSize(14, 14)
		indicator.setStyleSheet("background-color: red")

		open_button = QPushButton("Open")
		open_button.setFixedSize(60, 30)
		close_button = QPushButton("Close")
		close_button.setFixedSize(60, 30)

		self.layout.addWidget(label, row, column)
		self.layout.addWidget(indicator, row, column + 1, alignment=Qt.AlignRight)
		self.layout.addWidget(status_label, row, column + 2)
		self.layout.addWidget(open_button, row + 1, column)
		self.layout.addWidget(close_button, row + 1, column + 1)

		indicator_data = {
			"frame": indicator,
			"status": status_label,
			"text": status,
			"buttons": [open_button, close_button]
		}

		self.indicators[name] = indicator_data
		return None

	@Slot(str, bool)
	def update_indicator(self, name: str, state: bool) -> None:
		current_indicator = self.indicators[name]
		if state:
			current_indicator["frame"].setStyleSheet("background-color: green")
			current_indicator["status"].setText(current_indicator["text"][1])
			return None
		else:
			current_indicator["frame"].setStyleSheet("background-color: red")
			current_indicator["status"].setText(current_indicator["text"][0])
			return None