from PySide6.QtCore import QObject, Signal, Slot, Qt
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QGridLayout, QSplitter, QTabWidget, QMessageBox, QSizePolicy, QSpacerItem, QFileDialog
from LabSyncWidgets import InfoPanelWidget, LaserInfoWidgets, PortSelectionWidgets, StageWidgetNormal, LaserWidgetNormal, StageWidgetExpert, FrequencyGenWidgetExpert, LaserWidgetExpert
from Devices.EcoConnect import EcoConnect
from Devices.TGA import FrequencyGenerator
from Devices.omicron import OmicronLaser
import math, json, os

# Function for truncating numbers - used for stage position #
def trunctate(number: float, decimals: int) -> float:
	nbDecimals = len(str(number).split('.')[1])
	if nbDecimals <= decimals:
	 	return number
	stepper = 10.0 ** decimals
	return math.trunc(stepper * number) / stepper

## class for handling signal routing ##
class SignalHandler(QObject):
	def __init__(self) -> None:
		# inherit innit from QObject #
		super().__init__()

	# Function for connected a signal to a slot - or mutiple slots #
	def _connect(self, sender, signal_name: str, connections: list) -> None:
		signal = getattr(sender, signal_name)
		for receiver, slot_name in connections:
			slot = getattr(receiver, slot_name)
			signal.connect(slot)

## Main window class ##
class MainWindow(QMainWindow):
	def __init__(self, app) -> None:
		super().__init__()
		# get or make file saving directory #
		current_dir = os.path.dirname(os.path.abspath(__file__))
		self.file_dir = os.path.join(current_dir, "files")
		if not os.path.exists(self.file_dir):
			os.makedirs(self.file_dir)

		# get QApplication for closing window #
		self.app = app

		# set Window title #
		self.setWindowTitle("LabSync")

		# set container widget and main layout #
		container = QWidget()
		self.main_layout = QHBoxLayout(container)

		# define splitter widget #
		splitter = QSplitter(Qt.Horizontal)
		splitter.setHandleWidth(0)
		splitter.setChildrenCollapsible(False)

		# add info panel to left side #
		info_panel_layout = QGridLayout()
		info_panel_widget = QWidget()
		info_panel_widget.setLayout(info_panel_layout)
		self.info_panel = InfoPanelWidget()
		info_panel_layout.addWidget(self.info_panel, 0, 0)

		splitter.addWidget(info_panel_widget)

		# add Tabs to right side #
		self.tab_panel = self._setup_tabs()
		splitter.addWidget(self.tab_panel)

		self.tab_panel.setTabVisible(self.stage_tab_index, False)
		self.tab_panel.setTabVisible(self.freq_gen_tab_index, False)
		self.tab_panel.setTabVisible(self.luxx_tab_index, False)

		# set sizes #
		splitter.setStretchFactor(0, 1)
		splitter.setStretchFactor(1, 4)

		# set main layout to container widget and add container widget #
		self.main_layout.addWidget(splitter)
		container.setLayout(self.main_layout)
		self.setCentralWidget(container)

		# setup all other widgets #
		self.router = SignalHandler()
		self._setup_menubar()
		self._setup_widgets()
		self._load_default_ports()
		self._setup_devices()
		self._setup_signals()

	# Function to quit Application and close all ports #
	def closeEvent(self, event) -> None:
		# show messagebox for confirmation #
		response = QMessageBox.question(self,
						 "Close Labsync?",
						  "Do you want to close LabSync and all ports?",
						  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
						  QMessageBox.StandardButton.No)
		if response == QMessageBox.Yes:
			# close ports #
			self.Stage._set_port(False)
			self.FrequencyGenerator._set_port(False)
			self.Laser1._set_port(False)
			self.Laser2._set_port(False)
			# close window #
			event.accept()
		else:
			# if no, ignore #
			event.ignore()

	# Function for saving current parameters to json-file #
	def save_preset(self) -> None:
		# get filename and path #
		file_path = QFileDialog.getSaveFileName(self, "Save Parameters", self.file_dir, "Json Files (*.json)")[0]
		if file_path:
			# add json extension if now extension has been set #
			if not file_path.lower().endswith(".json"):
				file_path += ".json"
			# get all parameters and save to list #
			parameters = []
			stage_parameters = self.Stage.EcoVario.storage._get_all_parameters("EcoVario")
			parameters.append(stage_parameters)
			laser1_parameters = self.Laser1.Laser.storage._get_all_parameters("Laser")
			laser2_parameters = self.Laser2.Laser.storage._get_all_parameters("Laser")
			parameters.append(laser1_parameters)
			parameters.append(laser2_parameters)

			for i in [1, 2, 3, 4]:
				freq_gen_parameters = self.FrequencyGenerator.TGA1244.storage._get_all_parameters("C"+str(i))
				parameters.append(freq_gen_parameters)

			# dump all parameters into json file #
			with open(file_path, 'w') as file:
				try:
					json.dump(parameters, file, ensure_ascii=True, indent=4)
				except Exception as e:
					return QMessageBox.critical(self, "Error", f"Error while saving parameters!\n{e}")

	# Function for loading saved parameters from json-file #
	def load_preset(self) -> None:
		# get file path #
		file_path = QFileDialog.getOpenFileName(self, "Load Parameters", self.file_dir, "Json Files (*.json)")[0]
		try:
			with open(file_path, 'r') as file:
				parameters = json.load(file)
			# check if file has the correct length #
			if len(parameters) ==  7:
				# read each dict from file and store into storage module #
				stage_parameters = parameters[0]
				for key, value in stage_parameters.items():
					self.Stage.EcoVario.storage._set_parameter("EcoVario", key, value) if key != "if_active" else None
				laser1_parameters = parameters[1]
				for key, value in laser1_parameters.items():
					self.Laser1.Laser.storage._set_parameter("Laser", key, value) if key != "if_active" else None
				laser2_parameters = parameters[2]
				for key, value in laser2_parameters.items():
					self.Laser2.Laser.storage._set_parameter("Laser", key, value) if key != "if_active" else None
				for i in [1, 2, 3, 4]:
					freq_gen_parameters = parameters[i+2]
					for key, value in freq_gen_parameters.items():
						self.FrequencyGenerator.TGA1244.storage._set_parameter("C"+str(i), key, value) if key != "if_active" else None
			else:
				return QMessageBox.warning(self, "Warning", "File format not correct!\n Check Settings!")
		except FileNotFoundError:
			return QMessageBox.critical(self, "Error", f"File {file_path} not found!")
		except json.JSONDecodeError:
			return QMessageBox.critical(self, "Error", f"Error while trying to decode JSON-File {file_path}!")
		except Exception as e:
			print(f"Unexpected Error: {e}")

	# Function for loading default ports #
	def _load_default_ports(self) -> None:
		# select file - should not be deleted #
		ports_dir = self.file_dir + "/default_ports.json"
		try:
			with open(ports_dir, 'r') as file:
				ports = json.load(file)
				# load saved ports #
				self.def_stage_port = ports["EcoVario"]
				self.def_laser1_port = ports["Laser1"]
				self.def_laser2_port = ports["Laser2"]
				self.def_freq_gen_port = ports["TGA1244"]
		except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
			# fallback to default ports if file does not exist or could not be read #
			self.def_stage_port = "/dev/ttyUSB0"
			self.def_laser1_port = "/dev/ttyUSB2"
			self.def_laser2_port = "/dev/ttyUSB3"
			self.def_freq_gen_port = "/dev/ttyUSB1"
			return QMessageBox.critical(None, "Error", f"Default ports file not found!:\n {e}\n create new file!")

	# Function for saving default ports #
	def _set_default_ports(self, stage: str, freq: str, laser1: str, laser2: str) -> None:
		ports_dir = self.file_dir + "/default_ports.json"
		try:
			with open(ports_dir, 'w') as file:
				ports = {"EcoVario": stage,
						 "TGA1244": freq,
						 "Laser1": laser1,
						 "Laser2": laser2}
				json.dump(ports, file, ensure_ascii=True, indent=4)
		except Exception as e:
			return print(e)


	# Function to setup devices #
	def _setup_devices(self) -> None:
		# creating devices #
		self.Stage = StageFunctions(self.def_stage_port, self.stage_normal, self.stage_expert)
		self.FrequencyGenerator = FrequencyGeneratorFunctions(self.def_freq_gen_port)
		self.Laser1 = LaserFunctions(1, self.def_laser1_port)
		self.Laser2 = LaserFunctions(2, self.def_laser2_port)

	# Function to setup tabs for devices #
	def _setup_tabs(self) -> QTabWidget:
		tab_widget = QTabWidget()

		# normal mode tab #
		normal_tab = QWidget()
		self.normal_tab_layout = QHBoxLayout()
		normal_tab.setLayout(self.normal_tab_layout)
		tab_widget.addTab(normal_tab, "LabSync Controller")

		# EcoVario expert mode tab #
		stage_tab = QWidget()
		self.stage_tab_layout = QHBoxLayout()
		stage_tab.setLayout(self.stage_tab_layout)
		self.stage_tab_index = tab_widget.addTab(stage_tab, "EcoVario Controller")

		# Frequency Generator expert mode tab #
		freq_gen_tab = QWidget()
		self.freq_gen_tab_layout = QHBoxLayout()
		freq_gen_tab.setLayout(self.freq_gen_tab_layout)
		self.freq_gen_tab_index = tab_widget.addTab(freq_gen_tab, "TGA 1244 Controller")

		# Omicron LuxX+ expert mode tab #
		luxx_tab = QWidget()
		self.luxx_tab_layout = QHBoxLayout()
		luxx_tab.setLayout(self.luxx_tab_layout)
		self.luxx_tab_index = tab_widget.addTab(luxx_tab, "LuxX+ Controller")

		return tab_widget

	# Function to setup menubar #
	def _setup_menubar(self) -> None:
		menu_bar = self.menuBar()

		# create preset entry #
		preset_menu = menu_bar.addMenu("&Presets")
		save_preset = preset_menu.addAction("Save Preset")
		save_preset.triggered.connect(self.save_preset)

		load_preset = preset_menu.addAction("Load Preset")
		load_preset.triggered.connect(self.load_preset)

		# create expert mode toggle and port #
		mode_menu = menu_bar.addMenu("&Menu")
		expert_mode = mode_menu.addAction("Expert Mode")
		expert_mode.triggered.connect(self.expert_mode)

		port_select = mode_menu.addAction("Select Ports")
		port_select.triggered.connect(self._show_port_dialog)

	# Function for creating device-widgets on window #
	def _setup_widgets(self) -> None:
		# normal mode stage widget #
		self.stage_normal = StageWidgetNormal()
		self.stage_normal.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

		self.normal_tab_layout.addWidget(self.stage_normal)
		self.normal_tab_layout.addItem(QSpacerItem(100, 10))

		# normal mode laser widget #
		self.laser_normal = LaserWidgetNormal()
		self.laser_normal.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

		self.normal_tab_layout.addWidget(self.laser_normal)

		# stage expert mode widget #
		self.stage_expert = StageWidgetExpert()
		self.stage_expert.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

		self.stage_tab_layout.addWidget(self.stage_expert)

		# Frequency Generator expert widget #
		self.freq_gen_expert1 = FrequencyGenWidgetExpert(1)
		self.freq_gen_expert1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_expert2 = FrequencyGenWidgetExpert(2)
		self.freq_gen_expert2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_expert3 = FrequencyGenWidgetExpert(3)
		self.freq_gen_expert3.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_expert4 = FrequencyGenWidgetExpert(4)
		self.freq_gen_expert4.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert1)

		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert2)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert3)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert4)

		# laser expert widget #
		self.laser_expert1 = LaserWidgetExpert(1, 100)
		self.laser_expert1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

		self.laser_expert2 = LaserWidgetExpert(2, 200)
		self.laser_expert2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

		self.luxx_tab_layout.addWidget(self.laser_expert1)
		self.luxx_tab_layout.addWidget(self.laser_expert2)

	# Function for routing signals #
	def _setup_signals(self) -> None:
		## connect listeners ##
		# Stage #
		self.Stage.EcoVario.storage._add_listener("EcoVario", self.stage_expert, "_get_storage")
		self.Stage.EcoVario.storage._add_listener("EcoVario", self.stage_normal, "_get_storage")

		# Omicron Lasers #
		self.Laser1.Laser.storage._add_listener("Laser", self.laser_expert1, "_get_storage")
		self.Laser2.Laser.storage._add_listener("Laser", self.laser_expert2, "_get_storage")

		# Frequency Generator channels #
		for i in [1, 2, 3, 4]:
			self.FrequencyGenerator.TGA1244.storage._add_listener("C"+str(i), eval("self.freq_gen_expert%i"%i), "_get_storage")

		# general signals #
		self.router._connect(self.Stage, "port_signal", [(self.info_panel, "_update_indicator")])
		self.router._connect(self.FrequencyGenerator, "port_signal", [(self.info_panel, "_update_indicator")])
		self.router._connect(self.Laser1, "port_signal", [(self.info_panel, "_update_indicator")])
		self.router._connect(self.Laser2, "port_signal", [(self.info_panel, "_update_indicator")])

		# port signals #
		self.router._connect(self.info_panel, "stage_port_signal", [(self.Stage, "_set_port")])
		self.router._connect(self.info_panel, "freq_gen_port_signal", [(self.FrequencyGenerator, "_set_port")])
		self.router._connect(self.info_panel, "laser1_port_signal", [(self.Laser1, "_set_port")])
		self.router._connect(self.info_panel, "laser2_port_signal", [(self.Laser2, "_set_port")])

		# info panel signal #
		self.router._connect(self.info_panel, "laser_info_signal", [(self, "_show_laser_info")])
		self.router._connect(self.Stage, "position_signal", [(self.info_panel, "_update_indicator")])

		# Stage normal tab and expert tab signals #
		self.router._connect(self.stage_normal, "storage_update_signal", [(self.Stage, "manage_storage")])
		self.router._connect(self.stage_expert, "storage_update_signal", [(self.Stage, "manage_storage")])

		self.router._connect(self.stage_normal, "start_signal", [(self.Stage, "_set_values_start")])
		self.router._connect(self.stage_normal, "stop_signal", [(self.Stage, "stop")])

		self.router._connect(self.stage_expert, "start_signal", [(self.Stage, "_set_values_start")])
		self.router._connect(self.stage_expert, "stop_signal", [(self.Stage, "stop")])

		# Frequency Generator expert tab signals #
		self.router._connect(self.freq_gen_expert1, "storage_update_signal", [(self.FrequencyGenerator, "manage_storage")])
		self.router._connect(self.freq_gen_expert2, "storage_update_signal", [(self.FrequencyGenerator, "manage_storage")])
		self.router._connect(self.freq_gen_expert3, "storage_update_signal", [(self.FrequencyGenerator, "manage_storage")])
		self.router._connect(self.freq_gen_expert4, "storage_update_signal", [(self.FrequencyGenerator, "manage_storage")])

		self.router._connect(self.laser_normal, "storage_update_signal_freq", [(self.FrequencyGenerator, "_set_values_normal")])

		# Laser expert tab signals #
		self.router._connect(self.laser_expert1, "storage_update_signal", [(self.Laser1, "manage_storage")])
		self.router._connect(self.laser_expert2, "storage_update_signal", [(self.Laser2, "manage_storage")])
		self.router._connect(self.laser_expert1, "apply_signal", [(self.Laser1, "_set_values")])
		self.router._connect(self.laser_expert2, "apply_signal", [(self.Laser2, "_set_values")])

		self.router._connect(self.laser_normal, "storage_update_signal_laser1", [(self.Laser1, "manage_storage"),
																				 (self.Laser1, "_set_values")])
		self.router._connect(self.laser_normal, "storage_update_signal_laser2", [(self.Laser2, "manage_storage"),
																				 (self.Laser2, "_set_values")])

		# init try to open ports after signals are connected # TODO wo anders hin
		self.Stage.__post_init__()
		self.FrequencyGenerator.__post_init__()
		self.Laser1.__post_init__()
		self.Laser2.__post_init__()

	# Function for toggling expert mode #
	def expert_mode(self) -> None:
		visible = self.tab_panel.isTabVisible(self.stage_tab_index)
		# hiding or showing tabs #
		self.tab_panel.setTabVisible(self.stage_tab_index, not visible)
		self.tab_panel.setTabVisible(self.freq_gen_tab_index, not visible)
		self.tab_panel.setTabVisible(self.luxx_tab_index, not visible)

	# Function for showing Laser information #
	def _show_laser_info(self) -> None:
		self.laser_dialog = None
		# get Laser parameters #
		firmware = [self.Laser1.Laser.storage._get_parameter("Laser", "firmware"),
			  		self.Laser2.Laser.storage._get_parameter("Laser", "firmware")]
		specs = [self.Laser1.Laser.storage._get_parameter("Laser", "specs"),
				 self.Laser2.Laser.storage._get_parameter("Laser", "specs")]
		max_power = [self.Laser1.Laser.storage._get_parameter("Laser", "max_power"),
					 self.Laser2.Laser.storage._get_parameter("Laser", "max_power")]

		# check if window already exists and if so, raise to top #
		if self.laser_dialog is None or not self.laser_dialog.isVisible():
			self.laser_dialog = LaserInfoDialog(firmware, specs, max_power)
			self.laser_dialog.show()
		else:
			self.laser_dialog.raise_()

	# Function for showing port selection #
	def _show_port_dialog(self) -> None:
		self.port_dialog = None

		# check if window already exists and if so, raise to top #
		if self.port_dialog is None or not self.port_dialog.isVisible():
			self.port_dialog = PortSelectionDialog(self.Stage.port, self.FrequencyGenerator.port, self.Laser1.port, self.Laser2.port)
			self.port_dialog.widgets.set_ports_signal.connect(self._set_ports)
			self.port_dialog.widgets.default_set_signal.connect(self._set_default_ports)
			self.port_dialog.show()
		else:
			self.port_dialog.raise_()

	# Function for setting new ports #
	def _set_ports(self, stage: str, freq_gen: str, laser1: str, laser2: str) -> None:
		self.Stage.port = stage
		self.FrequencyGenerator.port = freq_gen
		self.Laser1.port = laser1
		self.Laser2.port = laser2

		print(laser1)

		self.port_dialog.close()

	# Function for continous calling of sub-functions #
	def loop_functions(self) -> None:
		self.Stage._get_current_position()

		stage_error_code = self.Stage._get_current_error_code()
		self.stage_normal.error_code.clear()
		self.stage_normal.error_code.setText(stage_error_code)
		self.stage_expert.error_code.clear()
		self.stage_expert.error_code.setText(stage_error_code)


## class for handling stage functions ##
class StageFunctions(QObject):
	# creating signals #
	port_signal = Signal(int, bool)
	position_signal = Signal(int, bool)

	def __init__(self, port: str, stage_normal, stage_expert) -> None:
		super().__init__()
		self.port = port
		self.EcoVario = EcoConnect(simulate=True)

		# TODO wollte ich eigentlich verhindern, aber mit signalen oder ähnliches zu umständlich?
		self.stage_normal = stage_normal
		self.stage_expert = stage_expert

	# Function to run initially, but after signals have been routed #
	def __post_init__(self) -> None:
		try:
			self.EcoVario.open_port(self.port, 9600)
			self.port_status = True
			self.port_signal.emit(3, True)
		except ConnectionError:
			self.port_status = False
			self.port_signal.emit(3, False)

	# Slot to manage EcoVario storage -> Get new parameters and pass them to storage moduale #
	@Slot(float, float, float, float)
	def manage_storage(self, target_position: float, speed: float, accel: float, deaccel: float) -> None:
		self.EcoVario.storage._set_parameter("EcoVario", "target_position", target_position)
		self.EcoVario.storage._set_parameter("EcoVario", "speed", speed)
		self.EcoVario.storage._set_parameter("EcoVario", "accel", accel)
		self.EcoVario.storage._set_parameter("EcoVario", "deaccel", deaccel)

	# Slot to get storage values and write to stage #
	@Slot()
	def _set_values_start(self) -> None:
		try:
			target_position = self.EcoVario.storage._get_parameter("EcoVario", 	"target_position")
			speed = self.EcoVario.storage._get_parameter("EcoVario", "speed")
			accel = self.EcoVario.storage._get_parameter("EcoVario", "accel")
			deaccel = self.EcoVario.storage._get_parameter("EcoVario", "deaccel")

			self.EcoVario._write_position(target_position)
			self.EcoVario._write_speed(speed)
			self.EcoVario._write_accel_deaccel(accel, deaccel)
			self.EcoVario.start()
		except ValueError as e:
			return QMessageBox.warning(None, "Error", f"{e}")

	# Slot to stop stage #
	@Slot()
	def stop(self) -> None:
		self.EcoVario.stop()

	def _get_current_position(self) -> None:
		current_position = self.EcoVario._get_current_position()
		if current_position == -1:
			return
		current_position = trunctate(current_position, 4)
		target_position = self.EcoVario.storage._get_parameter("EcoVario", "target_position")

		if str(current_position) != self.stage_normal.current_position.text():
			self.stage_normal.current_position.clear()
			self.stage_normal.current_position.setText(str(current_position))
			self.stage_expert.current_position.clear()
			self.stage_expert.current_position.setText(str(current_position))

		if target_position-0.002 <= current_position <= target_position+0.002:
			self.position_signal.emit(0, True)
		else:
			self.position_signal.emit(0, False)

	# Function to get current error code #
	def _get_current_error_code(self) -> str:
		current_error = self.EcoVario._get_last_error()
		if current_error == -1:
			 return "not connected!"
		else:
			return str(current_error)

	# Slot to open / close port on button press #
	@Slot(bool)
	def _set_port(self, state: bool) -> None:
		if state:
			try:
				self.EcoVario.open_port(self.port, 9600)
				self.port_signal.emit(3, True)
			except ConnectionError as e:
				self.port_signal.emit(3, False)
				return QMessageBox.information(None, "Error", "Could not open port:\n%s"%e)
		else:
			self.EcoVario.close_port()
			self.port_signal.emit(3, False)


## class for handling Frequency generator functions ##
class FrequencyGeneratorFunctions(QObject):
	# creating signals #
	port_signal = Signal(int, bool)

	def __init__(self, port: str) -> None:
		super().__init__()
		self.port = port
		self.TGA1244 = FrequencyGenerator(simulate=True)

	# Function to run initally, but after signals have been routed #
	def __post_init__(self) -> None:
		try:
			self.TGA1244.open_port(self.port, 9600)
			self.port_signal.emit(4, True)
		except ConnectionError:
			self.port_signal.emit(4, False)

	# Slot to manage storage -> get new parameters and pass them to storage module #
	@Slot(int, int, int, float, float, float, float, int, bool)
	def manage_storage(self, channel_index: int, waveform: int, inputmode: int, amplitude: float, offset: float, frequency: float, phase: float, lockmode: int, if_active: bool) -> None:
		channel = "C"+str(channel_index)
		self.TGA1244.storage._set_parameter(channel, "wave", waveform)
		self.TGA1244.storage._set_parameter(channel, "frequency", frequency)
		self.TGA1244.storage._set_parameter(channel, "amplitude", amplitude)
		self.TGA1244.storage._set_parameter(channel, "offset", offset)
		self.TGA1244.storage._set_parameter(channel, "phase", phase)
		self.TGA1244.storage._set_parameter(channel, "inputmode", inputmode)
		self.TGA1244.storage._set_parameter(channel, "lockmode", lockmode)
		self.TGA1244.storage._set_parameter(channel, "if_active", if_active)

		self.TGA1244.apply(channel=channel_index,
							wave=self.TGA1244.storage._get_parameter(channel, "wave"),
							amplitude=self.TGA1244.storage._get_parameter(channel, "amplitude"),
							offset=self.TGA1244.storage._get_parameter(channel, "offset"),
							frequency=self.TGA1244.storage._get_parameter(channel, "frequency"),
							inputmode=self.TGA1244.storage._get_parameter(channel, "inputmode"),
						 	phase=self.TGA1244.storage._get_parameter(channel, "phase"),
						 	lockmode=self.TGA1244.storage._get_parameter(channel, "lockmode"),
						 	if_active=self.TGA1244.storage._get_parameter(channel, "if_active")
						 	)

	# Slot to handle Frequency Generator Values on normal Tab #
	@Slot(str, str, int, int, float, float, float, float, int, int, bool, bool)
	def _set_values_normal(self, index_1: str, index_2: str, modualtion_1: int, modualtion_2: int, power_1: float, power_2: float, frequency_1: float, frequency_2: float, lockmode_1: int, lockmode_2: int, if_active_1: bool, if_active_2: bool) -> None:
		# get parameters for Frequency Generator on Digital or Analog modulation from look up table #
		parameters_1 = self._calculate_parameters(power_1)[:2]
		parameters_2 = self._calculate_parameters(power_2)[2:]

		# check selected modulation #
		if index_1 == index_2:
			return QMessageBox.information(None, "Error", "Frequency generator channels cannot be identical!")

		if modualtion_1 == 2:
			self.manage_storage(str(index_1), 0, 0, parameters_1[0], parameters_1[1], frequency_1, 0.0, lockmode_1, if_active_1)
		elif modualtion_1 == 3:
			self.manage_storage(str(index_1), 1, 0, 5.0, 0.0, frequency_1, 0.0, lockmode_1, if_active_1)
		else:
			self.TGA1244.toggle_channel_output(index_1, False)

		if modualtion_2 == 2:
			self.manage_storage(str(index_2), 0, 0, parameters_2[0], parameters_2[1], frequency_2, 0.0, lockmode_2, if_active_2)
		elif modualtion_2 == 3:
			self.manage_storage(str(index_2), 1, 0, 5.0, 0.0, frequency_2, 0.0, lockmode_2, if_active_2)
		else:
			self.TGA1244.toggle_channel_output(index_2, False)

	# Slot to open / close port on button press #
	@Slot(bool)
	def _set_port(self, state: bool) -> None:
		if state:
			try:
				self.TGA1244.open_port(self.port, 9600)
				self.port_signal.emit(4, True)
			except ConnectionError as e:
				self.port_signal.emit(4, False)
				return QMessageBox.information(None, "Error", "Could not open port:\n%s"%e)
		else:
			self.TGA1244.close_port()
			self.port_signal.emit(4, False)

	# Function for getting Frequency Generator parameters depending on Laser power from look up table #
	def _calculate_parameters(self, power: float) -> list[float, float, float, float]:
		table = {	 5: [2.30, 4.45, 1.75, 2.65],
					10: [2.80, 4.00, 2.50 ,2.30],
					15: [3.30, 3.80, 2.85, 2.25],
					20: [3.65, 3.70, 2.95, 2.10],
					25: [3.85, 3.60, 3.00, 2.05],
					30: [3.95, 3.55, 3.05, 2.06],
					35: [4.10, 3.50, 3.05, 1.90],
					40: [4.20, 3.40, 3.05, 1.90],
					45: [4.40, 3.35, 3.10, 1.90],
					50: [4.45, 3.30, 3.30, 2.00],
					55: [4.50, 3.30, 3.30, 1.95],
					60: [4.60, 3.25, 3.40, 1.96],
					65: [4.65, 3.20, 3.40, 1.90],
					70: [4.75, 3.20, 3.45, 1.90],
					75: [4.80, 3.15, 3.50, 1.90],
					80: [4.85, 3.15, 3.55, 1.90],
					85: [4.87, 3.15, 3.53, 1.90],
					90: [4.87, 3.15, 3.50, 1.90],
					95: [4.93, 3.12, 3.40, 1.82],
					100: [4.97, 3.09, 3.56, 1.90]}

		parameters = table[power]
		return parameters

## class for handling laser functions ##
class LaserFunctions(QObject):
	# creating signals #
	port_signal = Signal(int, bool)
	emission_signal = Signal(bool)

	def __init__(self, laser_index: int, port: str) -> None:
		super().__init__()
		self.laser_index = laser_index
		self.port = port
		self.emission = False

		self.Laser = OmicronLaser(simulate=True)

	# Function to run initally, but after signals have been routed #
	def __post_init__(self) -> None:
		try:
			self.Laser.open_port(self.port, 500000)
			self.port_signal.emit(self.laser_index+4, True)
		except ConnectionError:
			self.port_signal.emit(self.laser_index+4, False)

	# Slot to manage storage -> get new parameters and pass them to storage module #
	@Slot(float, int, int, int, bool)
	def manage_storage(self, power_percent: float, operating_mode: int, control_mode: int, if_active: bool) -> None:
		self.Laser.storage._set_parameter("Laser", "operating_mode", operating_mode)
		self.Laser.storage._set_parameter("Laser", "temporary_power", power_percent)
		self.Laser.storage._set_parameter("Laser", "if_active", if_active)
		self.Laser.storage._set_parameter("Laser", "control_mode", control_mode)

	# Slot to get parameters from storage and write to laser #
	@Slot()
	def _set_values(self) -> None:
		operating_mode = self.Laser.storage._get_parameter("Laser", "operating_mode")
		temporary_power = self.Laser.storage._get_parameter("Laser", "temporary_power")
		if_active = self.Laser.storage._get_parameter("Laser", "if_active")
		control_mode = self.Laser.storage._get_parameter("Laser", "control_mode")

		if operating_mode == 3 and control_mode == 1 or operating_mode == 4 and control_mode == 1:
			return QMessageBox.warning(None, "Error", "Analog and Digital modulation only support Active Current Control!")

		if operating_mode == 0:
			actual_mode = 0
		elif operating_mode == 1:
			if control_mode == 0:
				actual_mode = 1
			else:
				actual_mode = 2
		else:
			actual_mode = operating_mode + 1

		response = self.Laser.set_operating_mode(str(actual_mode))
		if not response:
			return QMessageBox.critical(None, "Error", "Operating mode was not set! \n Check Error!")
		elif response == -1:
			return QMessageBox.information(None, "Error", "Laser not connected!")

		response = self.Laser.set_temporary_power(temporary_power)
		if not response:
			return QMessageBox.critical(None, "Error", "Power was not set! \n Check Error!")
		elif response == -1:
			return QMessageBox.information(None, "Error", "Laser not connected!")

		# set meission status #
		self._set_emission(if_active)

	# Slot to set Laser emission and update indicators #
	@Slot(bool)
	def _set_emission(self, set_: bool) -> None:
		if set_ and not self.emission:
			response = self.Laser.laser_on()
			if response:
				self.emission = True
				self.emission_signal.emit(True)
			else:
				self.emission = False
				QMessageBox.warning(None, "Error", "Emission could not be started!")
		elif self.emission and not set_:
			response = self.Laser.laser_off()
			if response:
				self.emission = False
				self.emission_signal.emit(False)
			else:
				self.emission = False
				QMessageBox.warning(None, "Error", "Emission could not be stopped!")

	# Slot to open / close port on button press #
	@Slot(bool)
	def _set_port(self, state: bool) -> None:
		if state:
			try:
				self.Laser.open_port(self.port, 500000)
				self.port_signal.emit(self.laser_index+4, True)
			except ConnectionError as e:
				self.port_signal.emit(self.laser_index+4, False)
				return QMessageBox.information(None, "Error", "could not open port:\n%s"%e)
		else:
			self.Laser.close_port()
			self.port_signal.emit(self.laser_index+4, False)


## class for creating Laser information Dialog ##
class LaserInfoDialog(QWidget):
	def __init__(self, firmware: list, specs: list, max_power: list, parent=None) -> None:
		super().__init__(parent, Qt.Window)
		layout = QGridLayout()
		LaserInfoWidgets(layout, firmware, specs, max_power)
		layout.setVerticalSpacing(10)

		self.setWindowTitle("Laser Information")
		self.setMinimumSize(600, 400)
		self.setLayout(layout)

## class for creating Port selection Dialog ##
class PortSelectionDialog(QWidget):
	def __init__(self, stage_port: str, freq_gen_port: str, laser1_port: str, laser2_port: str, parent=None) -> None:
		super().__init__(parent, Qt.Window)
		layout = QGridLayout()
		self.widgets = PortSelectionWidgets(layout, stage_port, freq_gen_port, laser1_port, laser2_port)
		layout.setVerticalSpacing(10)

		self.setWindowTitle("Select Ports")
		self.setMinimumSize(300, 400)
		self.setLayout(layout)


