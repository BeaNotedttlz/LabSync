"""
Main application for controlling backend and frontend of the LabSync application.
@author: Merlin Schmidt
@date: 2025-18-10
@file: src/core/labsync_app.py
@note:
"""

from src.core.labsync_worker import WorkerHandler
from src.backend.devices.eco_connect import EcoConnect
from src.backend.devices.omicron import OmicronLaser
from src.backend.devices.tga import FrequencyGenerator
from src.backend.devices.fsv import SpectrumAnalyzer

from src.frontend.main_window import MainWindow

from PySide6.QtCore import QObject, QEvent, Signal, Slot
from PySide6.QtWidgets import (QApplication, QMessageBox)
import os, json

from src.core.storage import InstrumentCache
from src.core.utilities import ValueHandler
from src.core.mapping import Parameter, DeviceProfile

from typing import Any, Dict

from src.core.utilities import (FilesUtils, SignalHandler,
								UIParameterError, DeviceParameterError,
								ParameterOutOfRangeError, ParameterNotSetError)


class LabSync(QObject):
	"""
	LabSync class for handling the core logic between frontend and backend.

	:return: None
	:rtype: None
	"""

	def __init__(self, app, _file_dir: str) -> None:
		super().__init__()

		self.cache = InstrumentCache()
		self.value_handler = ValueHandler()
		self.file_utility = FilesUtils(_file_dir, file_name="settings.json")

		self.file_dir = _file_dir
		self.simulate = False

		self.stage_port = None
		self.freq_gen_port = None
		self.laser1_port = None
		self.laser2_port = None
		self.fsv_port = None


		self.main_window = MainWindow(app)
		self.main_window.requestClose.connect(self._cleanup_backend)

		self._load_default_ports()

	def _cleanup_backend(self) -> None:
		self.Stage.cleanup()
		return

	def _load_default_ports(self) -> None:
		"""
		Load the default ports of the devices.
		If the loading fails, the default hardcoded ports will be used and the broken file overwritten.

		:return: None
		:rtype: None
		"""
		# set default ports file path
		ports_dir = os.path.join(self.file_dir, "ports", "default_settings.json")
		try:
			with open(ports_dir, "r") as file:
				# get ports from file
				settings = json.load(file)
			# set device ports
			self.stage_port = settings["EcoVario"][0]; self.stage_baudrate = settings["EcoVario"][1]
			return
		except Exception as e:
			# set to a hardcoded default on error
			self.stage_port = "COM0"; self.stage_baudrate = 9600
			self.laser1_port = "COM1"; self.laser1_baudrate = 500000
			self.laser2_port = "COM2"; self.laser2_baudrate = 500000
			self.freq_gen_port = "COM3"; self.freq_gen_baudrate = 9600
			self.fsv_port = "TCPIP::141.99.144.147::INSTR"
			ports = {
				"EcoVario": ["COM0", 9600],
				"Laser1": ["COM1", 500000],
				"Laser2": ["COM2", 500000],
				"TGA1244": ["COM3", 9600],
				"FSV3000": "COM3"
			}
			with open(ports_dir, "w") as file:
				json.dump(ports, file, ensure_ascii=False, indent=4)
			# show the error
			QMessageBox.critical(
				None,
				"Error",
				f"Default ports file not found or broken\n{e}\nThe file was restored!"
			)

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
		# get default ports file path
		ports_dir = os.path.join(self.file_dir, "ports", "default_settings.json")
		try:
			with open(ports_dir, "w") as file:
				ports = {
					"EcoVario": [stage, 9600],
					"Laser1": [laser1, 500000],
					"Laser2": [laser2, 500000],
					"TGA1244": [freq_gen, 9600],
					"FSV3000": fsv
				}
				json.dump(ports, file, ensure_ascii=False, indent=4)
			return
		except Exception as e:
			QMessageBox.critical(
				None,
				"Error",
				f"Something went wrong while saving the ports\n{e}"
			)

	def _setup_devices(self) -> None:
		"""
		Setup app device instances and initialize all workers and threads.

		:return: None
		:rtype: None
		"""
		if None in [self.stage_port, self.laser1_port, self.laser2_port,
					self.freq_gen_port, self.fsv_port]:
			# check if any of the ports is the initialized none and try to load ports again
			self._load_default_ports()
		# otherwise create devices and workers
		stage_instance = EcoConnect(name="EcoVario", simulate=self.simulate)
		self.Stage = WorkerHandler(stage_instance, self.stage_port, self.stage_baudrate)

		laser1_instance = OmicronLaser(name="Laser1", simulate=self.simulate)
		self.Laser1 = WorkerHandler(laser1_instance, self.laser1_port, self.laser1_baudrate)

		laser2_instance = EcoConnect(name="Laser2", simulate=self.simulate)
		self.Laser2 = WorkerHandler(laser2_instance, self.laser2_port, self.laser2_baudrate)

		freq_gen = FrequencyGenerator(name="TGA1244", simulate=self.simulate)
		self.TGA = WorkerHandler(freq_gen, self.freq_gen_port, self.freq_gen_baudrate)

		fsv_instance = EcoConnect(name="FSV3000", simulate=self.simulate)
		self.FSV = WorkerHandler(fsv_instance, self.fsv_port, None)

		self._make_profile()
		return

	def _make_profile(self) -> None:
		"""
		Creating the device profiles.
		Used for mapping and parameter management.

		:return: None
		:rtype: None
		"""
		self.device_profile = DeviceProfile()
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
		for key, params in ecovario_keys.items():
			self.device_profile.add(
				Parameter(
					key=("EcoVario", key),
					handler=self.Stage,
					method=params[0],
					min_value=params[1],
					max_value=params[2],
					unit=params[3],
					data_type=params[4],
				))
		for key, params in laser_keys.items():
			self.device_profile.add(
				Parameter(
					key=("Laser1", key),
					method=params[0],
					handler=self.Laser1,
					min_value=params[1],
					max_value=params[2],
					unit=params[3],
					data_type=params[4],
				))
			self.device_profile.add(
				Parameter(
					key=("Laser2", key),
					method=params[0],
					handler=self.Laser2,
					min_value=params[1],
					max_value=params[2],
					unit=params[3],
					data_type=params[4],
				))
		for key, params in freq_gen_keys.items():
			self.device_profile.add(
				Parameter(
					key=("TGA1244", key),
					method=params[0],
					handler=self.TGA,
					min_value=params[1],
					max_value=params[2],
					unit=params[3],
					data_type=params[4]
				))
		for key, params in fsv_keys.items():
			self.device_profile.add(
				Parameter(
					key=("FSV3000", key),
					method=params[0],
					handler=self.FSV,
					min_value=params[1],
					max_value=params[2],
					unit=params[3],
					data_type=params[4]
				))
		return

	def receive_values(self, values: Dict[tuple, Any], force:bool=None) -> None:
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
			parameter = self.device_profile.get(key)

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

			request_id = f"SET_{key[1]}"
			device_handler = parameter.handler
			device_handler.request_task(request_id, parameter.method, value)
		return



