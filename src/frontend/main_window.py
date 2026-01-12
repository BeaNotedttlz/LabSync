"""
Main window module for the PySide6 LabSync application.
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/frontend/main_window.py
@note:
"""

from PySide6.QtWidgets import (QMainWindow, QApplication, QWidget,
							   QHBoxLayout, QSplitter, QGridLayout,
							   QMessageBox, QTabWidget, QSizePolicy,
							   QSpacerItem)
from PySide6.QtCore import Signal, Slot, Qt
from typing import Dict, Any

from src.frontend.widgets.devices.eco_normal import StageWidgetNormal
from src.frontend.widgets.info_panel import InfoPanelWidget

from src.core.context import UIRequest, RequestType, RequestResult

from src.frontend.widgets.devices.eco_expert import StageWidgetExpert
from src.frontend.widgets.devices.tga_expert import FrequencyGeneratorWidget
from src.frontend.widgets.devices.luxx_expert import LaserWidgetExpert
from src.frontend.widgets.devices.luxx_normal import LaserWidgetNormal
from src.frontend.widgets.devices.fsv_normal import FsvNormalWidget

from src.frontend.widgets.dialogs import LaserInfoDialog, PortSelectionDialog, SettingsDialog

class MainWindow(QMainWindow):
	"""
	Main window class for the PySide6 LabSync application.
	"""
	# create signals
	deviceRequest = Signal(object)
	# close window
	requestClose = Signal()
	# save / load preset
	savePreset = Signal()
	loadPreset = Signal()
	# save / load ports
	savePorts = Signal(str, str, str, str, str)
	setDefaultPorts = Signal(str, str, str, str, str)
	getCurrentPorts = Signal()
	# save / load settings
	saveSettings = Signal(str, bool)
	getSettings = Signal()

	def __init__(self, app) -> None:
		"""Constructor method
		"""
		super().__init__()
		# save the application instance to self.
		self.app = app

		# initialize variables
		# intern window is ready to close
		self._is_ready_to_close = False
		# Laser info dialog object
		self.laser_dialog = None
		# Port dialog object
		self.port_dialog = None
		# Settings dialog object
		self.settings_dialog = None

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
		self.info_panel.updatePort.connect(self.handle_ui_port_request)
		self.info_panel.laserInfoSig.connect(self._show_laser_info_dialog)
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
		self._setup_widgets(1.0, 1.0)
		return

	def closeEvent(self, event) -> None:
		"""
		closeEvent handler to manage port closing on application exit.

		:param event: The event at window close.
		:type event: QCloseEvent
		:return: None
		:rtype: None
		"""
		# Make QMessageBox to ask for confirmation
		if self._is_ready_to_close:
			# close window if workers have quit
			event.accept()
			return

		# Otherwise ask to confirm
		response = QMessageBox.question(
			self,
			"Close LabSync?",
			"Do you want to close LabSync and close all ports?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No
		)

		# If yes, only emit request close signal and disable window
		if response == QMessageBox.StandardButton.Yes:
			# The close event will be ignored at first
			event.ignore()
			self.setEnabled(False)
			self.requestClose.emit()
			return
		else:
			# Otherwise ignore the close event
			event.ignore()
			return

	@Slot()
	def finalize_exit(self) -> None:
		"""
		Finalize the application exit after all workers have been closed.
		This will be called by the shutdownFinished signal from the AppController.
		:return: None
		"""
		self._is_ready_to_close = True
		self.close()
		return

	# TODO missing functionality
	def _setup_menubar(self) -> None:
		"""
		Create the menubar of the LabSync application.

		:return: None
		"""
		# create menubar
		menu_bar = self.menuBar()

		# create preset entry
		preset_menu = menu_bar.addMenu("&Presets")
		save_preset = preset_menu.addAction("Save Preset")
		save_preset.triggered.connect(self.savePreset)

		load_preset = preset_menu.addAction("Load Preset")
		load_preset.triggered.connect(self.loadPreset)

		# create expert mode toggle and port
		mode_menu = menu_bar.addMenu("&Menu")
		expert_mode = mode_menu.addAction("Expert Mode")
		expert_mode.triggered.connect(self.toggle_expert_mode)

		# create port secltion and settings entrires
		port_select = mode_menu.addAction("Select Ports")
		port_select.triggered.connect(self._show_port_dialog)

		settings_menu = menu_bar.addMenu("&Settings")
		edit_settings = settings_menu.addAction("Edit Settings")
		edit_settings.triggered.connect(self._show_settings_dialog)

		# TODO: BodePlot window not implemented yet
		# # BodePlot window #
		# window_menu = menu_bar.addMenu("&Windows")
		# bode_window = window_menu.addAction("BodePlot")
		# bode_window.triggered.connect(self.open_bode_window)
		return

	def toggle_expert_mode(self) -> None:
		"""
		Toggle the application expert mode.

		:return: None
		"""
		# get current visibility state of expert mode tabs
		is_visible = self.tab_panel.isTabVisible(self.stage_tab_index)

		# toggle visibility of expert mode tabs
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

		tab_widget.setTabVisible(self.stage_tab_index, False)
		tab_widget.setTabVisible(self.freq_gen_tab_index, False)
		tab_widget.setTabVisible(self.laser_tab_index, False)

		# return widget for layout
		return tab_widget

	def _setup_widgets(self, laser1_max_power: float, laser2_max_power: float) -> None:
		# Setup EcoVario normal mode Widgets
		self.eco_normal_widget = StageWidgetNormal(device_id="EcoVario")
		self.eco_normal_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.normal_tab_layout.addWidget(self.eco_normal_widget)
		self.normal_tab_layout.addItem(QSpacerItem(100, 10))
		# Connect Request signal to handler
		self.eco_normal_widget.sendRequest.connect(self.handle_ui_request)
		# Connect Update signal to handler, this is used to update the expert mode tab
		self.eco_normal_widget.sendUpdate.connect(self.update_ui_request)

		# Setup Laser normal mode Widgets
		self.laser_normal_widget = LaserWidgetNormal()
		self.laser_normal_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.normal_tab_layout.addWidget(self.laser_normal_widget)
		# Connect Request signal to handler
		self.laser_normal_widget.sendRequest.connect(self.handle_ui_request)
		# Connect Update signal to handler, this is used to update the expert mode tab
		self.laser_normal_widget.sendUpdate.connect(self.update_ui_request)

		# Setup EcoVario expert mode Widgets
		self.eco_expert_widget = StageWidgetExpert(device_id="EcoVario")
		self.eco_expert_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.stage_tab_layout.addWidget(self.eco_expert_widget)
		# Connect Request signal to handler
		self.eco_expert_widget.sendRequest.connect(self.handle_ui_request)
		# Connect Update signal to handler, this is used to update the normal mode tab
		self.eco_expert_widget.sendUpdate.connect(self.update_ui_request)

		# Setup TGA1244 expert mode Widgets
		self.freq_gen_expert_widget_1 = FrequencyGeneratorWidget(
			device_id="TGA1244",
			channel_index=1
		)
		self.freq_gen_expert_widget_1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert_widget_1)
		# Connect Request signal to handler
		self.freq_gen_expert_widget_1.sendRequest.connect(self.handle_ui_request)

		self.freq_gen_expert_widget_2 = FrequencyGeneratorWidget(
			device_id="TGA1244",
			channel_index=2
		)
		self.freq_gen_expert_widget_2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert_widget_2)
		# Connect Request signal to handler
		self.freq_gen_expert_widget_2.sendRequest.connect(self.handle_ui_request)

		self.freq_gen_expert_widget_3 = FrequencyGeneratorWidget(
			device_id="TGA1244",
			channel_index=3
		)
		self.freq_gen_expert_widget_3.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert_widget_3)
		# Connect Request signal to handler
		self.freq_gen_expert_widget_3.sendRequest.connect(self.handle_ui_request)

		self.freq_gen_expert_widget_4 = FrequencyGeneratorWidget(
			device_id="TGA1244",
			channel_index=4
		)
		self.freq_gen_expert_widget_4.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.freq_gen_tab_layout.addWidget(self.freq_gen_expert_widget_4)
		# Connect Request signal to handler
		self.freq_gen_expert_widget_4.sendRequest.connect(self.handle_ui_request)

		# Setup LuxX+ expert mode Widgets
		self.laser_1_widget = LaserWidgetExpert(device_id="Laser1", laser_index=1,
												max_power=laser1_max_power)
		self.laser_1_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.laser_tab_layout.addWidget(self.laser_1_widget)
		# Connect Request signal to handler
		self.laser_1_widget.sendRequest.connect(self.handle_ui_request)

		self.laser_2_widget = LaserWidgetExpert(device_id="Laser2", laser_index=2,
												max_power=laser2_max_power)
		self.laser_2_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.laser_tab_layout.addWidget(self.laser_2_widget)
		# Connect Request signal to handler
		self.laser_2_widget.sendRequest.connect(self.handle_ui_request)

		# Setup FSV3000 normal mode Widgets
		self.fsv_normal_widget = FsvNormalWidget(device_id="FSV3000")
		self.fsv_normal_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
		self.fsv_tab_layout.addWidget(self.fsv_normal_widget)
		# Connect Request signal to handler
		self.fsv_normal_widget.sendRequest.connect(self.handle_ui_request)
		return

	def update_connection_status(self, device_id: str, status: bool) -> None:
		"""
		Updates the connection status indicator in the info panel.
		:param device_id: ID of the device for the connection status change.
		:type device_id: str
		:param status: Status of the connection.
		:type status: bool
		:return: None
		"""
		self.info_panel.update_indicator(device_id, status)
		return

	@Slot(dict)
	def handle_ui_request(self, request: Dict[tuple, Any]) -> None:
		"""
		Handles the request from a widget and formats it as a UIRequest object.
		This will then be sent to LabSync to finally send to device.
		:param request: Request object.
		:type request: Dict[str, str, Any]
		:return: None
		"""
		# iterate over request dict and create UIRequest objects
		for keys, value in request.items():
			device_id = keys[0]
			parameter = keys[1]
			# create UIRequest object
			cmd = UIRequest(
				device_id=device_id,
				cmd_type=RequestType.SET,
				parameter=parameter,
				value=value
			)
			# send update request to device / worker through AppController
			self.deviceRequest.emit(cmd)
		return

	@Slot(str, bool)
	def handle_ui_port_request(self, device_id: str, status: bool) -> None:
		"""
		Handles the port connection / disconnection request from the info panel.
		:param device_id: ID of the device for the port request.
		:type device_id: str
		:param status: Status of the connection (True = connect, False = disconnect).
		:type status: bool
		:return: None
		"""
		cmd = UIRequest(
			device_id=device_id,
			cmd_type=(RequestType.CONNECT if status else RequestType.DISCONNECT),
			value=status
		)
		self.deviceRequest.emit(cmd)
		return

	@Slot(dict)
	def update_ui_request(self, request: Dict[tuple, Any], sender: str) -> None:
		"""
		Gets an update from the widget and passes it to another.
		:param request: Request object.
		:type request: Dict[str, str, Any]
		:param sender: Sender ID
		:type sender: str
		:return: None
		"""
		# determine sender and pass update to respective widget
		if sender == "normal":
			self.eco_expert_widget.get_update(request)
			return
		elif sender == "expert":
			self.eco_normal_widget.get_update(request)
			return
		elif sender == "laser":
			# TODO normal mode laser widget updating respective expert mode widgets
			pass
		else:
			QMessageBox.warning(
				self,
				"UI Error",
				"An Interal UI Error occurred."
				"Unknown sender: {}".format(sender)
			)
			return

	@Slot(RequestResult)
	def handle_device_result(self, result: RequestResult) -> None:
		"""
		Handles the result from a device request and updates the UI accordingly.
		:param result: Result object from device request.
		:type result: RequestResult
		:return: None
		"""
		# parse request ID with the known request ID format
		request_type, device_id, parameter = result.request_id.split("-")
		if request_type == "SET" and parameter == "emission_status":
			# update emission status indicator in info panel
			self.info_panel.update_indicator(device_id+"Status", result.value)

		if request_type == "POLL" and parameter == "current_pos":
			# update current position in both normal and expert mode widgets
			self.eco_normal_widget.get_update(
				{(device_id, "current_pos"): result.value}
			)
			self.eco_expert_widget.get_update(
				{(device_id, "current_pos"): result.value}
			)
		elif request_type == "POLL" and parameter == "current_error_code":
			# update current error code in both normal and expert mode widgets
			self.eco_normal_widget.get_update(
				{(device_id, "error_code"): result.value}
			)
			self.eco_expert_widget.get_update(
				{(device_id, "error_code"): result.value}
			)

		if request_type == "POLL" and parameter == "INFO":
			# update laser info dialog if open
			if self.laser_dialog is not None:
				# TODO this works - is there a better way?
				if result.value is None:
					return
				data = {
					device_id: result.value
				}
				self.laser_dialog.update_info(data)
		elif request_type == "POLL" and parameter == "Ports":
			# update port dialog if open
			if self.port_dialog is not None:
				self.port_dialog.get_current_ports(result.value)
		elif request_type == "POLL" and parameter == "Settings":
			# update settings dialog if open
			if self.settings_dialog is not None:
				self.settings_dialog.load_settings(result.value)
		return

	@Slot()
	def _show_laser_info_dialog(self) -> None:
		"""
		Helper method to show the laser info dialog or raise it if already open.
		:return: None
		"""
		if self.laser_dialog is None:
			# Create new dialog if not open
			self.laser_dialog = LaserInfoDialog(self)

			# connect the finished signal to the close handler
			self.laser_dialog.finished.connect(self._on_laser_dialog_closed)
			self.laser_dialog.show()
		else:
			if not self.laser_dialog.isVisible():
				# Show dialog if not visible
				self.laser_dialog.show()
			# Raise dialog to front
			self.laser_dialog.raise_()

		# Request laser info from both lasers
		# This asynchronously updates the dialog when results arrive, fields will be initialized differently and updated.
		for device in ["Laser1", "Laser2"]:
			info_request = UIRequest(
				device_id=device,
				cmd_type=RequestType.POLL,
				parameter="INFO",
				value=None
			)
			self.deviceRequest.emit(info_request)
		return

	@Slot()
	def _on_laser_dialog_closed(self) -> None:
		"""
		Handler for laser info dialog closed event.
		:return: None
		"""
		# disconnect the finished signal
		self.laser_dialog.finished.disconnect(self._on_laser_dialog_closed)
		# set dialog object to None
		self.laser_dialog = None
		return

	@Slot()
	def _show_port_dialog(self) -> None:
		"""
		Helper method to show the port selection dialog or raise it if already open.
		:return: None
		"""
		if self.port_dialog is None:
			# Create new dialog if not open
			self.port_dialog = PortSelectionDialog(self)
			# connect the finished signal to the close handler
			self.port_dialog.finished.connect(self._on_port_dialog_closed)
			self.port_dialog.applyPorts.connect(self.savePorts)
			self.port_dialog.defaultPorts.connect(self.setDefaultPorts)
			self.port_dialog.applyPorts.connect(lambda: self.port_dialog.close())
			# show dialog
			self.port_dialog.show()
		else:
			if not self.port_dialog.isVisible():
				# show dialog if not visible
				self.port_dialog.show()
			# raise dialog to front
			self.port_dialog.raise_()
		# Request current ports
		# This asynchronously updates the dialog when results arrive, fields will be initialized differently and updated.
		self.getCurrentPorts.emit()
		return

	@Slot()
	def _on_port_dialog_closed(self) -> None:
		"""
		Handler for port dialog closed event.
		:return: None
		"""
		# disconnect the finished signal
		self.port_dialog.finished.disconnect(self._on_port_dialog_closed)
		self.port_dialog.applyPorts.disconnect(self.savePorts)
		self.port_dialog.defaultPorts.disconnect(self.setDefaultPorts)
		# set dialog object to None
		self.port_dialog = None
		return

	@Slot()
	def _show_settings_dialog(self) -> None:
		"""
		Helper method to show the settings dialog or raise it if already open.
		:return: None
		"""
		if self.settings_dialog is None:
			# Create new dialog if not open
			self.settings_dialog = SettingsDialog(self)
			# connect the finished signal to the close handler
			self.settings_dialog.finished.connect(self._on_settings_dialog_closed)
			self.settings_dialog.applySettings.connect(self.saveSettings)
			self.settings_dialog.applySettings.connect(lambda: self.settings_dialog.close())
			self.settings_dialog.show()
		else:
			if not self.settings_dialog.isVisible():
				# show dialog if not visible
				self.settings_dialog.show()
			# raise dialog to front
			self.settings_dialog.raise_()

		# Request current settings
		# This asynchronously updates the dialog when results arrive, fields will be initialized differently and updated
		self.getSettings.emit()
		return

	@Slot()
	def _on_settings_dialog_closed(self) -> None:
		"""
		Handler for settings dialog closed event.
		:return: None
		"""
		# disconnect the finished signal
		self.settings_dialog.finished.disconnect(self._on_settings_dialog_closed)
		self.settings_dialog.applySettings.disconnect(self.saveSettings)
		# set dialog object to None
		self.settings_dialog = None
		return

	@Slot(str, str, object)
	def get_cache_update(self, device_id: str, parameter: str, value: Any) -> None:
		"""
		Handles cache updates from the storage system.
		:param device_id: Device ID
		:type device_id: str
		:param parameter: Parameter name
		:type parameter: str
		:param value: Update value
		:type value: Any
		:return: None
		"""
		if device_id == "EcoVario":
			# update both normal and expert mode widgets
			self.eco_normal_widget.get_update({(device_id, parameter): value})
			self.eco_expert_widget.get_update({(device_id, parameter): value})
		elif device_id == "Laser1" or device_id == "Laser2":
			# update respective expert mode widget
			if device_id == "Laser1":
				# update laser 1 expert mode widget
				self.laser_1_widget.get_update({(device_id, parameter): value})
			else:
				# update laser 2 expert mode widget
				self.laser_2_widget.get_update({(device_id, parameter): value})
		elif device_id == "TGA1244":
			# determine channel index from value tuple
			channel_index = int(value[1])
			# update respective frequency generator expert mode widget
			if channel_index == 1:
				self.freq_gen_expert_widget_1.get_update({(device_id, parameter): value})
			elif channel_index == 2:
				self.freq_gen_expert_widget_2.get_update({(device_id, parameter): value})
			elif channel_index == 3:
				self.freq_gen_expert_widget_3.get_update({(device_id, parameter): value})
			elif channel_index == 4:
				self.freq_gen_expert_widget_4.get_update({(device_id, parameter): value})
		elif device_id == "FSV3000":
			# update FSV3000 normal mode widget
			self.fsv_normal_widget.get_update({(device_id, parameter): value})
		else:
			# unknown device ID
			QMessageBox.warning(
				self,
				"UI Error",
				"An Interal UI Error occurred."
				"Unknown device ID: {}".format(device_id)
			)
		return