"""
Main application window for LabSync.
@autor: Merlin Schmidt
@date: 2024-06-10
@file: LabSyncApp.py
@note: Use at your own risk.
"""

from Classes.App.EcoFunc import EcoFunctions
from Classes.App.TgaFunc import FrequencyGeneratorFunctions
from Classes.App.LaserFunc import LaserFunctions
from Classes.App.FsvFunc import FsvFunctions
from Classes.App.Bode import BodePlot

from Classes.Widgets.Dialogs import LaserInfoWidget, PortSelectionWidget, SettingsWidget
from Classes.Widgets.FsvBodeplot import BodePlotWindow
from Classes.Widgets.InfoPanel import InfoPanelWidget
from Classes.Widgets.EcoNormal import StageWidgetNormal
from Classes.Widgets.EcoExpert import StageWidgetExpert
from Classes.Widgets.LaserNormal import LaserWidgetNormal
from Classes.Widgets.TgaExpert import FrequencyGeneratorWidgetExpet
from Classes.Widgets.LaserExpert import LaserWidgetExpert
from Classes.Widgets.FsvNormal import FsvNormalWidget

from Devices.Storage import ParameterStorage
from src.utils import SignalHandler, FilesUtils

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout,
							   QSplitter, QMessageBox, QGridLayout,
							   QFileDialog, QTabWidget, QSizePolicy,
							   QSpacerItem)
import os, json

class MainWindow(QMainWindow):
	"""
	Main window class for the LabSync application.

	:param app: The application instance.
	:type app: QApplication
	:param _file_util: Utility for file operations.
	:type _file_util: FilesUtils
	:param _file_dir: Directory path for file storage.
	:type _file_dir: str
	:param _simulate: Flag to indicate simulation mode.
	:type _simulate: bool
	:return: None
	"""
	def __init__(self, app, _file_util, _file_dir: str, _simulate: bool) -> None:
		super().__init__()
		# save application to self variable
		self.app = app
		# create storage and signal handler objects
		self.storage = ParameterStorage()
		self.signal_handler = SignalHandler()
		# save file util and dir to self variables
		self.file_util = _file_util
		self.file_dir = _file_dir

		# initialize window variables
		self.port_dialog = None
		self.laser_dialog = None
		self.settings_dialog = None
		self.bode_window = None
		self.bode_plotter = None
		self.simulate = _simulate

		# set window title
		self.setWindowTitle("LabSync")

		# create container widget and main layout
		container = QWidget()
		self.main_layout = QHBoxLayout(container)

		# make splitter for info panel and tab widget
		splitter = QSplitter(Qt.Horizontal)
		splitter.setHandleWidth(0)
		splitter.setChildrenCollapsible(False)

		# make info panel layout and widget
		info_panel_layout = QGridLayout()
		info_panel_widget = QWidget()
		info_panel_widget.setLayout(info_panel_layout)
		self.info_panel = InfoPanelWidget()
		info_panel_layout.addWidget(self.info_panel, 0, 0)

		# add info panel and tab widget to splitter
		splitter.addWidget(info_panel_widget)
		self.tab_panel = self._setup_tabs()
		splitter.addWidget(self.tab_panel)

		# hide expert mode tabs by default
		self.tab_panel.setTabVisible(self.stage_tab_index, False)
		self.tab_panel.setTabVisible(self.freq_gen_tab_index, False)
		self.tab_panel.setTabVisible(self.laser_tab_index, False)

		# set splitter parameters to adjust size rations
		splitter.setStretchFactor(0, 1)
		splitter.setStretchFactor(1, 4)

		# add splitter to main layout and set central widget
		self.main_layout.addWidget(splitter)
		container.setLayout(self.main_layout)
		self.setCentralWidget(container)

		# call all methods for inital loading
		self._load_default_ports()
		self._setup_devices()
		self._setup_menubar()
		self._setup_widgets()
		self._setup_connections()
		self._setup_listeners()

	def closeEvent(self, event) -> None:
		"""
		closeEvent handler to manage port closing on application exit.

		:param event: The event at window close.
		:type event: QCloseEvent
		:return: None
		"""
		# Make QMessageBox to ask for confirmation
		response = QMessageBox.question(
			self,
			"Close LabSync?",
			"Do you want to close LabSync and close all ports?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No
		)
		if response == QMessageBox.StandardButton.Yes:
			# close ports and application
			self.Stage.EcoVario.close_port()
			self.FrequencyGenerator.TGA1244.close_port()
			self.Laser1.LuxX.close_port()
			self.Laser2.LuxX.close_port()
			event.accept()
		else:
			# ignore event otherwise
			event.ignore()

	def _save_preset(self) -> None:
		"""
		private save_preset method to save current parameters to a json file.

		:return: None
		"""
		# Get saev file path
		file_path = QFileDialog.getSaveFileName(
			self,
			"Save Parameters",
			self.file_dir,
			"Json Files (*.json)"
		)[0]
		if file_path:
			# add json if not set correctly
			if not file_path.endswith(".json"):
				file_path = file_path + ".json"
			with open(file_path, 'w') as file:
				try:
					# get all parameters and save to json
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
		"""
		private load_preset method to load parameters from a json file.

		:return: None
		"""
		# Get load file path
		file_path = QFileDialog.getOpenFileName(
			self,
			"Load Parameters",
			self.file_dir,
			"Json Files (*.json)"
		)[0]
		if file_path:
			with open(file_path, 'r') as file:
				try:
					# load parameters from json and restore to storage
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
		"""
		private load_default_ports method to load default device ports from json file.

		:return: None
		"""
		# set default ports file path
		ports_dir = os.path.join(self.file_dir, "ports/default_ports.json")
		try:
			with open(ports_dir, "r") as file:
				# get ports from file and save to self variables
				ports = json.load(file)
				self.def_stage_port = ports["EcoVario"]
				self.def_laser1_port = ports["Laser1"]
				self.def_laser2_port = ports["Laser2"]
				self.def_freq_gen_port = ports["TGA1244"]
				self.def_fsv_port = ports["FSV3000"]
				return None
		except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
			# for errors set default values
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
		"""
		private set_default_ports method to save default device ports to json file.

		:param stage: Stage port from dialog window
		:type stage: str
		:param TGA1244: TGA1244 port from dialog window
		:type stage: str
		:param laser1: Laser 1 port from dialog window
		:type laser1: str
		:param laser2: Laser 2 port from dialog window
		:type laser2: str
		:param fsv:	FSV3000 port from dialog window
		:type fsv: str
		:return: None
		"""
		# get default ports file path
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
				# dump ports to json file
				json.dump(ports, file, ensure_ascii=True, indent=4)
				return None
		except Exception as e:
			return print(f"{e}")

	@Slot(str, str, str, str)
	def _set_ports(self, stage, freq_gen, laser1, laser2) -> None:
		"""
		private set_ports slot to set device ports from dialog window.

		:param stage: Stage port from dialog window
		:type stage: str
		:param TGA1244: TGA1244 port from dialog window
		:type TGA1244: str
		:param laser1: Laser 1 port from dialog window
		:type laser1: str
		:param laser2: Laser 2 port from dialog window
		:type laser2: str
		:param fsv:	FSV3000 port from dialog window
		:type fsv: str
		:return: None
		"""
		# set ports to device functions
		self.Stage.port = stage
		self.FrequencyGenerator.port = freq_gen
		self.Laser1.port = laser1
		self.Laser2.port = laser2

		# close dialog window
		self.port_dialog.close()
		return None

	@Slot(str, bool)
	def _set_settings(self, username: str, debug_mode: bool) -> None:
		"""
		private set_settings slot to set application settings from dialog window.

		:param username: Username from dialog window
		:type username: str
		:param debug_mode: debug mode flag from dialog window
		:type debug_mode: bool
		:return: None
		"""
		# pass username to file utility
		self.file_util.edit_settings(
			setting_name="username",
			value=username
		)
		# pass debug mode to file utility
		self.file_util.edit_settings(
			setting_name="debug_mode",
			value=debug_mode
		)
		# close dialog window
		self.settings_dialog.close()
		return None

	def _setup_devices(self) -> None:
		"""
		private setup_devices method to initialize device functions

		:return: None
		"""
		# only check for stage port and load all ports if necessary
		if self.def_stage_port is None:
			self._load_default_ports()

		# create EcoFunctions object and device parameters
		self.Stage = EcoFunctions(
			port=self.def_stage_port,
			_storage=self.storage,
			_simulate=self.simulate
		)
		# create LaserFunctions objects for both lasers
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
		# create FrequencyGeneratorFunctions object
		self.FrequencyGenerator = FrequencyGeneratorFunctions(
			port=self.def_freq_gen_port,
			_storage=self.storage,
			_simulate=self.simulate
		)
		# create FsvFunctions object
		self.SpectrumAnylyzer = FsvFunctions(
			ip=self.def_fsv_port,
			_storage=self.storage,
			_simulate=self.simulate
		)
		return None

	def _setup_tabs(self) -> QTabWidget:
		"""
		private setup_tabs method to create tab widget with normal and expert mode tabs.

		:return: Tab widget object
		:rtype: QTabWidget
		"""
		# create tab widget
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

		# return widget for layout
		return tab_widget

	def _setup_menubar(self) -> None:
		"""
		private setup_menubar method to create menubar with preset, mode and window entries.

		:return: None
		"""
		# create menubar
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

		# create port secltion and settings entrires
		port_select = mode_menu.addAction("Select Ports")
		port_select.triggered.connect(self._show_port_dialog)

		settings = mode_menu.addAction("Settings")
		settings.triggered.connect(self._show_settings_dialog)

		# BodePlot window #
		window_menu = menu_bar.addMenu("&Windows")
		bode_window = window_menu.addAction("BodePlot")
		bode_window.triggered.connect(self.open_bode_window)

		return None

	def _setup_widgets(self) -> None:
		"""
		private setup_widgets method to create and add all widgets to the tab panels.

		:return: None
		"""

		# normal mode stage widgets
		self.stage_normal = StageWidgetNormal()
		self.stage_normal.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

		# normal mode laser & TGA widgets
		self.normal_tab_layout.addWidget(self.stage_normal)
		self.normal_tab_layout.addItem(QSpacerItem(100, 10))

		self.laser_normal = LaserWidgetNormal()
		self.laser_normal.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.normal_tab_layout.addWidget(self.laser_normal)

		# expert mode stage widget
		self.stage_expert = StageWidgetExpert()
		self.stage_expert.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.stage_tab_layout.addWidget(self.stage_expert)

		# expert mode TGA widgets
		self.freq_gen_expert1 = FrequencyGeneratorWidgetExpet(channel=1)
		self.freq_gen_expert1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_expert2 = FrequencyGeneratorWidgetExpet(channel=2)
		self.freq_gen_expert1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_expert3 = FrequencyGeneratorWidgetExpet(channel=3)
		self.freq_gen_expert1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_expert4 = FrequencyGeneratorWidgetExpet(channel=4)
		self.freq_gen_expert1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert1)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert2)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert3)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert4)

		# spectrum analyzer widgets
		self.fsv_normal = FsvNormalWidget()
		self.fsv_normal.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.fsv_tab_layout.addWidget(self.fsv_normal)

		# expert mode laser widgets
		self.laser_expert1 = LaserWidgetExpert(
			index=1
		)
		self.laser_expert1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.laser_expert2 = LaserWidgetExpert(
			index=2
		)
		self.laser_expert2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

		self.laser_tab_layout.addWidget(self.laser_expert1)
		self.laser_tab_layout.addWidget(self.laser_expert2)

		return None

	def _toggle_expert_mode(self) -> None:
		"""
		private toggle_expert_mode method to show/hide expert mode tabs.

		:return: None
		"""
		# check for current visibility and toggle tabs
		visible = self.tab_panel.isTabVisible(self.stage_tab_index)

		self.tab_panel.setTabVisible(self.stage_tab_index, not visible)
		self.tab_panel.setTabVisible(self.freq_gen_tab_index, not visible)
		self.tab_panel.setTabVisible(self.laser_tab_index, not visible)
		return None

	def _setup_connections(self) -> None:
		"""
		private setup_connections method to connect all signals and slots between widgets and device functions.

		:return: None
		"""
		# connect indicator signals and slots
		self.Laser1.emission_status_signal.connect(self.info_panel.update_indicator)
		self.Laser2.emission_status_signal.connect(self.info_panel.update_indicator)
		self.Stage.position_status_signal.connect(self.info_panel.update_indicator)

		# create port indicators and management connections
		self.info_panel.laser_info_signal.connect(self._show_laser_info_dialog)
		self.Stage.port_status_signal.connect(self.info_panel.update_indicator)
		self.Laser1.port_status_signal.connect(self.info_panel.update_indicator)
		self.Laser2.port_status_signal.connect(self.info_panel.update_indicator)
		self.FrequencyGenerator.port_status_signal.connect(self.info_panel.update_indicator)
		self.SpectrumAnylyzer.port_status_signal.connect(self.info_panel.update_indicator)

		# create port management connections
		self.info_panel.stage_port_signal.connect(self.Stage.manage_port)
		self.info_panel.freq_gen_port_signal.connect(self.FrequencyGenerator.manage_port)
		self.info_panel.laser1_port_signal.connect(self.Laser1.manage_port)
		self.info_panel.laser2_port_signal.connect(self.Laser2.manage_port)
		self.info_panel.fsv_port_signal.connect(self.SpectrumAnylyzer.manage_port)

		# create start and stop stage connections
		self.stage_normal.start_signal.connect(self.Stage.start)
		self.stage_expert.start_signal.connect(self.Stage.start)
		self.stage_normal.stop_signal.connect(self.Stage.stop)
		self.stage_expert.stop_signal.connect(self.Stage.stop)

		# create reset and homing connections
		self.stage_expert.reset_signal.connect(self.Stage.EcoVario.reset_error)
		self.stage_expert.homing_signal.connect(self.Stage.EcoVario.set_homing)

		# create parameter update connections
		self.stage_normal.update_param_signal.connect(self.stage_normal.get_params)
		self.stage_normal.update_param_signal.connect(self.stage_expert.get_params)
		self.stage_expert.update_param_signal.connect(self.stage_expert.get_params)
		self.stage_expert.update_param_signal.connect(self.stage_normal.get_params)

		# create apply connections for expert mode widgets
		self.freq_gen_expert1.apply_signal.connect(self.FrequencyGenerator.apply)
		self.freq_gen_expert2.apply_signal.connect(self.FrequencyGenerator.apply)
		self.freq_gen_expert3.apply_signal.connect(self.FrequencyGenerator.apply)
		self.freq_gen_expert4.apply_signal.connect(self.FrequencyGenerator.apply)

		# create apply connections for laser widgets
		self.laser_expert1.apply_signal.connect(self.Laser1.apply)
		self.laser_expert2.apply_signal.connect(self.Laser2.apply)
		self.laser_normal.apply_signal_laser1.connect(self.Laser1.apply)
		self.laser_normal.apply_signal_laser2.connect(self.Laser2.apply)

		# create frequency generator apply connections for normal mode laser widget
		self.laser_normal.freq_gen_apply_ch1.connect(self.FrequencyGenerator.apply_on_normal)
		self.laser_normal.freq_gen_apply_ch2.connect(self.FrequencyGenerator.apply_on_normal)

		# create spectrum analyzer start measurement connection
		self.fsv_normal.start_signal.connect(self.SpectrumAnylyzer.start_measurement)

		'''
		These post init methods are necessary to set the max power of the lasers correctly.
		The max power is called at the init of the laser port and therefore the port needs to be
		opened after the signals have been established.
		This can be improved by asking for the max power later
		'''
		self.Stage.__post_init__()
		self.FrequencyGenerator.__post_init__()
		self.Laser1.__post_init__()
		self.Laser2.__post_init__()
		# TODO this works but prob is really inconsistent, need to find a better way
		self.laser_expert1.max_power = self.Laser1.LuxX.max_power
		self.laser_expert2.max_power = self.Laser2.LuxX.max_power
		self.SpectrumAnylyzer.__post_init__()
		return None

	def _setup_listeners(self) -> None:
		"""
		private setup_listeners method to create parameter listeners for all device parameters.

		:return: None
		"""
		# add listeners for stage parameters
		_stage_params = ["position", "speed", "accell", "deaccell"]
		for param in _stage_params:
			self.storage.new_listener("EcoVario", param,
									  [self.stage_normal.get_params, self.stage_expert.get_params])

		# create listeners for frequency generator parameters
		_tga_params = ["waveform", "frequency", "amplitude", "offset", "phase", "inputmode", "lockmode"]
		for param in _tga_params:
			self.storage.new_listener("TGA", param,
									  [self.freq_gen_expert1.get_params, self.freq_gen_expert2.get_params,
									   self.freq_gen_expert3.get_params, self.freq_gen_expert4.get_params])

		# create listeners for laser parameters
		_laser_params = ["op_mode", "temp_power", "max_power"]
		for param in _laser_params:
			self.storage.new_listener("LuxX1", param,
									  self.laser_expert1.get_params)
			self.storage.new_listener("LuxX2", param,
									  self.laser_expert2.get_params)

		# create listeners for spectrum analyzer parameters
		_fsv_params = ["center_frequency", "span", "bandwidth", "sweep_points", "sweep_type", "meas_type", "unit"]
		for param in _fsv_params:
			self.storage.new_listener("FSV", param, self.fsv_normal.get_params)
		return None

	def loop_calls(self) -> None:
		"""
		loop_calls method to be called periodically for continuous updates.

		:return: None
		"""
		# get and update current stage position
		current_position = self.Stage.get_current_position()
		self.stage_normal.out_current_position.setText(str(current_position))
		self.stage_expert.out_current_position.setText(str(current_position))

		# get and update current stage error code
		stage_error_code = self.Stage.get_current_error_code()
		self.stage_normal.out_error_code.setText(str(stage_error_code))
		self.stage_expert.out_error_code.setText(str(stage_error_code))

		return None

	@Slot()
	def _show_port_dialog(self) -> None:
		"""
		private show_port_dialog slot to open port selection dialog.

		:return: None
		"""
		# create dialog if not already open
		if self.port_dialog is None or not self.port_dialog.isVisible():
			self.port_dialog = PortSelectionWidget(
				self.def_stage_port,
				self.def_freq_gen_port,
				self.def_laser1_port,
				self.def_laser2_port,
				self.def_fsv_port
			)
			# connect signals for method calls
			self.port_dialog.apply_signal.connect(self._set_ports)
			self.port_dialog.default_signal.connect(self._set_default_ports)
			self.port_dialog.show()
		else:
			# raise if already open
			self.port_dialog.raise_()

	@Slot()
	def _show_laser_info_dialog(self) -> None:
		"""
		private show_laser_info_dialog slot to open laser information dialog.

		:return: None
		"""
		# create dialog if not already open
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
			# raise if already open
			self.laser_dialog.raise_()

	@Slot()
	def _show_settings_dialog(self) -> None:
		"""
		private show_settings_dialog slot to open settings dialog.

		:return None
		"""
		# create dialog if not already open
		if self.settings_dialog is None or not self.settings_dialog.isVisible():
			username = ""
			self.settings_dialog = SettingsWidget(
				username,
				self.simulate
			)
			self.settings_dialog.show()
			# connect apply signal
			self.settings_dialog.apply_signal.connect(self._set_settings)
		else:
			# raise if already open
			self.settings_dialog.raise_()
		return None

	@Slot()
	def open_bode_window(self) -> None:
		"""
		open_bode_window slot to open Bode Plot window.

		:return: None
		"""
		# create window if not already open
		if self.bode_window is None or not self.bode_window.isVisible():
			self.bode_window = BodePlotWindow()
			self.bode_plotter = BodePlot(self.FrequencyGenerator.TGA1244, self.SpectrumAnylyzer.FSV)
			self.bode_window.start_signal.connect(self.bode_plotter.get_bode)
			self.bode_plotter.data_signal.connect(self.bode_window.plot_bode)
			self.bode_window.show()
		else:
			# raise if already open
			self.bode_window.raise_()
		return None






