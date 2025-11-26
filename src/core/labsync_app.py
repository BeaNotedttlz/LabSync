"""
Main application for controlling backend and frontend of the LabSync application.
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/core/labsync_app.py
@note:
"""
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
from PySide6.QtWidgets import QMessageBox

from src.core.storage import InstrumentCache
from src.core.utilities import ValueHandler, FilesUtils

from typing import Dict

class MapWorkers:
	def __init__(self) -> None:
		self._workers: Dict[str, WorkerHandler] = {}
	@property
	def worker(self) -> Dict[str, WorkerHandler]:
		return self._workers.copy()

	def set_worker(self, device_id: str, worker: WorkerHandler) -> None:
		self._workers[device_id] = worker

class LabSync(QObject):
	"""
	Core LabSync controller. This connects the frontend and the backend.
	"""
	connectionChanged = Signal(str, bool)
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
		self.main_window.show()

		# connect signals
		self.connectionChanged.connect(self.main_window.update_connection_status)
		self.main_window.requestClose.connect(self._cleanup_backend)
		self.shutdownFinished.connect(self.main_window.finalize_exit)
		self._setup_profiles()
		return

	@Slot()
	def _cleanup_backend(self) -> None:
		self._pending_workers.clear()

		for worker_id, _ in self.workers.worker.items():
			self._pending_workers.add(worker_id)

		if not self._pending_workers:
			self.shutdownFinished.emit()
			return

		for _, handler in self.workers.worker.items():
			handler.start_shutdown()

		return

	@Slot()
	def _on_worker_finish(self, device_id: str) -> None:
		if device_id in self._pending_workers:
			self._pending_workers.remove(device_id)

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
			for i in range(4):
				self.freq_gen_profile.add(Parameter(
					key=(i+1, key),
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
		workers = {
			"EcoVario": self.stage_worker,
			"Laser1": self.laser1_worker,
			"Laser2": self.laser2_worker,
			"TGA1244": self.freq_gen_worker,
			"FSV3000": self.fsv_worker
		}
		for device_id, worker in workers.items():
			self.workers.set_worker(device_id, worker)
			worker.handlerFinished.connect(self._on_worker_finish)
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
			request_type, device_id, parameter = result.request_id.split("_")
			if request_type == "SET" or request_type == "POLL":
				self.cache.set_value(device_id, parameter, result.value)
				return
			elif request_type == "CONNECT" or request_type == "DISCONNECT":
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
		if error_result.error_type == ErrorType.CONNECTION:
			QMessageBox.critical(
				self.main_window,
				"Connection Error",
				f"Could not open {error_result.device_id} port!\n"
				f"{error_result.request_id}: {error_result.error}"
			)
		elif error_result.error_type == ErrorType.TASK:
			QMessageBox.critical(
				self.main_window,
				"Request Task Error",
				f"Could not do operation: {error_result.request_id} for device: {error_result.device_id}\n"
				f"{error_result.error}"
			)
		else:
			QMessageBox.critical(
				self.main_window,
				"Unknown Error Occurred",
				f"Something went wrong! {error_result.request_id} for device: {error_result.device_id}\n"
				f"{error_result.error}"

			)
		return

	@Slot()
	def request_worker(self, cmd: DeviceRequest) -> None:
		device_handler = self.workers.worker[cmd.device_id]
		if device_handler:
			device_handler.send_request(cmd)
			return
		else:
			QMessageBox.critical(
				self.main_window,
				"Internal Error",
				"Device handler cannot be found \n"
				"If you dont know what this means commit an Issue on GitHub!"
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

		return




