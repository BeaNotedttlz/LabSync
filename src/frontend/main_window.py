"""
Main window module for the PySide6 LabSync application.
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/frontend/main_window.py
@note:
"""

from PySide6.QtWidgets import (QMainWindow, QApplication, QWidget,
							   QHBoxLayout, QSplitter, QGridLayout,
							   QMessageBox, QTabWidget, QSizePolicy,)
from PySide6.QtCore import Signal, Slot, Qt
from typing import Dict, Any

from src.frontend.widgets.devices.eco_normal import StageWidgetNormal
from src.frontend.widgets.info_panel import InfoPanelWidget

from src.core.context import UIRequest, RequestType

from src.frontend.widgets.devices.eco_expert import StageWidgetExpert
from src.frontend.widgets.devices.tga_expert import FrequencyGeneratorWidget
from src.frontend.widgets.devices.luxx_expert import LaserWidgetExpert


class MainWindow(QMainWindow):
	"""
	Main window class for the PySide6 LabSync application.

	:param app: Application instance.
	:rtype: QApplication
	"""
	# create signals
	deviceRequest = Signal(object)
	# close window
	requestClose = Signal()
	# save / load preset
	savePreset = Signal()
	loadPreset = Signal()
	# save ports
	savePorts = Signal(str, str, str, str, str)
	setDefaultPorts = Signal(str, str, str, str, str)

	def __init__(self, app) -> None:
		"""Constructor method
		"""
		super().__init__()
		# save the application instance to self.
		self.app = app

		# set window title
		self.setWindowTitle("LabSync")

		# create container widget and main layout
		container = QWidget()
		self.main_layout = QHBoxLayout()

		# make splitter for the info panel and tab widget
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

		# set splitter parameters to adjust size rations
		splitter.setStretchFactor(0, 1)
		splitter.setStretchFactor(1, 4)

		# add splitter to main layout and set central widget
		self.main_layout.addWidget(splitter)
		container.setLayout(self.main_layout)
		self.setCentralWidget(container)

		self._setup_menubar()
		self._setup_tabs()

	def closeEvent(self, event) -> None:
		"""
		closeEvent handler to manage port closing on application exit.

		:param event: The event at window close.
		:type event: QCloseEvent
		:return: None
		:rtype: None
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
			self.requestClose.emit()
			event.accept()
		else:
			# ignore event otherwise
			event.ignore()

	def _setup_menubar(self) -> None:
		"""
		Create the menubar of the LabSync application.

		:return: None
		:rtype: None
		"""
		# create menubar
		menu_bar = self.menuBar()

		# create preset entry #
		preset_menu = menu_bar.addMenu("&Presets")
		save_preset = preset_menu.addAction("Save Preset")
		save_preset.triggered.connect(self.savePreset)

		load_preset = preset_menu.addAction("Load Preset")
		load_preset.triggered.connect(self.loadPreset)

		# create expert mode toggle and port #
		mode_menu = menu_bar.addMenu("&Menu")
		expert_mode = mode_menu.addAction("Expert Mode")
		expert_mode.triggered.connect(self.toggle_expert_mode)

		# create port secltion and settings entrires
		port_select = mode_menu.addAction("Select Ports")
		port_select.triggered.connect(self._show_port_dialog)

		settings = mode_menu.addAction("Settings")
		settings.triggered.connect(self._show_settings_dialog)

		# BodePlot window #
		window_menu = menu_bar.addMenu("&Windows")
		bode_window = window_menu.addAction("BodePlot")
		bode_window.triggered.connect(self.open_bode_window)
		return

	def toggle_expert_mode(self) -> None:
		"""
		Toggle the application expert mode.

		:return: None
		:rtype: None
		"""
		is_visible = self.tab_panel.isTabVisible(self.stage_tab_index)

		self.tab_panel.setTabVisible(self.stage_tab_index, not is_visible)
		self.tab_panel.setTabVisible(self.freq_gen_tab_index, not is_visible)
		self.tab_panel.setTabVisible(self.laser_tab_index, not is_visible)
		return

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

	def _setup_widgets(self, laser1_max_power: int, laser2_max_power: int) -> None:
		self.eco_normal_widget = StageWidgetNormal(device_id="EcoVario")
		self.eco_normal_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.normal_tab_layout.addWidget(self.eco_normal_widget)

		self.eco_expert_widget = StageWidgetExpert(device_id="EcoVario")
		self.eco_expert_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.stage_tab_layout.addWidget(self.eco_expert_widget)

		self.freq_gen_expert_widget_1 = FrequencyGeneratorWidget(
			device_id="TGA1244",
			channel_index=1
		)
		self.freq_gen_expert_widget_1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert_widget_1)

		self.freq_gen_expert_widget_2 = FrequencyGeneratorWidget(
			device_id="TGA1244",
			channel_index=2
		)
		self.freq_gen_expert_widget_2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert_widget_2)

		self.freq_gen_expert_widget_3 = FrequencyGeneratorWidget(
			device_id="TGA1244",
			channel_index=3
		)
		self.freq_gen_expert_widget_3.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert_widget_3)

		self.freq_gen_expert_widget_4 = FrequencyGeneratorWidget(
			device_id="TGA1244",
			channel_index=4
		)
		self.freq_gen_expert_widget_4.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert_widget_4)

		self.laser_1_widget = LaserWidgetExpert(device_id="Laser1", laser_index=1,
												max_power=laser1_max_power)
		self.laser_1_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.laser_tab_layout.addWidget(self.laser_1_widget)

		self.laser_2_widget = LaserWidgetExpert(device_id="Laser2", laser_index=2,
												max_power=laser2_max_power)
		self.laser_2_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.laser_tab_layout.addWidget(self.laser_2_widget)
		return

	def update_connection_status(self, device_id: str, status: bool) -> None:
		return

	@Slot(Dict[str, str, Any])
	def handle_ui_request(self, request: Dict[str, str, Any]) -> None:
		"""
		Handles the request from a widget and formats it as a UIRequest object.
		This will then be sent to LabSync to finally send to device.
		:param request: Request object.
		:type request: Dict[str, str, Any]
		:return: None
		"""
		device_id = request["device_id"]
		parameter = request["parameter"]
		value = request["value"]

		cmd = UIRequest(
			device_id=device_id,
			parameter=parameter,
			cmd_type=RequestType.SET,
			value=value
		)
		self.deviceRequest.emit(cmd)
		return

	@Slot(Dict[str, str, Any])
	def update_ui_request(self, request: Dict[str, str, Any], sender: str) -> None:
		"""
		Gets an update from the widget and passes it to another.
		:param request: Request object.
		:type request: Dict[str, str, Any]
		:param sender: Sender ID
		:type sender: str
		:return: None
		"""
		if sender == "normal":
			self.eco_expert_widget.get_update(request)
			return
		elif sender == "expert":
			self.eco_normal_widget.get_update(request)
			return
		else:
			QMessageBox.warning(
				self,
				"UI Error",
				"An Interal UI Error occurred."
				"Unknown sender: {}".format(sender)
			)
			return


