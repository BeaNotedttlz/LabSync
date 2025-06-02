from PySide6.QtWidgets import QLabel, QLineEdit, QComboBox, QWidget, QPushButton, QGridLayout, QSpacerItem, QSpinBox, QCheckBox, QFrame
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QDoubleValidator

# Function for creating outfield widgets #
def _create_output_field(layout, name: str, init_value: str, unit: str, row: int, column: int) -> QLabel:
	main_label = QLabel(init_value)
	main_label.setAlignment(Qt.AlignRight)
	main_label.setStyleSheet("QLabel{border:2px solid grey;}")
	main_label.setFixedHeight(22)

	secondary_label = QLabel(unit)
	name_label = QLabel(name)

	layout.addWidget(name_label, row, column)
	layout.addWidget(main_label, row+1, column)
	layout.addWidget(secondary_label, row+1, column+1)

	return main_label

# Function for creating inputfield widgets #
def _create_input_field(layout, name: str, init_value: str, unit: str, row: int, column: int) -> QLineEdit:
	main_line = QLineEdit(init_value)
	main_line.setAlignment(Qt.AlignRight)

	unit_label = QLabel(unit)
	name_label = QLabel(name)

	layout.addWidget(name_label, row, column)
	layout.addWidget(main_line, row+1, column)
	layout.addWidget(unit_label, row+1, column+1)

	return main_line

# Function for creating combobox widgets #
def _create_combo_box(layout, items: list, name:str, row: int, column: int) -> QComboBox:
	combo_box = QComboBox()
	combo_box.addItems(items)

	name_label = QLabel(name)

	layout.addWidget(name_label, row, column)
	layout.addWidget(combo_box, row+1, column)

	return combo_box

## Class for creating EcoVario normal widget ##
class StageWidgetNormal(QWidget):
	# creating signals #
	storage_update_signal = Signal(float, float, float, float)
	start_signal = Signal()
	stop_signal = Signal()

	def __init__(self) -> None:
		super().__init__()
		# create buttons #
		start_button = QPushButton("Start")
		stop_button = QPushButton("Stop")

		# creating layout #
		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		# creating and adding widgets to layout #
		layout.addWidget(QLabel("Stage Controls"), 0, 0)
		self.current_position = _create_output_field(layout, "Current position", "0.0", "mm", 1, 0)
		self.target_position = _create_output_field(layout, "Target position", "0.0", "mm", 3, 0)
		self.new_position = _create_input_field(layout, "New position", "0.0", "mm", 5, 0)
		self.new_position.setValidator(QDoubleValidator())
		self.speed = _create_input_field(layout, "Speed", "25.0", "mm/s", 7, 0)
		self.speed.setValidator(QDoubleValidator())
		layout.addItem(QSpacerItem(10,100), 9, 0)
		layout.addWidget(start_button, 10, 0)
		layout.addWidget(stop_button, 11, 0)
		layout.addItem(QSpacerItem(10, 40), 12, 0)
		self.error_code = _create_output_field(layout, "Error code", "", "", 13, 0)
		self.error_code.setAlignment(Qt.AlignLeft)

		self.setLayout(layout)

		# Signal handling #
		start_button.clicked.connect(lambda: self._update_storage(True))
		stop_button.clicked.connect(lambda: self.stop_signal.emit())
		self.new_position.returnPressed.connect(lambda: self._write_new_pos())
		#self.speed.editingFinished.connect(lambda: self._update_storage(False))

	# Slot for wiring new postion on return press #
	@Slot()
	def _write_new_pos(self) -> None:
		self.target_position.clear()
		self.target_position.setText(self.new_position.text())

		self._update_storage(False)

	# Slot for writing to storage module and starting stage #
	@Slot(bool)
	def _update_storage(self, start_button: bool) -> None:
		target_position = float(self.target_position.text().replace(',', '.'))
		speed = float(self.speed.text().replace(',', '.'))

		self.storage_update_signal.emit(target_position, speed, 501.30, 501.30)

		if start_button:
			self.start_signal.emit()

	# Function for getting values from storage mdoule #
	def _get_storage(self, parameter_name: str, value: float) -> None:
		if parameter_name == "target_position":
			self.target_position.clear()
			self.target_position.setText(str(value))
		elif parameter_name == "speed":
			self.speed.clear()
			self.speed.setText(str(value))

## Class for creating normal laser widget ##
class LaserWidgetNormal(QWidget):
	# creating signals #
	storage_update_signal_laser1 = Signal(float, int, int, bool)
	storage_update_signal_laser2 = Signal(float, int, int, bool)
	storage_update_signal_freq = Signal(int, int, int, int, float, float, float, float, int, int, bool, bool)

	def __init__(self) -> None:
		super().__init__()
		# creating layout #
		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		# creating and adding widgets to layout #
		modulation_modes = ["Standby", "CW", "Analog", "Digital"]
		self.modulation1 = _create_combo_box(layout, modulation_modes, "Modulation mode", 1, 0)
		self.modulation2 = _create_combo_box(layout, modulation_modes, "Modulation mode", 1, 2)

		control_modes = ["ACC", "APC"]
		self.control_mode1 = _create_combo_box(layout, control_modes, "Control mode", 3, 0)
		self.control_mode2 = _create_combo_box(layout, control_modes, "Control mode", 3, 2)

		self.spinbox1 = QSpinBox()
		self.spinbox1.setMinimum(5)
		self.spinbox1.setMaximum(100)
		self.spinbox1.setSingleStep(5)
		self.spinbox1.setAlignment(Qt.AlignRight)

		self.spinbox2 = QSpinBox()
		self.spinbox2.setMinimum(5)
		self.spinbox2.setMaximum(100)
		self.spinbox2.setSingleStep(5)
		self.spinbox2.setAlignment(Qt.AlignRight)

		self.frequency1 = _create_input_field(layout, "Modulation frequency", "0.0", "Hz", 7, 0)
		self.frequency1.setValidator(QDoubleValidator())
		self.frequency2 = _create_input_field(layout, "Modulation frequency", "0,0", "Hz", 7, 2)
		self.frequency2.setValidator(QDoubleValidator())

		lockmodes = ["indep", "master", "slave", "off"]
		self.lockmode1 = _create_combo_box(layout, lockmodes, "Lockmode", 9, 0)
		self.lockmode2 = _create_combo_box(layout, lockmodes, "Lockmode", 9, 2)

		channels = ["1", "2", "3", "4"]
		self.channel1 = _create_combo_box(layout, channels, "TGA 1244 Channel", 11, 0)
		self.channel2 = _create_combo_box(layout, channels, "TGA 1244 Channel", 11, 2)
		self.channel2.setCurrentIndex(1)

		self.if_active1 = QCheckBox("Set active \n λ-1")
		self.if_active2 = QCheckBox("Set active \n λ-2")

		apply_button = QPushButton("Apply")

		layout.addWidget(QLabel("Laser Controls"), 0, 1)
		layout.addWidget(QLabel("Power 1"), 5, 0)
		layout.addWidget(self.spinbox1, 6, 0)
		layout.addWidget(QLabel("%"), 6, 1)
		layout.addWidget(QLabel("Power 2"), 5, 2)
		layout.addWidget(self.spinbox2, 6, 2)
		layout.addWidget(QLabel("%"), 6, 3)

		layout.addItem(QSpacerItem(10, 80), 13, 0)
		layout.addWidget(self.if_active1, 14, 0)
		layout.addWidget(self.if_active2, 14, 2)
		layout.addWidget(apply_button, 15, 1)
		self.setLayout(layout)

		# signal handling #
		apply_button.clicked.connect(self._update_storage)

	# Slot for writing to storage module #
	@Slot()
	def _update_storage(self) -> None:
		modulation_1 = self.modulation1.currentIndex()
		modulation_2 = self.modulation2.currentIndex()
		control_mode_1 = self.control_mode1.currentIndex()
		control_mode_2 = self.control_mode2.currentIndex()

		power_1 = (self.spinbox1.value()//5)*5
		self.spinbox1.setValue(power_1)
		power_2 = (self.spinbox2.value()//5)*5
		self.spinbox2.setValue(power_2)
		frequency_1 = float(self.frequency1.text().replace(',','.'))
		frequency_2 = float(self.frequency2.text().replace(',','.'))

		channel_1 = self.channel1.currentIndex()+1
		channel_2 = self.channel2.currentIndex()+1

		lockmode_1 = self.lockmode1.currentIndex()
		lockmode_2 = self.lockmode2.currentIndex()

		if_active_1 = self.if_active1.isChecked()
		if_active_2 = self.if_active2.isChecked()

		self.storage_update_signal_laser1.emit(power_1, modulation_1, control_mode_1, if_active_1)
		self.storage_update_signal_laser2.emit(power_2, modulation_2, control_mode_2, if_active_2)
		self.storage_update_signal_freq.emit(channel_1, channel_2, modulation_1, modulation_2, power_1, power_2, frequency_1, frequency_2, lockmode_1, lockmode_2, if_active_1, if_active_2)

	# Slot for getting values from storage module #
	@Slot(int, int, int, int, float, float, float, float)
	def _get_storage(self, modulation_1: int, modulation_2: int, control_mdoe_1: int, control_mode_2: int, power_1: float, power_2: float, frequency_1: float, frequency_2: float) -> None:
		self.modulation1.setCurrentIndex(modulation_1)
		self.modulation2.setCurrentIndex(modulation_2)
		self.control_mode1.setCurrentIndex(control_mdoe_1)
		self.control_mode2.setCurrentIndex(control_mode_2)

		self.spinbox1.setValue(power_1)
		self.spinbox2.setValue(power_2)
		self.frequency1.clear()
		self.frequency1.insert(str(frequency_1))
		self.frequency2.clear()
		self.frequency2.insert(str(frequency_2))

## Class for creating expert stage widget ##
class StageWidgetExpert(QWidget):
	# creating signals #
	storage_update_signal = Signal(float, float, float, float)
	start_signal = Signal()
	stop_signal = Signal()

	def __init__(self) -> None:
		super().__init__()
		# creating layout #
		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		# creating and adding widgets to layout #
		start_button = QPushButton("Start")
		stop_button = QPushButton("Stop")
		self.send_control_word = QPushButton("Send \n control word")
		self.sync = QCheckBox("Sync Accel. \n and Deaccel.")
		self.sync.setChecked(True)
		self.show_control_word = QPushButton("Get control word")

		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		layout.addWidget(QLabel("Stage Controls"), 0, 0)
		self.current_position = _create_output_field(layout, "Current position", "0.0", "mm", 1, 0)
		self.target_position = _create_output_field(layout, "Target position", "0.0", "mm", 3, 0)
		self.new_position = _create_input_field(layout, "New position", "0.0", "mm", 5, 0)
		self.new_position.setValidator(QDoubleValidator())
		self.speed = _create_input_field(layout, "Speed", "25.0", "mm/s", 7, 0)
		self.speed.setValidator(QDoubleValidator())
		layout.addItem(QSpacerItem(10,100), 9, 0)
		layout.addWidget(start_button, 10, 0)
		layout.addWidget(stop_button, 11, 0)

		layout.addItem(QSpacerItem(200, 10), 0, 1)

		self.acceleration = _create_input_field(layout, "Acceleration", "501.30", "mm/s^2", 1, 2)
		self.acceleration.setValidator(QDoubleValidator())
		self.deacceleration = _create_input_field(layout, "Deacceleration", "501.30", "mm/s^2", 3, 2)
		self.deacceleration.setValidator(QDoubleValidator())
		self.control_word = _create_input_field(layout, "Control word", "0x3F", "", 7, 2)
		self.error_code = _create_output_field(layout, "Error code", "", "", 10, 2)

		layout.addWidget(self.send_control_word, 9, 2)
		layout.addWidget(self.sync, 5, 2)
		layout.addWidget(self.show_control_word, 8, 3)
		self.setLayout(layout)

		# signaling handling #
		start_button.clicked.connect(lambda: self._update_storage(True))
		self.new_position.returnPressed.connect(lambda: self._write_new_pos())
		stop_button.clicked.connect(lambda: self.stop_signal.emit())

	# Slot for writing new position on return press #
	@Slot()
	def _write_new_pos(self) -> None:
		self.target_position.clear()
		self.target_position.setText(self.new_position.text())

		self._update_storage(False)

	# Slot for writing to storage module and starting stage #
	@Slot(bool)
	def _update_storage(self, start_button: bool) -> None:
		target_position = float(self.target_position.text().replace(',','.'))
		speed = float(self.speed.text().replace(',','.'))
		accel = float(self.acceleration.text().replace(',','.'))

		if self.sync.isChecked():
			deaccel = accel
		else:
			deaccel = float(self.deacceleration.text().replace(',','.'))

		self.storage_update_signal.emit(target_position, speed, accel, deaccel)
		if start_button:
			self.start_signal.emit()

	# Function for getting values from storage #
	def _get_storage(self, parameter_name: str, value: float) -> None:
		if parameter_name == "target_position":
			self.target_position.clear()
			self.target_position.setText(str(value))
		elif parameter_name == "speed":
			self.speed.clear()
			self.speed.setText(str(value))
		elif parameter_name == "accel":
			self.acceleration.clear()
			self.acceleration.setText(str(value))
		else:
			self.deacceleration.clear()
			self.deacceleration.setText(str(value))

## class for creating expert Frequency generator widgets ##
class FrequencyGenWidgetExpert(QWidget):
	# creating signals #
	storage_update_signal = Signal(int, int, int, float, float, float, float, int, bool)

	def __init__(self, channel_index: int) -> None:
		super().__init__()
		self.channel_index = channel_index
		# creating layout #
		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		# creating and adding widgets to layout #
		apply_button = QPushButton("Apply")
		self.if_active = QCheckBox("Set active")

		# creating layout and adding widgets to layout #
		layout = QGridLayout()
		layout.setVerticalSpacing(15)

		waveforms = ["sine", "square", "triang", "dc"]
		self.waveform = _create_combo_box(layout, waveforms, "Waveform", 1, 0)
		inputmodes = ["Amp+Offset", "Low+High"]
		self.input_mode = _create_combo_box(layout, inputmodes, "Inputmode", 3, 0)
		self.amplitude = _create_input_field(layout, "Amp/Low", "0.0", "V", 5, 0)
		self.amplitude.setValidator(QDoubleValidator())
		self.offset = _create_input_field(layout, "Offset/High", "0.0", "V", 7, 0)
		self.offset.setValidator(QDoubleValidator())
		self.frequency = _create_input_field(layout, "Frequency", "0.0", "Hz", 9, 0)
		self.frequency.setValidator(QDoubleValidator())
		self.phase = _create_input_field(layout, "Pahse", "0.0", "Deg", 11, 0)
		self.phase.setValidator(QDoubleValidator())

		lockmodes = ["indep", "master", "slave", "off"]
		self.lockmode = _create_combo_box(layout,lockmodes, "Lockmode",13, 0)

		layout.addWidget(QLabel("Channel "+ str(channel_index) + ":"), 0, 0)
		layout.addWidget(self.if_active, 15, 0)
		layout.addWidget(apply_button, 16, 0)
		self.setLayout(layout)

		# signal handling #
		apply_button.clicked.connect(self._update_storage)

	# Slot for updating storage module #
	@Slot()
	def _update_storage(self) -> None:
		wave = self.waveform.currentIndex()
		inputmode = self.input_mode.currentIndex()
		amplitude = float(self.amplitude.text().replace(',','.'))
		offset = float(self.offset.text().replace(',','.'))
		frequency = float(self.frequency.text().replace(',','.'))
		phase = float(self.phase.text().replace(',','.'))
		lockmode = self.lockmode.currentIndex()
		if_active = self.if_active.isChecked()

		self.storage_update_signal.emit(self.channel_index, wave, inputmode, amplitude, offset, frequency, phase, lockmode, if_active)

	# Function for getting values from storage #
	def _get_storage(self, parameter_name: str, value) -> None:
		if parameter_name == "wave":
			self.waveform.setCurrentIndex(value)
		elif parameter_name == "inputmode":
			self.input_mode.setCurrentIndex(value)
		elif parameter_name == "amplitude":
			self.amplitude.clear()
			self.amplitude.setText(str(value))
		elif parameter_name == "offset":
			self.offset.clear()
			self.offset.setText(str(value))
		elif parameter_name == "frequency":
			self.frequency.clear()
			self.frequency.setText(str(value))
		elif parameter_name == "phase":
			self.phase.clear()
			self.phase.setText(str(value))
		elif parameter_name == "lockmode":
			self.lockmode.setCurrentIndex(value)
		else:
			self.if_active.setChecked(value)

## class for creating expert laser widget ##
class LaserWidgetExpert(QWidget):
	# creating signals #
	storage_update_signal = Signal(float, int, int, bool)
	apply_signal = Signal()

	def __init__(self, laser_index: int, max_power: int=1) -> None:
		super().__init__()
		self.max_power = max_power
		self.laser_index = laser_index
		# creating layout #
		layout = QGridLayout()
		layout.setVerticalSpacing(10)

		# creating and adding widgets to layout #
		apply_button = QPushButton("Apply")
		self.if_active = QCheckBox("Set active")

		layout = QGridLayout()
		layout.setVerticalSpacing(15)
		self.laser_power_percent = _create_input_field(layout, "Setpoint λ-" + str(self.laser_index), "0.0", "%", 1, 0)
		self.laser_power_percent.setValidator(QDoubleValidator())
		self.laser_power_absolute = _create_input_field(layout, "Setpoint λ-" + str(self.laser_index), "0.0", "mW", 3, 0)
		self.laser_power_absolute.setValidator(QDoubleValidator())

		modulation_modes = ["Standby", "CW", "Analog", "Digital"]
		self.operating_mode = _create_combo_box(layout, modulation_modes, "Modulation mode", 5, 0)
		control_modes = ["ACC", "APC"]
		self.control_mode = _create_combo_box(layout, control_modes, "Control mode", 7, 0)

		layout.addWidget(QLabel("λ-"+str(self.laser_index)), 0, 0)
		layout.addItem(QSpacerItem(10, 80), 9, 0)
		layout.addWidget(self.if_active, 10, 0)
		layout.addWidget(apply_button, 11, 0)
		self.setLayout(layout)

		# signal handling #
		apply_button.clicked.connect(lambda: self._update_storage(True))
		self.laser_power_percent.returnPressed.connect(lambda: self._calculate_power(True))
		self.laser_power_absolute.returnPressed.connect(lambda: self._calculate_power(False))

	# Function for calculating power depending on input mode #
	def _calculate_power(self, if_percent: bool) -> None:
		if if_percent:
			self.laser_power_absolute.clear()

			power = float(self.laser_power_percent.text().replace(',','.'))*self.max_power/100
			self.laser_power_absolute.insert(str(power))
		else:
			self.laser_power_percent.clear()

			power = float(self.laser_power_absolute.text().replace(',','.'))/self.max_power*100
			self.laser_power_percent.insert(str(power))

	# Slot for writing values to storage module #
	@Slot(bool)
	def _update_storage(self, apply_button: bool) -> None:
		power_percent = float(self.laser_power_percent.text().replace(',','.'))
		operating_mode = self.operating_mode.currentIndex()
		control_mode = self.control_mode.currentIndex()
		if_active = self.if_active.isChecked()

		self.storage_update_signal.emit(power_percent, operating_mode, control_mode, if_active)
		if apply_button:
			self.apply_signal.emit()


	# Function for getting values from storage module #
	def _get_storage(self, parameter_name: str, value) -> None:
		if parameter_name == "temporary_power":
			self.laser_power_percent.clear()
			self.laser_power_percent.setText(str(value))
			self._calculate_power(True)
		elif parameter_name == "operating_mode":
			self.operating_mode.setCurrentIndex(value)
		elif parameter_name == "control_mode":
			self.control_mode.setCurrentIndex(value)
		elif parameter_name == "if_active":
			self.if_active.setChecked(value)


## class for creating info panel widget on main window ##
class InfoPanelWidget(QWidget):
	# creating signals #
	laser_info_signal = Signal()
	stage_port_signal = Signal(bool)
	freq_gen_port_signal = Signal(bool)
	laser1_port_signal = Signal(bool)
	laser2_port_signal = Signal(bool)

	def __init__(self) -> None:
		super().__init__()
		self.info_states = {	0: ["Moving", "Not Moving"],
					  			1: ["Emission off", "Emission on"],
					  			2: ["Closed", "Open", "Error"]}
		self.indicators = []

		# create layout #
		self.layout = QGridLayout()
		self.layout.setVerticalSpacing(5)
		# Laser info button #
		laser_push_button = QPushButton("Laser info")
		laser_push_button.clicked.connect(self.laser_info_signal.emit)

		self._create_status_indicator("Stage :", self.info_states[0], 0, 0)
		self._create_status_indicator("Laser 1:", self.info_states[1], 1, 0)
		self._create_status_indicator("Laser 2:", self.info_states[1], 2, 0)
		self.layout.addWidget(laser_push_button, 3, 0)

		#self.layout.addItem(QSpacerItem(10, 100), 4, 0)

		self._create_port_indicator("EcoVario port:", self.info_states[2], 4, 0, 3)
		self._create_port_indicator("TGA 1244 port:", self.info_states[2], 6, 0, 4)
		self._create_port_indicator("Laser 1 port:", self.info_states[2], 8, 0, 5)
		self._create_port_indicator("Laser 2 port:", self.info_states[2], 10, 0, 6)
		self.setLayout(self.layout)

		# TODO ist das die beste Lösung? #
		self.indicators[3]["buttons"][0].clicked.connect(lambda: self.stage_port_signal.emit(True))
		self.indicators[3]["buttons"][1].clicked.connect(lambda: self.stage_port_signal.emit(False))

		self.indicators[4]["buttons"][0].clicked.connect(lambda: self.freq_gen_port_signal.emit(True))
		self.indicators[4]["buttons"][1].clicked.connect(lambda: self.freq_gen_port_signal.emit(False))

		self.indicators[5]["buttons"][0].clicked.connect(lambda: self.laser1_port_signal.emit(True))
		self.indicators[5]["buttons"][1].clicked.connect(lambda: self.laser1_port_signal.emit(False))
		self.indicators[6]["buttons"][0].clicked.connect(lambda: self.laser2_port_signal.emit(True))
		self.indicators[6]["buttons"][1].clicked.connect(lambda: self.laser2_port_signal.emit(False))


	# Function for creating status indicators #
	def _create_status_indicator(self, label: str, status: list, row: int, column: int) -> None:
		label = QLabel(label)
		label.setAlignment(Qt.AlignRight)
		status_label = QLabel(status[0])
		indicator = QFrame()
		indicator.setFixedSize(14, 14)
		indicator.setStyleSheet("background-color: red")

		self.layout.addWidget(label, row, column)
		self.layout.addWidget(indicator, row, column+1, alignment=Qt.AlignRight)
		self.layout.addWidget(status_label, row, column+2)

		indicator_data = {	"frame": indicator,
							"status": status_label,
							"text": status}
		self.indicators.append(indicator_data)

	# Function for creating port indicators #
	def _create_port_indicator(self, label: str, status: list, row: int, column: int, index: int) -> None:
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
		self.layout.addWidget(indicator, row, column+1, alignment=Qt.AlignRight)
		self.layout.addWidget(status_label, row, column+2)
		self.layout.addWidget(open_button, row+1, column)
		self.layout.addWidget(close_button, row+1, column+1)

		indicator_data = {	"frame": indicator,
							"status": status_label,
							"text": status,
							"buttons": [open_button, close_button]}
		self.indicators.append(indicator_data)

	# Slot for updating indicators #
	@Slot(int, bool)
	def _update_indicator(self, index: int, if_on: bool) -> None:
		current_indicator = self.indicators[index]
		if if_on:
			current_indicator["frame"].setStyleSheet("background-color: green")
			current_indicator["status"].setText(current_indicator["text"][1])
			return
		else:
			current_indicator["frame"].setStyleSheet("background-color: red")
			current_indicator["status"].setText(current_indicator["text"][0])
			return

## class for creating laser info window ##
class LaserInfoWidgets(QWidget):
	def __init__(self, layout, firmware: tuple=[["","",""],["","",""]], specs: tuple=["",""], max_power: tuple=["",""], error_byte: tuple=["not connected!","not connected!"]) -> None:
		super().__init__()
		for i in [1, 2]:
			layout.addWidget(QLabel("Laser %d: "%i), 0, i-1 if i == 1 else i+1)
			layout.addWidget(QLabel("Model code: "), 1, i-1 if i == 1 else i+1)
			layout.addWidget(QLabel("Device id: "), 2, i-1 if i == 1 else i+1)
			layout.addWidget(QLabel("Firmware version: "), 3, i-1 if i == 1 else i+1)
			layout.addWidget(QLabel("Wavelenght: "), 4, i-1 if i == 1 else i+1)
			layout.addWidget(QLabel("Max power: "), 5, i-1 if i == 1 else i+1)
			layout.addWidget(QLabel("Status: "), 6, i-1 if i == 1 else i+1)

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

## class for creating control word window ##
class ControlWordsWidgets(QWidget):
	# creating signals #
	apply_signal = Signal(tuple)

	def __init__(self, layout) -> None:
		super().__init__()
		self.var0 = QCheckBox("Einschalten")
		self.var0.setChecked(True)
		self.var1 = QCheckBox("Motorspannung ein")
		self.var1.setChecked(True)
		self.var2 = QCheckBox("Schnellstop")
		self.var2.setChecked(True)
		self.var3 = QCheckBox("Betriebsfreigabe")
		self.var3.setChecked(True)
		self.var4 = QCheckBox("neue Zielposition")
		self.var4.setChecked(True)
		self.var5 = QCheckBox("direkte Sollwertvorgabe")
		self.var5.setChecked(True)
		self.var6 = QCheckBox("absoluter/relativer Modus")
		self.var7 = QCheckBox("Fehlerrücksetzen")
		self.var8 = QCheckBox("Halt")
		self.var9 = QCheckBox("reserviert 1")
		self.var10 = QCheckBox("reserviert 2")

		for i in range(0, 11, 1):
			layout.addWidget(eval("self.var%d"%i), i, 0)

		layout.addItem(QSpacerItem(10, 100), 11, 0)
		apply_button = QPushButton("Apply")
		layout.addWidget(apply_button, 12, 0)

		apply_button.clicked.connect(self._get_states)

	# Slot for getting and calculation control word #
	@Slot()
	def _get_states(self) -> None:
		states = [eval("self.var%d"%i).isChecked() for i in range(0, 11, 1)][::-1]
		self.apply_signal.emit(states)

## class for creating port selection widgets ##
class PortSelectionWidgets(QWidget):
	# creating signals #
	set_ports_signal = Signal(str, str, str, str)
	default_set_signal = Signal(str, str, str, str)

	def __init__(self, layout, stage_port: str, freq_gen_port: str, laser1_port: str, laser2_port: str) -> None:
		super().__init__()

		self.stage_port = _create_input_field(layout, "EcoVatio Port:", stage_port, "", 0, 0)
		self.stage_port.setAlignment(Qt.AlignLeft)
		self.freq_gen_port = _create_input_field(layout, "TGA 1244 Port:", freq_gen_port, "", 2, 0)
		self.freq_gen_port.setAlignment(Qt.AlignLeft)
		self.laser1_port = _create_input_field(layout, "Laser 1 Port:", laser1_port, "", 4, 0)
		self.laser1_port.setAlignment(Qt.AlignLeft)
		self.laser2_port = _create_input_field(layout, "Laser 2 Port:", laser2_port, "", 6, 0)
		self.laser2_port.setAlignment(Qt.AlignLeft)

		apply_button = QPushButton("Apply")
		def_button = QPushButton("Set as default")

		layout.addItem(QSpacerItem(100, 10), 7, 0)
		layout.addWidget(apply_button, 8, 0)
		layout.addWidget(def_button, 8, 1)
		apply_button.clicked.connect(self.apply_ports)
		def_button.clicked.connect(self.default_ports)

	# Slot for setting new ports and closing dialog #
	@Slot()
	def apply_ports(self) -> None:
		stage = self.stage_port.text()
		freq_gen = self.freq_gen_port.text()
		laser1 = self.laser1_port.text()
		laser2 = self.laser2_port.text()

		self.set_ports_signal.emit(stage, freq_gen, laser1, laser2)

	# Slot for setting new default ports #
	@Slot()
	def default_ports(self) -> None:
		stage = self.stage_port.text()
		freq_gen = self.freq_gen_port.text()
		laser1 = self.laser1_port.text()
		laser2 = self.laser2_port.text()

		self.default_set_signal.emit(stage, freq_gen, laser1, laser2)

