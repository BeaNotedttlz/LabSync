from PySide6.QtWidgets import QSpacerItem

from Classes.App.EcoFunc import EcoFunctions
from Classes.App.TgaFunc import FrequencyGeneratorFunctions
from Classes.App.LaserFunc import LaserFunctions
from Classes.App.FsvFunc import FsvFunctions
from Classes.App.Bode import BodePlot

from Classes.Widgets.Dialogs import LaserInfoWidget, PortSelectionWidget
from Classes.Widgets.FsvBodeplot import BodePlotWindow
from Classes.Widgets.InfoPanel import InfoPanelWidget
from Classes.Widgets.EcoNormal import StageWidgetNormal
from Classes.Widgets.EcoExpert import StageWidgetExpert
from Classes.Widgets.LaserNormal import LaserWidgetNormal
from Classes.Widgets.TgaExpert import FrequencyGeneratorWidgetExpet
from Classes.Widgets.LaserExpert import LaserWidgetExpert
from Classes.Widgets.FsvNormal import FsvNormalWidget

from Devices.Storage import ParameterStorage
from signals import SignalHandler

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout,
							   QSplitter, QMessageBox, QGridLayout,
							   QFileDialog, QTabWidget, QSizePolicy)
import os, json

class MainWindow(QMainWindow):
	def __init__(self, app, _simulate: bool) -> None:
		super().__init__()
		self.app = app
		self.simulate = _simulate
		self.storage = ParameterStorage()

		self.signal_handler = SignalHandler()
		curr_file_dir = os.path.dirname(os.path.realpath(__file__))
		self.file_dir = os.path.join(curr_file_dir, "files")

		self.port_dialog = None
		self.laser_dialog = None
		self.bode_window = None
		self.bode_plotter = None

		self.setWindowTitle("LabSync")

		container = QWidget()
		self.main_layout = QHBoxLayout(container)

		splitter = QSplitter(Qt.Horizontal)
		splitter.setHandleWidth(0)
		splitter.setChildrenCollapsible(False)

		info_panel_layout = QGridLayout()
		info_panel_widget = QWidget()
		info_panel_widget.setLayout(info_panel_layout)
		self.info_panel = InfoPanelWidget()
		info_panel_layout.addWidget(self.info_panel, 0, 0)

		splitter.addWidget(info_panel_widget)
		self.tab_panel = self._setup_tabs()
		splitter.addWidget(self.tab_panel)

		self.tab_panel.setTabVisible(self.stage_tab_index, False)
		self.tab_panel.setTabVisible(self.freq_gen_tab_index, False)
		self.tab_panel.setTabVisible(self.laser_tab_index, False)

		splitter.setStretchFactor(0, 1)
		splitter.setStretchFactor(1, 4)

		self.main_layout.addWidget(splitter)
		container.setLayout(self.main_layout)
		self.setCentralWidget(container)

		self._load_default_ports()
		self._setup_devices()
		self._setup_menubar()
		self._setup_widgets()
		self._setup_connections()
		self._setup_listeners()

	def closeEvent(self, event) -> None:
		response = QMessageBox.question(
			self,
			"Close LabSync?",
			"Do you want to close LabSync and close all ports?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No
		)
		if response == QMessageBox.StandardButton.Yes:
			self.Stage.EcoVario.close_port()
			self.FrequencyGenerator.TGA1244.close_port()
			self.Laser1.LuxX.close_port()
			self.Laser2.LuxX.close_port()
			event.accept()
		else:
			event.ignore()

	def _save_preset(self) -> None:
		file_path = QFileDialog.getSaveFileName(
			self,
			"Save Parameters",
			self.file_dir,
			"Json Files (*.json)"
		)[0]
		if file_path:
			if not file_path.endswith(".json"):
				file_path = file_path + ".json"
			with open(file_path, 'w') as file:
				try:
					parameters = self.storage.get_all()
					parameters_list = [[key, value] for key, value in parameters.items()]
					json.dump(parameters_list, file, ensure_ascii=True, indent=4)
					return None
				except Exception as e:
					QMessageBox.critical(
						self,
						"Error",
						f"Error while saving parameters:\n {e}",
					)
		return None

	def _load_preset(self) -> None:
		file_path = QFileDialog.getOpenFileName(
			self,
			"Load Parameters",
			self.file_dir,
			"Json Files (*.json)"
		)[0]
		if file_path:
			with open(file_path, 'r') as file:
				try:
					parameters = json.load(file)
					parameters_restored = {tuple(key): value for key, value in parameters}
					self.storage.load_all(parameters_restored)
					return None
				except KeyError as e:
					QMessageBox.critical(
						self,
						"Error",
						"Stored Parameters damaged, could not load file!"
					)
					return None
				except Exception as e:
					QMessageBox.critical(
						self,
						"Error",
						f"Something went wrong while loading parameters:\n {e}",
					)
					return None


	def _load_default_ports(self) -> None:
		ports_dir = os.path.join(self.file_dir, "ports/default_ports.json")
		try:
			with open(ports_dir, "r") as file:
				ports = json.load(file)
				self.def_stage_port = ports["EcoVario"]
				self.def_laser1_port = ports["Laser1"]
				self.def_laser2_port = ports["Laser2"]
				self.def_freq_gen_port = ports["TGA1244"]
				self.def_fsv_port = ports["FSV3000"]
				return None
		except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
			self.def_stage_port = "COM0"
			self.def_laser1_port = "COM1"
			self.def_laser2_port = "COM2"
			self.def_freq_gen_port = "COM3"
			self.def_fsv_port = "TCPIP::141.99.144.147::INSTR"
			QMessageBox.critical(
				self,
				"Error",
				f"Default ports file not found or broken\n{e}\n"
			)
			return None

	def _set_default_ports(self, stage: str, TGA1244: str, laser1: str, laser2: str, fsv: str) -> None:
		ports_dir = os.path.join(self.file_dir, "ports/default_ports.json")
		try:
			with open(ports_dir, "w") as file:
				ports = {
					"EcoVario": stage,
					"Laser1": laser1,
					"Laser2": laser2,
					"TGA1244": TGA1244,
					"FSV3000": fsv
				}
				json.dump(ports, file, ensure_ascii=True, indent=4)
				return None
		except Exception as e:
			return print(f"{e}")

	def _set_ports(self, stage, freq_gen, laser1, laser) -> None:
		self.Stage.port = stage
		self.FrequencyGenerator.port = freq_gen
		self.Laser1.port = laser1
		self.Laser2.port = laser1

		self.port_dialog.close()
		return None

	def _setup_devices(self) -> None:
		if self.def_stage_port is None:
			self._load_default_ports()

		self.Stage = EcoFunctions(
			port=self.def_stage_port,
			_storage=self.storage,
			_simulate=self.simulate
		)
		self.Laser1 = LaserFunctions(
			port=self.def_laser1_port,
			_storage=self.storage,
			index=1,
			_simulate=self.simulate
		)
		self.Laser2 = LaserFunctions(
			port=self.def_laser2_port,
			_storage=self.storage,
			index=2,
			_simulate=self.simulate
		)
		self.FrequencyGenerator = FrequencyGeneratorFunctions(
			port=self.def_freq_gen_port,
			_storage=self.storage,
			_simulate=self.simulate
		)
		self.SpectrumAnylyzer = FsvFunctions(
			ip=self.def_fsv_port,
			_storage=self.storage,
			_simulate=self.simulate
		)
		return None

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
		laser_tab = QWidget()
		self.laser_tab_layout = QHBoxLayout()
		laser_tab.setLayout(self.laser_tab_layout)
		self.laser_tab_index = tab_widget.addTab(laser_tab, "LuxX+ Controller")

		fsv_tab = QWidget()
		self.fsv_tab_layout = QHBoxLayout()
		fsv_tab.setLayout(self.fsv_tab_layout)
		self.fsv_tab_index = tab_widget.addTab(fsv_tab, "FSV3000 Controller")

		return tab_widget

	def _setup_menubar(self) -> None:
		menu_bar = self.menuBar()

		# create preset entry #
		preset_menu = menu_bar.addMenu("&Presets")
		save_preset = preset_menu.addAction("Save Preset")
		save_preset.triggered.connect(self._save_preset)

		load_preset = preset_menu.addAction("Load Preset")
		load_preset.triggered.connect(self._load_preset)

		# create expert mode toggle and port #
		mode_menu = menu_bar.addMenu("&Menu")
		expert_mode = mode_menu.addAction("Expert Mode")
		expert_mode.triggered.connect(self._toggle_expert_mode)

		port_select = mode_menu.addAction("Select Ports")
		port_select.triggered.connect(self._show_port_dialog)

		# BodePlot window #
		window_menu = menu_bar.addMenu("&Windows")
		bode_window = window_menu.addAction("BodePlot")
		bode_window.triggered.connect(self.open_bode_window)

	def _setup_widgets(self) -> None:

		self.stage_normal = StageWidgetNormal()
		self.stage_normal.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

		self.normal_tab_layout.addWidget(self.stage_normal)
		self.normal_tab_layout.addItem(QSpacerItem(100, 10))

		self.laser_normal = LaserWidgetNormal()
		self.laser_normal.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.normal_tab_layout.addWidget(self.laser_normal)

		self.stage_expert = StageWidgetExpert()
		self.stage_expert.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.stage_tab_layout.addWidget(self.stage_expert)

		self.freq_gen_expert1 = FrequencyGeneratorWidgetExpet(channel=1)
		self.freq_gen_expert1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_expert2 = FrequencyGeneratorWidgetExpet(channel=2)
		self.freq_gen_expert1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_expert3 = FrequencyGeneratorWidgetExpet(channel=3)
		self.freq_gen_expert1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_expert4 = FrequencyGeneratorWidgetExpet(channel=4)
		self.freq_gen_expert1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

		self.fsv_normal = FsvNormalWidget()
		self.fsv_normal.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.fsv_tab_layout.addWidget(self.fsv_normal)

		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert1)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert2)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert3)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert4)

		self.laser_expert1 = LaserWidgetExpert(
			index=1,
			max_power=self.Laser1.LuxX.max_power
		)
		self.laser_expert1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.laser_expert2 = LaserWidgetExpert(
			index=2,
			max_power=self.Laser2.LuxX.max_power
		)
		self.laser_expert2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

		self.laser_tab_layout.addWidget(self.laser_expert1)
		self.laser_tab_layout.addWidget(self.laser_expert2)

		return None

	def _toggle_expert_mode(self) -> None:
		visible = self.tab_panel.isTabVisible(self.stage_tab_index)

		self.tab_panel.setTabVisible(self.stage_tab_index, not visible)
		self.tab_panel.setTabVisible(self.freq_gen_tab_index, not visible)
		self.tab_panel.setTabVisible(self.laser_tab_index, not visible)
		return None

	def _setup_connections(self) -> None:
		self.info_panel.laser_info_signal.connect(self._show_laser_info_dialog)
		self.Stage.port_status_signal.connect(self.info_panel.update_indicator)
		self.Laser1.port_status_signal.connect(self.info_panel.update_indicator)
		self.Laser2.port_status_signal.connect(self.info_panel.update_indicator)
		self.FrequencyGenerator.port_status_signal.connect(self.info_panel.update_indicator)
		self.SpectrumAnylyzer.port_status_signal.connect(self.info_panel.update_indicator)

		self.info_panel.stage_port_signal.connect(self.Stage.manage_port)
		self.info_panel.freq_gen_port_signal.connect(self.FrequencyGenerator.manage_port)
		self.info_panel.laser1_port_signal.connect(self.Laser1.manage_port)
		self.info_panel.laser2_port_signal.connect(self.Laser2.manage_port)
		self.info_panel.fsv_port_signal.connect(self.SpectrumAnylyzer.manage_port)


		self.stage_normal.start_signal.connect(self.Stage.start)
		self.stage_expert.start_signal.connect(self.Stage.start)
		self.stage_normal.stop_signal.connect(self.Stage.stop)
		self.stage_expert.stop_signal.connect(self.Stage.stop)

		self.stage_normal.update_param_signal.connect(self.stage_normal.get_params)
		self.stage_normal.update_param_signal.connect(self.stage_expert.get_params)
		self.stage_expert.update_param_signal.connect(self.stage_expert.get_params)
		self.stage_expert.update_param_signal.connect(self.stage_normal.get_params)

		self.freq_gen_expert1.apply_signal.connect(self.FrequencyGenerator.apply)
		self.freq_gen_expert2.apply_signal.connect(self.FrequencyGenerator.apply)
		self.freq_gen_expert3.apply_signal.connect(self.FrequencyGenerator.apply)
		self.freq_gen_expert4.apply_signal.connect(self.FrequencyGenerator.apply)

		self.laser_expert1.apply_signal.connect(self.Laser1.apply)
		self.laser_expert2.apply_signal.connect(self.Laser2.apply)
		self.laser_normal.apply_signal_laser1.connect(self.Laser1.apply)
		self.laser_normal.apply_signal_laser2.connect(self.Laser2.apply)

		self.laser_normal.freq_gen_apply_ch1.connect(self.FrequencyGenerator.apply_on_normal)
		self.laser_normal.freq_gen_apply_ch2.connect(self.FrequencyGenerator.apply_on_normal)

		self.fsv_normal.start_signal.connect(self.SpectrumAnylyzer.start_measurement)

		self.Stage.__post_init__()
		self.FrequencyGenerator.__post_init__()
		self.Laser1.__post_init__()
		self.Laser2.__post_init__()
		self.SpectrumAnylyzer.__post_init__()
		return None

	def _setup_listeners(self) -> None:
		_stage_params = ["position", "speed", "accell", "deaccell"]
		for param in _stage_params:
			self.storage.new_listener("EcoVario", param,
									  [self.stage_normal.get_params, self.stage_expert.get_params])

		_tga_params = ["waveform", "frequency", "amplitude", "offset", "phase", "inputmode", "lockmode"]
		for param in _tga_params:
			self.storage.new_listener("TGA", param,
									  [self.freq_gen_expert1.get_params, self.freq_gen_expert2.get_params,
									   self.freq_gen_expert3.get_params, self.freq_gen_expert4.get_params])

		_laser_params = ["op_mode", "temp_power"]
		for param in _laser_params:
			self.storage.new_listener("LuxX1", param,
									  self.laser_expert1.get_params)
			self.storage.new_listener("LuxX2", param,
									  self.laser_expert2.get_params)

		_fsv_params = ["center_frequency", "span", "bandwidth", "sweep_points", "sweep_type", "meas_type", "unit"]
		for param in _fsv_params:
			self.storage.new_listener("FSV", param, self.fsv_normal.get_params)
		return None

	def _loop_calls(self) -> None:
		current_position = self.Stage.get_current_position()
		stage_error_code = self.Stage.get_current_error_code()

		self.storage.set("EcoVario", "current_position", current_position)
		self.storage.set("EcoVario", "error_code", stage_error_code)

		return None

	def _show_port_dialog(self) -> None:
		if self.port_dialog is None or not self.port_dialog.isVisible():
			self.port_dialog = PortSelectionWidget(
				self.def_stage_port,
				self.def_freq_gen_port,
				self.def_laser1_port,
				self.def_laser2_port,
				self.def_fsv_port
			)
			self.port_dialog.apply_signal.connect(self._set_ports)
			self.port_dialog.default_signal.connect(self._set_default_ports)
			self.port_dialog.show()
		else:
			self.port_dialog.raise_()

	def _show_laser_info_dialog(self) -> None:
		if self.laser_dialog is None or not self.laser_dialog.isVisible():
			firmware = [self.Laser1.LuxX.firmware, self.Laser2.LuxX.firmware]
			specs = [self.Laser1.LuxX.specs, self.Laser2.LuxX.specs]
			max_power = [self.Laser1.LuxX.max_power, self.Laser2.LuxX.max_power]
			self.laser_dialog = LaserInfoWidget(
				firmware,
				specs,
				max_power
			)
			self.laser_dialog.show()
		else:
			self.laser_dialog.raise_()

	def open_bode_window(self):
		if self.bode_window is None or not self.bode_window.isVisible():
			self.bode_window = BodePlotWindow()
			self.bode_plotter = BodePlot(self.FrequencyGenerator.TGA1244, self.SpectrumAnylyzer.FSV)
			self.bode_window.start_signal.connect(self.bode_plotter.get_bode)
			self.bode_plotter.data_signal.connect(self.bode_window.plot_bode)
			self.bode_window.show()
		else:
			self.bode_window.raise_()






