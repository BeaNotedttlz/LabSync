"""
Main application for controlling backend and frontend of the LabSync application.
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/core/labsync_app.py
@note:
"""
import os
import numpy as np

from src.core.context import (DeviceRequest, RequestType, RequestResult,
							  ErrorType, DeviceProfile, Parameter)
from src.core.context import UIRequest
from src.core.utilities import PortSetError
from src.core.labsync_worker import WorkerHandler
from src.backend.devices.eco_connect import EcoConnect
from src.backend.devices.omicron import OmicronLaser
from src.backend.devices.tga import FrequencyGenerator
from src.backend.devices.fsv import SpectrumAnalyzer

from src.frontend.main_window import MainWindow

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QMessageBox, QFileDialog

from src.core.storage import InstrumentCache
from src.core.utilities import ValueHandler, FilesUtils

from typing import Dict, Any

class MapWorkers:
	"""
	Mapper for device workers and device ID. This allows for the easy access to the worker instance
	from the device ID.
	"""
	def __init__(self) -> None:
		"""Constructor method
		"""
		# internal worker storage
		self._workers: Dict[str, WorkerHandler] = {}
		return

	@property
	def worker(self) -> Dict[str, WorkerHandler]:
		"""
		Get the entire worker storage as a dictionary.
		:return: The workers in a dictionary.
		:rtype: Dict[str, WorkerHandler]
		"""
		return self._workers.copy()

	def set_worker(self, device_id: str, worker: WorkerHandler) -> None:
		"""
		Set new worker to the map. Note that this will not check if the worker already exists and just overwrite it.
		:param device_id: Device ID of the worker
		:type device_id: str
		:param worker: Worker instance
		:type worker: WorkerHandler
		:return: None
		"""
		self._workers[device_id] = worker
		return

class MapPorts:
	def __init__(self) -> None:
		self._ports: Dict[str, list] = {}
		return

	@property
	def ports(self) -> Dict[str, list]:
		return self._ports.copy()

	def set_port(self, device_id: str, port: list) -> None:
		self._ports[device_id] = port
		return


class LabSync(QObject):
	"""
	Core LabSync controller. This connects the frontend and the backend.
	"""
	# Signal to change connection status in the UI
	connectionChanged = Signal(str, bool)
	# Signal to allow closing of the application
	# This will be emitted once all workers and threads have been closed
	shutdownFinished = Signal()

	returnResult = Signal(RequestResult)

	returnStorageUpdate = Signal(str, str, object)

	def __init__(self, app, file_dir: str) -> None:
		"""Constructor method
		"""
		super().__init__()

		# create cache
		self.cache = InstrumentCache()
		self.cache.valueChanged.connect(self._handle_cache_update)
		# handler for comparing values
		self.value_handler = ValueHandler()
		# File utility
		self.file_utils = FilesUtils(file_path=file_dir, file_name="settings.json")
		# Worker map
		self.workers = MapWorkers()
		self.device_ports = MapPorts()
		# Store pending workers still needed to be closed on quit
		self._pending_workers = set()  # type: ignore[var-annotated]

		# save file dir and simulate flag
		self.file_dir = file_dir

		# initialize the device ports as None
		self.stage_port = None
		self.freq_gen_port = None
		self.laser1_port = None
		self.laser2_port = None
		self.fsv_port = None

		# create main window widgets
		self.main_window = MainWindow(app)
		self.main_window.show()

		try:
			self.simulate = self.file_utils.read_settings()["debug_mode"]
		except KeyError:
			self.simulate = False
			QMessageBox.warning(
				self.main_window,
				"Settings Load Error",
				"There was an error loading the settings file! "
				"The debug mode will be set to False. REALOAD FILE!"
			)

		if self.simulate:
			response = QMessageBox.question(
				self.main_window,
				"Debug Mode",
				"Debug Mode is activated! Do you want to continue?",
				QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
				QMessageBox.StandardButton.No
			)
			if response == QMessageBox.StandardButton.No:
				self.simulate = False
				self.file_utils.edit_settings("debug_mode", False)

		# connect signals
		# update connection status in UI
		self.connectionChanged.connect(self.main_window.update_connection_status)
		# Request worker quit on QCloseEvent
		self.main_window.requestClose.connect(self._cleanup_backend)
		self.main_window.deviceRequest.connect(self.request_worker)
		# Signal that the application can be closed
		self.shutdownFinished.connect(self.main_window.finalize_exit)
		self.returnResult.connect(self.main_window.handle_device_result)

		self.returnStorageUpdate.connect(self.main_window.get_cache_update)

		self.main_window.getCurrentPorts.connect(self._get_current_device_ports)
		self.main_window.savePorts.connect(self.manage_device_ports)
		self.main_window.setDefaultPorts.connect(self._set_default_ports)

		self.main_window.getSettings.connect(self._get_current_settings)
		self.main_window.saveSettings.connect(self._save_setting)

		self.main_window.savePreset.connect(self.save_preset)
		self.main_window.loadPreset.connect(self.load_preset)

		# Setup device profiles and Instances / Workers
		self._setup_profiles()
		return

	@Slot()
	def _cleanup_backend(self) -> None:
		"""
		Start clean up process of the devices and workers
		:return: None
		"""
		# clear all pending workers to be closed
		self._pending_workers.clear()

		# add all current workers to pending
		for worker_id, _ in self.workers.worker.items():
			self._pending_workers.add(worker_id)

		# finalize shutdown if no workers are pending
		if not self._pending_workers:
			self.shutdownFinished.emit()
			return

		# Start shutdown process for all current workers
		for _, handler in self.workers.worker.items():
			handler.start_shutdown()

		return

	@Slot()
	def _on_worker_finish(self, device_id: str) -> None:
		"""
		Log the finished closing of the worker. This will emit the shutdown signal if there are no more pending workers.
		:param device_id: ID of the device worker
		:type device_id: str
		:return: None
		"""
		# If the ID is currently pending remove from set
		if device_id in self._pending_workers:
			self._pending_workers.remove(device_id)

		# if no more pending devices quit application
		if not self._pending_workers:
			self.shutdownFinished.emit()

		return

	def _setup_profiles(self) -> None:
		"""
		Setup device parameter profiles needed for the initialization of the workers.
		:return: None
		"""
		ecovario_keys = {
			"target_pos": ["set_position", 0.0, 2530.0, "mm", float],
			"target_vel": ["set_speed", 0.0, 100.0, "mm/s", float],
			"target_acc": ["set_acceleration", 0.0, 1000.0, "mm/s2", float],
			"target_deacc": ["set_deacceleration", 0.0, 1000.0, "mm/s2", float],
			"current_pos": ["get_current_position", 0.0, 2530.0, "mm", float],
			"START": ["start", None, None, None, None],
			"STOP": ["stop", None, None, None, None],
			"HOME": ["home_stage", None, None, None, None],
			"RESET": ["reset_current_error", None, None, None, None],
			"current_error_code": ["get_current_error", None, None, None, None]
		}
		laser_keys = {
			"temp_power": ["set_temp_power", 0.0, 100.0, "%", float],
			"operating_mode": ["set_op_mode", 0, 5, "", int],
			"emission_status": ["set_emission", False, True, "", bool],
			"INFO": ["get_device_information", None, None, None, None]
		}
		freq_gen_keys = {
			"amplitude": ["set_amplitude", 0.0, 10.0, "V", float],
			"offset": ["set_offset", 0, 0, 10.0, "V", float],
			"frequency": ["set_frequency", 0, 0, 40e6, "Hz", float],
			"phase": ["set_phase", 0, 0, 360, "deg", float],
			"waveform": ["set_waveform", None, None, "", str],
			"lockmode": ["set_lockmode", None, None, "", str],
			"output": ["set_output", None, None, "", bool]
		}
		fsv_keys = {
			"center_freq": ["set_center_frequency", 0.0, 13.6e6, "Hz", float],
			"freq_span": ["set_span", 0.0, 13.6e6, "Hz", float],
			"bandwidth": ["set_bandwidth", 0.0, 13.6e6, "Hz", float],
			"unit": ["set_unit", None, None, "", str],
			"sweep_type": ["set_sweep_type", None, None, "", str],
			"sweep_points": ["set_sweep_points", 0, 1e6, "", int],
			"avg_count": ["set_avg_count", 0, 1e3, "", int],
			"measurement_type": ["start_measurement", None, None, "", str]
		}
		self.stage_profile = DeviceProfile()
		for key, parameter in ecovario_keys.items():
			self.stage_profile.add(Parameter(
				key=key,
				method=parameter[0],
				min_value=parameter[1],
				max_value=parameter[2],
				unit=parameter[3],
				data_type=parameter[4]
			))
		self.laser1_profile = DeviceProfile()
		for key, parameter in laser_keys.items():
			self.laser1_profile.add(Parameter(
				key=key,
				method=parameter[0],
				min_value=parameter[1],
				max_value=parameter[2],
				unit=parameter[3],
				data_type=parameter[4]
			))
		self.laser2_profile = DeviceProfile()
		for key, parameter in laser_keys.items():
			self.laser2_profile.add(Parameter(
				key=key,
				method=parameter[0],
				min_value=parameter[1],
				max_value=parameter[2],
				unit=parameter[3],
				data_type=parameter[4]
			))
		self.freq_gen_profile = DeviceProfile()
		for key, parameter in freq_gen_keys.items():
			self.freq_gen_profile.add(Parameter(
				key=key,
				method=parameter[0],
				min_value=parameter[1],
				max_value=parameter[2],
				unit=parameter[3],
				data_type=parameter[4]
			))
		self.fsv_profile = DeviceProfile()
		for key, parameter in fsv_keys.items():
			self.fsv_profile.add(Parameter(
				key=key,
				method=parameter[0],
				min_value=parameter[1],
				max_value=parameter[2],
				unit=parameter[3],
				data_type=parameter[4]
			))
		self._setup_devices()
		return

	def _setup_devices(self) -> None:
		"""
		Setup app device instances and initialize all workers and threads
		:return: None
		"""
		# check if any of the ports are missing and try to load ports again
		if None in [self.stage_port, self.laser1_port, self.laser2_port,
					self.freq_gen_port, self.fsv_port]:
			self._load_default_ports()
		# otherwise create devices and workers
		# EcoVario Stage
		stage_instance = EcoConnect(ID="EcoVario", simulate=self.simulate)
		self.stage_worker = WorkerHandler(device_id="EcoVario", driver_instance=stage_instance,
										  profile_instance=self.stage_profile)
		# LuxX+ Laser 1
		laser1_instance = OmicronLaser(ID="Laser1", simulate=self.simulate)
		self.laser1_worker = WorkerHandler(device_id="Laser1", driver_instance=laser1_instance,
										   profile_instance=self.laser1_profile)
		# LuxX+ Laser 2
		laser2_instance = OmicronLaser(ID="Laser2", simulate=self.simulate)
		self.laser2_worker = WorkerHandler(device_id="Laser2", driver_instance=laser2_instance,
										   profile_instance=self.laser2_profile)
		# TGA1244 Frequency Generator
		freq_gen_instance = FrequencyGenerator(ID="TGA1244", simulate=self.simulate)
		self.freq_gen_worker = WorkerHandler(device_id="TGA1244", driver_instance=freq_gen_instance,
											 profile_instance=self.freq_gen_profile)
		# FSV3000 Spectrum Analyzer
		fsv_instance = SpectrumAnalyzer(ID="FSV3000", simulate=self.simulate)
		self.fsv_worker = WorkerHandler(device_id="FSV3000", driver_instance=fsv_instance,
										profile_instance=self.fsv_profile)
		# Add all created workers to the Map with the corresponding IDs
		workers = {
			"EcoVario": self.stage_worker,
			"Laser1": self.laser1_worker,
			"Laser2": self.laser2_worker,
			"TGA1244": self.freq_gen_worker,
			"FSV3000": self.fsv_worker
		}
		for device_id, worker in workers.items():
			# Add worker instances
			self.workers.set_worker(device_id, worker)
			# connect finish signal for each worker
			worker.handlerFinished.connect(self._on_worker_finish)
			worker.receivedResult.connect(self.receive_worker_result)

			# Call helper method to connect to device
			# Silent flag to not show error messageboxes on startup
			self.connect_device(device_id, if_silent=True)
		# Set polling parameters for devices
		self._set_poll_parameters()
		return

	def _set_poll_parameters(self) -> None:
		"""
		Helper method to set all the polling parameters needed for the application
		:return: None
		"""
		# Get the stage worker from map
		stage_worker = self.workers.worker["EcoVario"]
		# Generate position polling request
		# Poll every 2000ms -> This needs to be changed later to a more dynamic approach
		position_poll = DeviceRequest(
			device_id="EcoVario",
			cmd_type=RequestType.START_POLL,
			parameter="current_pos",
			value=2000
		)
		# Generate error code polling request
		# Poll every 2000ms -> This needs to be changed later to a more dynamic approach
		error_poll = DeviceRequest(
			device_id="EcoVario",
			cmd_type=RequestType.START_POLL,
			parameter="current_error_code",
			value=2000
		)
		# Send polling requests to worker
		# stage_worker.send_request(position_poll)
		# stage_worker.send_request(error_poll)
		# initialize target position in cache
		# THis is done because the cache values are only set after a device request
		# TODO however this is bad design, need to find a better way -> initialize cache values on profile setup?
		self.cache.set_value("EcoVario", "target_pos", 0.0)
		return

	def _load_default_ports(self) -> None:
		"""
		Load the default ports of the devices.
		If the loading fails, the default hardcoded ports will be used and the broken file overwritten.

		:return: None
		"""
		# get the ports from the file using the file utils
		ports = self.file_utils.read_port_file()
		try:
			# get ports from the dictionary
			# Even on error this should return the default ports
			self.stage_port = ports["EcoVario"][0]; self.stage_baudrate = ports["EcoVario"][1]
			self.laser1_port = ports["Laser1"][0]; self.laser1_baudrate = ports["Laser1"][1]
			self.laser2_port = ports["Laser2"][0]; self.laser2_baudrate = ports["Laser2"][1]
			self.freq_gen_port = ports["TGA1244"][0]; self.freq_gen_baudrate = ports["TGA1244"][1]
			self.fsv_port = ports["FSV3000"][0]; self.fsv_baudrate = ports["FSV3000"][1]

			# Set device ports
			for device_id, port in ports.items():
				self.device_ports.set_port(device_id, port)
			return
		# If any key is missing reset the file to default ports
		# This should normally not happen due to the file utils implementation
		# But just to be safe any error will be handled and the default ports file overwritten
		except KeyError:
			# reset port file to default ports
			try:
				self.file_utils.set_ports("COM0", "COM1", "COM2", "COM3", "COM4", set_def=True)
			except PortSetError:
				QMessageBox.critical(
					self.main_window,
					"Critical Error",
					"Could not reset the device port file to default ports! "
					"Please check file permissions and restart the application."
				)
			# read the default ports again
			ports = self.file_utils.read_port_file()
			self.stage_port = ports["EcoVario"][0]; self.stage_baudrate = ports["EcoVario"][1]
			self.laser1_port = ports["Laser1"][0]; self.laser1_baudrate = ports["Laser1"][1]
			self.laser2_port = ports["Laser2"][0]; self.laser2_baudrate = ports["Laser2"][1]
			self.freq_gen_port = ports["TGA1244"][0]; self.freq_gen_baudrate = ports["TGA1244"][1]
			self.fsv_port = ports["FSV3000"][0]; self.fsv_baudrate = ports["FSV3000"][1]

			# Set device ports
			for device_id, port in ports.items():
				self.device_ports.set_port(device_id, port)

			# Show critical message box to notify user
			QMessageBox.critical(
				self.main_window,
				"Device Port Read Error",
				"There was an error reading the device port file! "
				"The file will be reset to default ports."
			)
			return

	@Slot(list, list, list, list, list)
	def _set_default_ports(self, stage: list, laser1: list, laser2: list,
						   freq_gen: list, fsv: list) -> None:

		try:
			self.file_utils.set_ports(stage, laser1, laser2, freq_gen, fsv)
			return
		except PortSetError:
			QMessageBox.critical(
				self.main_window,
				"Critical Error",
				"Could not reset the device port file to default ports! "
			)
			return

	@Slot(list, list, list, list, list)
	def manage_device_ports(self, stage: list, laser1: list, laser2: list,
						   freq_gen: list, fsv: list) -> None:

		# Define new device ports for easy access
		new_port_info = {
			"EcoVario": stage,
			"Laser1": laser1,
			"Laser2": laser2,
			"TGA1244": freq_gen,
			"FSV3000": fsv
		}

		for device_id, new_port_config in new_port_info.items():

			# Get device worker and current port
			worker = self.workers.worker.get(device_id, None)
			if worker is None:
				QMessageBox.warning(
					self.main_window,
					"Internal Error Occurred",
					"Something went wrong!\n Missing device ID: {}".format(device_id)
				)
			else:
				current_port_config = self.device_ports.ports.get(device_id, None)
				if new_port_config[1] is None:
					# If the baudrate is None, device uses TCPIP
					new_port_config = new_port_config[0]
					current_port_config = current_port_config[0]
				# Only disconnect and change port config if something changed
				if current_port_config != new_port_config:
					self.disconnect_device(device_id)
					# After device has been disconnected, set new port config and create open request
					cmd = DeviceRequest(
						device_id=device_id,
						cmd_type=RequestType.CONNECT,
						value=new_port_config
					)
					worker.send_request(cmd)
					self.device_ports.set_port(device_id, new_port_config)
		return

	@Slot()
	def connect_device(self, device_id, if_silent: bool=False) -> None:
		"""
		Helper method to send connect request to device workers.
		:param device_id: ID of the device to connect
		:type device_id: str
		:param if_silent: Silent flag to not show error messageboxes
		:type if_silent: bool
		:return: None
		"""
		# Get worker handler object from map
		worker_handler = self.workers.worker[device_id]
		# generate connect request
		connect_request = DeviceRequest(
			device_id=device_id,
			cmd_type=RequestType.CONNECT,
			parameter="SILENT" if if_silent else None,	# Add silent flag if needed
			value = self.device_ports.ports[device_id]
		)
		# send connect request to worker
		worker_handler.send_request(connect_request)
		return

	@Slot()
	def disconnect_device(self, device_id) -> None:
		"""
		Helper method to send disconnect request to device workers.
		:param device_id:
		:return:
		"""
		# get worker handler object from map
		worker_handler = self.workers.worker[device_id]
		# Generate disconnect request
		disconnect_request = DeviceRequest(
			device_id=device_id,
			cmd_type=RequestType.DISCONNECT,
			value = None
		)
		# send disconnect request to worker
		worker_handler.send_request(disconnect_request)
		return

	@Slot()
	def save_preset(self) -> None:
		"""
		Save the current chache as a preset file. This uses the custom lab_parser and the .gnt file format.

		:return: None
		"""
		# Get the save file path from the user with a file dialog
		save_path, _ = QFileDialog.getSaveFileName(
			self.main_window,
			"Save Preset File",
			os.path.join(os.path.dirname(self.file_dir), "presets"),
			"lab Files (*.gnt)"
		)
		# If the user selected a file path save the preset
		if save_path:
			# append .gnt file extension if not present
			# This is done to avoid user errors
			if not save_path.endswith(".gnt"):
				save_path += ".gnt"

			try:
				# Save the cache to the selected file path
				self.cache.save_cache(save_path)
			except Exception as e:
				QMessageBox.critical(
					self.main_window,
					"Preset Save Error",
					f"Could not save preset file!\n{e}"
				)
		else:
			QMessageBox.information(
				self.main_window,
				"Save Preset Cancelled",
				"No file selected, preset save cancelled."
			)
		return

	@Slot()
	def load_preset(self) -> None:
		"""
		Load a preset file into the current cache. This uses the custom lab_parser and the .gnt file format.

		:return: None
		"""
		# Get the load file path from the user with a file dialog
		preset_path, _ = QFileDialog.getOpenFileName(
			self.main_window,
			"Load Preset File",
			os.path.join(os.path.dirname(self.file_dir), "presets"),
		)
		# If the user selected a file path load the preset
		if preset_path:
			try:
				# Load the preset file into the cache
				self.cache.load_cache(preset_path)

			except Exception as e:
				QMessageBox.critical(
					self.main_window,
					"Preset Load Error",
					f"Could not load preset file!\n{e}"
				)
		else:
			QMessageBox.information(
				self.main_window,
				"Load Preset Cancelled",
				"No file selected, preset load cancelled."
			)
		return

	@Slot(RequestResult)
	def receive_worker_result(self, result: RequestResult) -> None:
		"""
		Called when the worker finishes a request. This handles all request results.
		:param result: Result of the worker
		:type result: RequestResult
		:return: None
		"""
		# Check if the result is an error
		if not result.is_success:
			# Handle the error accordingly
			self._handle_worker_error(result)
			return
		else:
			# Handle successful result
			# Get the request type, device ID and parameter from the request ID
			# This is done by splitting the request ID, since the format is known
			request_type, device_id, parameter = result.request_id.split("-")
			# Special handling for EcoVario position polling
			# This is done first to avoid necessary checking at higher polling rates
			if request_type == "POLL" and parameter == "current_pos":
				if result.value is not None:
					# Get actual float value
					current_position = float(result.value)
					# Emit the result to the UI
					self.returnResult.emit(result)
					# Get current target position from cache
					target_position = self.cache.get_value(device_id, "target_pos")
					# Check if current position is within tolerance of target position
					# Then update the EcoVario status indicator in the UI
					if np.abs(current_position - target_position) <= 0.01:
						self.main_window.info_panel.update_indicator("EcoVarioStatus", True)
					else:
						self.main_window.info_panel.update_indicator("EcoVarioStatus", False)
				else:
					# If the value is None the device is not connected! update accordingly
					# TODO: This should be avoided -> pause polling on disconnect?
					result.value = "Not Connected!"
					self.returnResult.emit(result)
			# Special handling for EcoVario position polling
			# This is done first to avoid necessary checking at higher polling rates
			elif request_type == "POLL" and parameter == "current_error_code":
				if result.value is None:
					# If the value is None the device is not connected! update accordingly
					# TODO: This should be avoided -> pause polling on disconnect?
					result.value = "Not Connected!"
				self.returnResult.emit(result)
			else:
				# For all other request types update handle accordingly
				if request_type == "SET" or request_type == "POLL":
					# Update the chache with the new value
					self.cache.set_value(device_id, parameter, result.value)
					# Handle Connect and Disconnect results
					# TODO: This should be handled in a better way -> remake this structure
				elif request_type == RequestType.CONNECT.value or request_type == RequestType.DISCONNECT.value:
					self.connectionChanged.emit(device_id, result.value)
				else:
					# I dont even know what this is?
					pass
		return

	def _handle_worker_error(self, error_result: RequestResult) -> None:
		"""
		Handles the error of a worker request. Shows the respective Messagebox with the needed information.
		:param error_result: Result with the error information
		:type error_result: RequestResult
		:return: None
		"""
		# Handle connection error
		if error_result.error_type == ErrorType.CONNECTION:
			# show message box with failed connection
			QMessageBox.critical(
				self.main_window,
				"Connection Error",
				f"Could not open {error_result.device_id} port!\n"
				f"{error_result.request_id}: {error_result.error}"
			)
			return
		# Handle initial connection error
		elif error_result.error_type == ErrorType.INIT_CONNECTION:
			# Only show status Bar error instead of MessageBox
			self.main_window.statusBar().showMessage(f"Device not found: {error_result.device_id}. Please connect manually!", 5000)
			return
		# Handle task execution error
		elif error_result.error_type == ErrorType.TASK:
			QMessageBox.critical(
				self.main_window,
				"Request Task Error",
				f"Could not do operation: {error_result.request_id} for device: {error_result.device_id}\n"
				f"{error_result.error}"
			)
			return
		# Handle all other errors
		else:
			QMessageBox.critical(
				self.main_window,
				"Unknown Error Occurred",
				f"Something went wrong! {error_result.request_id} for device: {error_result.device_id}\n"
				f"{error_result.error}"

			)
		return

	@Slot(UIRequest)
	def request_worker(self, request: UIRequest) -> None:
		"""
		A single entry point for UI requests
		:param request: Request from the User Interface
		:type request: UIRequest
		:return: None
		"""
		if request.cmd_type == RequestType.DISCONNECT or request.cmd_type == RequestType.CONNECT:
			# Handle connection and disconnection requests
			if request.value:
				self.connect_device(request.device_id)
			else:
				self.disconnect_device(request.device_id)
		else:
			# Handle all other requests
			device_request = DeviceRequest(
				device_id=request.device_id,
				cmd_type=request.cmd_type,
				parameter=request.parameter,
				value=request.value
			)
			# Get worker instance from Map
			worker = self.workers.worker[device_request.device_id]
			# Send request to worker instance
			worker.send_request(device_request)
		return

	@Slot()
	def _get_current_device_ports(self) -> None:
		"""
		Helper Method: Get the current device ports and emit to the ports dialog
		:return: None
		"""
		port_result = RequestResult(
			request_id="POLL-None-Ports",
			device_id="None",
			value=self.device_ports.ports
		)
		self.returnResult.emit(port_result)
		return

	@Slot()
	def _get_current_settings(self) -> None:
		"""
		Helper Method: Get the current application settings and emit to the settings dialog
		:return: None
		"""
		settings = self.file_utils.read_settings()
		settings_result = RequestResult(
			request_id="POLL-None-Settings",
			device_id="None",
			value=settings
		)
		self.returnResult.emit(settings_result)
		return

	@Slot(str, bool)
	def _save_setting(self, username: str, debug_mode: bool) -> None:
		"""
		Save a new application setting to the settings file.
		:return: None
		"""
		try:
			self.file_utils.edit_settings("username", username)
			self.file_utils.edit_settings("debug_mode", debug_mode)
			return
		except PortSetError as e:
			QMessageBox.critical(
				None,
				"Error",
				f"Something went wrong while saving the setting\n{e}"
			)
			return

	@Slot(str, str, object)
	def _handle_cache_update(self, device_id: str, parameter: str, value: Any) -> None:
		"""
		Update the cache with a new value.
		:param device_id: Device ID of the parameter
		:type device_id: str
		:param parameter: Parameter name
		:type parameter: str
		:param value: New value of the parameter
		:type value: Any
		:return: None
		"""
		# TODO: Not quite sure what this is useful for?
		self.returnStorageUpdate.emit(device_id, parameter, value)
		return