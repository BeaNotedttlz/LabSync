"""
Main application for controlling backend and frontend of the LabSync application.
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/core/labsync_app.py
@note:
"""
from src.core.context import DeviceRequest, RequestType
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
from src.core.mapping import Parameter, DeviceProfile
from src.core.utilities import PortSetError, DeviceConnectionError

from typing import Any, Dict
import os, json

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
	LabSync class for handling the core logic between frontend and backend.

	:return: None
	:rtype: None
	"""
	# define signals
	conectionChanged = Signal(str, bool)

	def __ini__(self, app, file_dir: str) -> None:
		"""Constructor method
		"""
		super().__init__()

		self.cache = InstrumentCache()
		self.value_handler = ValueHandler()
		self.file_utils = FilesUtils(file_path=file_dir, file_name="settings.json")

		self.file_dir = file_dir
		self.simulate = False
		self.workers = MapWorkers()

		self.stage_port = None
		self.freq_gen_port = None
		self.laser1_port = None
		self.laser2_port = None
		self.fsv_port = None

		self.main_window = MainWindow(app)
		return

	def _cleanup_backend(self) -> None:
		# TODO special close request for closeEvent?
		self.stage_worker.stop()
		self.laser1_worker.stop()
		self.laser2_worker.stop()
		self.freq_gen_worker.stop()
		self.fsv_worker.stop()
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
			self.stage_profile(Parameter(
				key=key,
				method=parameter[0],
				min_value=parameter[1],
				max_value=parameter[2],
				unit=parameter[3],
				datatype=parameter[4],
			))
		self.laser1_profile = DeviceProfile()
		for key, parameter in laser_keys.items():
			self.laser1_profile(Parameter(
				key=key,
				method=parameter[0],
				min_value=parameter[1],
				max_value=parameter[2],
				unit=parameter[3],
				datatype=parameter[4],
			))
		self.laser2_profile = DeviceProfile()
		for key, parameter in laser_keys.items():
			self.laser2_profile(Parameter(
				key=key,
				method=parameter[0],
				min_value=parameter[1],
				max_value=parameter[2],
				unit=parameter[3],
				datatype=parameter[4],
			))
		self.freq_gen_profile = DeviceProfile()
		for key, parameter in freq_gen_keys.items():
			self.freq_gen_profile(Parameter(
				key=key,
				method=parameter[0],
				min_value=parameter[1],
				max_value=parameter[2],
				unit=parameter[3],
				datatype=parameter[4],
			))
		self.fsv_profile = DeviceProfile()
		for key, parameter in fsv_keys.items():
			self.fsv_profile(Parameter(
				key=key,
				method=parameter[0],
				min_value=parameter[1],
				max_value=parameter[2],
				unit=parameter[3],
				datatype=parameter[4],
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
		laser2_instance = OmicronLaser(name="Laser1", simulate=self.simulate)
		self.laser2_worker = WorkerHandler(device_id="Laser1", driver_instance=laser2_instance,
										   profile_instance=self.laser2_profile)
		# TGA1244 Frequency Generator
		freq_gen_instance = FrequencyGenerator(name="TGA1244", simulate=self.simulate)
		self.freq_gen_worker = WorkerHandler(device_id="TGA", driver_instance=freq_gen_instance,
											 profile_instance=self.freq_gen_profile)
		# FSV3000 Spectrum Analyzer
		fsv_instance = SpectrumAnalyzer(name="FSV3000", simulate=self.simulate)
		self.fsv_worker = WorkerHandler(device_id="FSV3000", driver_instance=fsv_instance,
										profile_instance=self.fsv_profile)
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


	@Slot(str, str)
	def _handle_worker_error(self, id: str, error_msg: str) -> None:
		"""
		Executed when the worker encountered an error.

		:param error_msg: The error message
		:type error_msg: str
		:param id: ID of the error
		:type id: str
		:return: None
		:rtype: None
		"""
		if id == "CONN":
			QMessageBox.information(
				self.main_window,
				"Connection Error",
				f"Something went went wrong while connecting to the device\n{error_msg}"
			)
			self.conectionChanged.emit(id, False)
			return
		elif id.startswith("SET_"):
			device = id[4:]

	def receive_values(self, values: Dict[tuple, Any], force:bool=False) -> None:
		"""
		The gatekeeper logic checking if the values have already been set.
		This will then call the worker handler for further processing.

		:param values: Values received from the ui. dict[(device, parameter), value]
		:type values: Dict[tuple, Any]
		:param force: Flag to set when forcing the update of the parameter
		:type force: bool
		:raises AttributeError: If the parameter is not supported by the backend
		:return: None
		:rtype: None
		"""
		for key, value in values.items():
			parameter = self.device_profile.parameters[key]

			if not parameter:
				continue

			current_value = self.cache.get_value(key[0], key[1])
			if not self.value_handler.check_values(current_value, value) and not force:
				continue

			if not parameter.validate(value):
				QMessageBox.warning(
					self.main_window,
					"Input Error",
					f"Value: {value} for {key} is out of bounds!\n"
						f"Limit: {parameter.min_value} - {parameter.max_value} {parameter.unit}"
				)
				continue

			request_id = f"SET_{key[0]}-{key[1]}"
			device_handler = parameter.handler
			device_handler.request_task(request_id, parameter.method, value)
		return

	@Slot(str, object)
	def _handle_worker_finish(self, request_id: str, commited_value: Any) -> None:
		"""
		Executed when the worker successfully finished.

		:param request_id: ID of the request -> (SET|READ|POLL_device-parameter)
		:type request_id: str
		:param commited_value: value that was set
		:type commited_value: Any
		:return: None
		:rtype: None
		"""
		if request_id.startswith("SET_") or request_id.startswith("READ_"):
			parameter_key = request_id[4:].split("-")
			self.cache.set_value(parameter_key[0], parameter_key[1], commited_value)
		return


