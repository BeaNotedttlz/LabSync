"""
Main application for controlling backend and frontend of the LabSync application.
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/core/labsync_app.py
@note:
"""
import traceback

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
from PySide6.QtWidgets import QMessageBox, QStatusBar

from src.core.storage import InstrumentCache
from src.core.utilities import ValueHandler, FilesUtils

from typing import Dict

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

	def __init__(self, app, file_dir: str) -> None:
		"""Constructor method
		"""
		super().__init__()

		# create cache
		self.cache = InstrumentCache()
		# handler for comparing values
		self.value_handler = ValueHandler()
		# File utility
		self.file_utils = FilesUtils(file_path=file_dir, file_name="settings.json")
		# Worker map
		self.workers = MapWorkers()
		self.device_ports = MapPorts()
		# Store pending workers still needed to be closed on quit
		self._pending_workers = set()

		# save file dir and simulate flag
		self.file_dir = file_dir
		self.simulate = True


		# initialize the device ports as None
		self.stage_port = None
		self.freq_gen_port = None
		self.laser1_port = None
		self.laser2_port = None
		self.fsv_port = None

		# create main window widgets
		self.main_window = MainWindow(app)

		# self.simulate = self.file_utils.read_settings()["debug_mode"]
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

		self.main_window.show()

		# connect signals
		# update connection status in UI
		self.connectionChanged.connect(self.main_window.update_connection_status)
		# Request worker quit on QCloseEvent
		self.main_window.requestClose.connect(self._cleanup_backend)
		self.main_window.deviceRequest.connect(self.request_worker)
		# Signal that the application can be closed
		self.shutdownFinished.connect(self.main_window.finalize_exit)

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
			"current_pos": [None, 0.0, 2530.0, "mm", float],
			"START": ["start", None, None, None, None],
			"STOP": ["stop", None, None, None, None]
		}
		laser_keys = {
			"temp_power": ["set_temp_power", 0.0, 100.0, "%", float],
			"operating_mode": ["set_op_mode", 0, 5, "", int],
			"emission_status": ["set_emission", None, None, "", bool]
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
			"avg_count": ["set_avg_count", 0, 1e3, "", int]
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
		# TODO rename 'name' to 'ID'
		# EcoVario Stage
		stage_instance = EcoConnect(name="EcoVario", simulate=self.simulate)
		self.stage_worker = WorkerHandler(device_id="EcoVario", driver_instance=stage_instance,
										  profile_instance=self.stage_profile)
		# LuxX+ Laser 1
		laser1_instance = OmicronLaser(name="Laser1", simulate=self.simulate)
		self.laser1_worker = WorkerHandler(device_id="Laser1", driver_instance=laser1_instance,
										   profile_instance=self.laser1_profile)
		# LuxX+ Laser 2
		laser2_instance = OmicronLaser(name="Laser2", simulate=self.simulate)
		self.laser2_worker = WorkerHandler(device_id="Laser2", driver_instance=laser2_instance,
										   profile_instance=self.laser2_profile)
		# TGA1244 Frequency Generator
		freq_gen_instance = FrequencyGenerator(name="TGA1244", simulate=self.simulate)
		self.freq_gen_worker = WorkerHandler(device_id="TGA1244", driver_instance=freq_gen_instance,
											 profile_instance=self.freq_gen_profile)
		# FSV3000 Spectrum Analyzer
		fsv_instance = SpectrumAnalyzer(name="FSV3000", simulate=self.simulate)
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

			self.connect_device(device_id, if_silent=True)
		return

	def _load_default_ports(self) -> None:
		"""
		Load the default ports of the devices.
		If the loading fails, the default hardcoded ports will be used and the broken file overwritten.

		:return: None
		"""
		ports = self.file_utils.read_port_file()
		self.stage_port = ports["EcoVario"][0]; self.stage_baudrate = ports["EcoVario"][1]
		self.laser1_port = ports["Laser1"][0]; self.laser1_baudrate = ports["Laser1"][1]
		self.laser2_port = ports["Laser2"][0]; self.laser2_baudrate = ports["Laser2"][1]
		self.freq_gen_port = ports["TGA1244"][0]; self.freq_gen_baudrate = ports["TGA1244"][1]
		self.fsv_port = ports["FSV3000"][0]; self.fsv_baudrate = ports["FSV3000"][1]

		for device_id, port in ports.items():
			self.device_ports.set_port(device_id, port)
		return

	@Slot(str, str, str, str, str)
	def _set_default_ports(self, stage: str, laser1: str, laser2: str,
						   freq_gen: str, fsv: str) -> None:
		"""
		Set the default ports of the devices. This is called by the ports dialog.
		TODO implement the baudrates

		:param stage: Stage port from dialog window
		:type stage: str
		:param laser1: Laser1 port from dialog window
		:type laser1: str
		:param laser2: Laser2 port from dialog window
		:type laser2: str
		:param freq_gen: Frequency generator from dialog window
		:type freq_gen: str
		:param fsv: FSV port from dialog window
		:type fsv: str
		:return: None
		:rtype: None
		"""
		try:
			self.file_utils.set_ports(stage, freq_gen, laser1, laser2, fsv)
			return
		except PortSetError as e:
			QMessageBox.critical(
				None,
				"Error",
				f"Something went wrong while saving the ports\n{e}"
			)
			return

	@Slot(str, str, str, str, str)
	def manage_device_ports(self, stage: str, laser1: str, laser2: str,
						   freq_gen: str, fsv: str) -> None:
		"""
		Disconnects all devices and requests a reconnect with new ports.
		:param stage: New stage port
		:type stage: str
		:param laser1: New laser 1 port
		:type laser1: str
		:param laser2: New laser 2 port
		:type laser2: str
		:param freq_gen: New frequency generator port
		:type freq_gen: str
		:param fsv: New FSV port
		:type fsv: str
		:return: None
		"""
		# set new device ports
		new_port_config = {
			"EcoVario": [stage, 9600],
			"Laser1": [laser1, 500000],
			"Laser2": [laser2, 500000],
			"TGA1244": [freq_gen, 9600],
			"FSV3000": fsv
		}
		for dev_id, new_port in new_port_config.items():
			handler = self.workers.worker[dev_id]

			if handler:
				cmd = DeviceRequest(
					device_id=dev_id,
					cmd_type=RequestType.CONNECT,
					value = new_port
				)
				handler.send_request(cmd)
				self.device_ports.set_port(dev_id, new_port)
			else:
				QMessageBox.critical(
					self.main_window,
					"Error",
					"Something went wrong!\n Missing device ID: {}".format(dev_id)
				)
		return

	def _disconnect_all(self) -> None:
		"""
		Disconnect all devices.
		:return: None
		"""
		for dev_id, handler in self.workers.worker.items():
			cmd = DeviceRequest(
				device_id=dev_id,
				cmd_type=RequestType.DISCONNECT,
			)
			handler.send_request(cmd)
		return

	@Slot()
	def connect_device(self, device_id, if_silent: bool=False) -> None:
		worker_handler = self.workers.worker[device_id]
		connect_request = DeviceRequest(
			device_id=device_id,
			cmd_type=RequestType.CONNECT,
			parameter="SILENT" if if_silent else None,
			value = self.device_ports.ports[device_id]
		)
		worker_handler.send_request(connect_request)
		return

	@Slot()
	def disconnect_device(self, device_id) -> None:
		worker_handler = self.workers.worker[device_id]
		disconnect_request = DeviceRequest(
			device_id=device_id,
			cmd_type=RequestType.DISCONNECT,
			value = None
		)
		worker_handler.send_request(disconnect_request)
		return

	@Slot(RequestResult)
	def receive_worker_result(self, result: RequestResult) -> None:
		"""
		Called when the worker finishes a request. This handles all request results.
		:param result: Result of the worker
		:type result: RequestResult
		:return: None
		"""
		if not result.is_success:
			self._handle_worker_error(result)
			return

		else:
			request_type, device_id, parameter = result.request_id.split("-")
			if request_type == "SET" or request_type == "POLL":
				self.cache.set_value(device_id, parameter, result.value)
				return
			elif request_type == RequestType.CONNECT.value or request_type == RequestType.DISCONNECT.value:
				self.connectionChanged.emit(device_id, result.value)
			else:
				pass

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




