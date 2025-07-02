from PySide6.QtWidgets import QSpacerItem

from Classes.App.EcoFunc import EcoFunctions
from Classes.App.TgaFunc import FrequencyGeneratorFunctions
from Classes.App.LaserFunc import LaserFunctions

from Classes.Widgets.Dialogs import LaserInfoWidget, PortSelectionWidget
from Classes.Widgets.InfoPanel import InfoPanelWidget, LaserInfoWidget
from Classes.Widgets.EcoExpert import StageWidgetNormal
from Classes.Widgets.EcoNormal import StageWidgetExpert
from Classes.Widgets.LaserNormal import LaserWidgetNormal
from Classes.Widgets.TgaExpert import FrequencyGeneratorWidgetExpet
from Classes.Widgets.LaserExpert import LaserWidgetExpert

from Devices.storage import ParameterStorage
from LabSyncapp_old import LaserInfoDialog
from signals import SignalHandler


from PySide6.QtCore import Qt, Signal, Slot, QObject
from PySide6.QtWidgets import (QMainWindow, QApplication, QWidget, QHBoxLayout,
							   QSplitter, QMessageBox, QGridLayout, QVBoxLayout,
							   QFileDialog, QTabWidget, QSizePolicy)
import os, json

class MainWindow(QMainWindow):
	def __init__(self, app) -> None:
		super().__init__()
		self.app = app
		self.storage = ParameterStorage()
		self.signal_handler = SignalHandler()
		curr_file_dir = os.path.dirname(os.path.realpath(__file__))
		self.file_dir = os.path.join(curr_file_dir, "files")

		self.port_dialog = None
		self.laser_dialog = None

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

	def _setup_tabs(self) -> QTabWidget:
		tab_widget = QTabWidget()

		normal_tab = QWidget()
		self.normal_tab_layout = QHBoxLayout()
		normal_tab.setLayout(self.normal_tab_layout)
		tab_widget.addTab(normal_tab, "LabSync Controller")

		stage_tab = QWidget()
		self.stage_tab_layout = QHBoxLayout()
		stage_tab.setLayout(self.stage_tab_layout)
		self.stage_tab_index = tab_widget.addTab(stage_tab, "EcoVario Controller")

		freq_gen_tab = QWidget()
		self.freq_gen_tab_layout = QHBoxLayout()
		freq_gen_tab.setLayout(self.freq_gen_tab_layout)
		self.freq_gen_tab_index = tab_widget.addTab(freq_gen_tab, "TGA 1244 Controller")

		laser_tab = QWidget()
		self.laser_tab_layout = QHBoxLayout()
		laser_tab.setLayout(self.laser_tab_layout)
		self.laser_tab_index = tab_widget.addTab(laser_tab, "LuxX+ Controller")

		return tab_widget

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
					parameters = self.storage.get_all_parameters()
					parameters_list = [[list(key), value] for key, value in parameters.items()]
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
					self.storage.load_data_dict(parameters_restored)
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
				return None
		except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
			self.def_stage_port = "COM0"
			self.def_laser1_port = "COM1"
			self.def_laser2_port = "COM2"
			self.def_freq_gen_port = "COM3"
			QMessageBox.critical(
				self,
				"Error",
				f"Default ports file not found or broken\n{e}\n"
			)
			return None

	def _set_default_ports(self, stage: str, TGA1244: str, laser1: str, laser2: str) -> None:
		ports_dir = os.path.join(self.file_dir, "ports/default_ports.json")
		try:
			with open(ports_dir, "w") as file:
				ports = {
					"EcoVario": stage,
					"Laser1": laser1,
					"Laser2": laser2,
					"TGA1244": TGA1244
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
		)
		self.Laser1 = LaserFunctions(
			port=self.def_laser1_port,
			_storage=self.storage,
			index=1
		)
		self.Laser2 = LaserFunctions(
			port=self.def_laser2_port,
			_storage=self.storage,
			index=2
		)
		self.FrequencyGenerator = FrequencyGeneratorFunctions(
			port=self.def_freq_gen_port,
			_storage=self.storage
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


		self.stage_normal.start_signal.connect(self.Stage.start)
		self.stage_expert.start_signal.connect(self.Stage.start)
		self.stage_normal.stop_signal.connect(self.Stage.stop)
		self.stage_expert.stop_signal.connect(self.Stage.stop)

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

		self.Stage.__post_init__()
		self.FrequencyGenerator.__post_init__()
		self.Laser1.__post_init__()
		self.Laser2.__post_init__()
		return None

	def _show_port_dialog(self) -> None:
		if self.port_dialog is None or not self.port_dialog.isVisible():
			self.port_dialog = PortSelectionWidget(
				self.def_stage_port,
				self.def_freq_gen_port,
				self.def_laser1_port,
				self.def_laser2_port,
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
			self.laser_dialog = LaserInfoDialog(
				firmware,
				specs,
				max_power
			)
			self.laser_dialog.show()
		else:
			self.laser_dialog.raise_()




