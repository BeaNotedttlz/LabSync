"""
Module for the OmicronLaser functions. This handles most of the logic outside the backend driver.
@autor: Merlin Schmidt
@date: 2025-15-10
@file: Classes/App/LaserFunc.py
@note: use at your own risk.
"""

from Devices.Omircon import OmicronLaser
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QMessageBox
from src.utils import ParameterNotSetError, ParameterOutOfRangeError, DeviceParameterError


class LaserFunctions(QObject):
	"""
	LaserFunctions class for handling laser functions and logic.

	:param port: Device serial port
	:type port: str
	:param _storage: Parameter storage instance
	:type _storage: ParameterStorage
	:param _simulate: Flag for device simulation
	:type _simulate: bool
	:return: None
	:rtype: None
	"""
	# device signals
	port_status_signal = Signal(str, bool)
	emission_status_signal = Signal(str, bool)

	def __init__(self, port: str, _storage, index, _simulate: bool) -> None:
		"""Constructor method
		"""
		super().__init__()

		# save port and storage in self
		self.port = port
		self.storage = _storage
		self.index = index
		# create OmicronLaser backend driver
		self.LuxX = OmicronLaser(
			name="LuxX"+str(index),
			_storage=self.storage,
			simulate=_simulate
		)

	def __post_init__(self) -> None:
		"""
		Post init method that opens the port after signals have been routed.

		:return: None
		:rtype: None
		"""
		try:
			# try to open device port
			self.LuxX.open_port(self.port, baudrate=500000)
			# emit port status signal to change indicator
			self.port_status_signal.emit(f"Laser{self.index}Port", True)
		except ConnectionError:
			# if it fails send closed signal
			self.port_status_signal.emit(f"Laser{self.index}Port", False)

	@Slot(bool)
	def manage_port(self, state: bool) -> None:
		"""
		Manage device port after initial opening. This is called by pressing the status buttons.

		:param state: Desired state of the device port
		:type state: bool
		:return: None
		:rtype: None
		"""
		if state:
			try:
				self.LuxX.open_port(self.port, baudrate=500000)
				self.port_status_signal.emit(f"Laser{self.index}Port", True)
			except ConnectionError as e:
				self.port_status_signal.emit(f"Laser{self.index}Port", False)
				QMessageBox.information(
					None,
					"Error",
					"Could not open LuxX Port!\n%s"%e
				)
			return None
		else:
			self.LuxX.close_port()
			self.port_status_signal.emit(f"Laser{self.index}Port", False)
			return None

	@Slot( float, int, bool)
	def apply(self, temp_power, op_mode, emission) -> None:
		"""
		Apply the changed parameters to the Laser.

		:param temp_power: Target temporary device power
		:type temp_power: float
		:param op_mode: Target operating mode (1-5)
		:type op_mode: int
		:param emission: Status of the emission
		:type emission: bool
		:raises ParameterOutOfRangeError: If the temporary power exceeds 100%
		:raises DeviceParameterError: If a unsupported parameter get passed.
				This cannot happen for normal LabSync use.
		:return: None
		:rtype: None
		"""
		if temp_power > 100.0:
			# raise error if target power exceeds maximal power of 100%
			raise ParameterOutOfRangeError("Laser power cant exceed max power!")
		parameters = {
			"temp_power": temp_power,
			"op_mode": op_mode,
			"emission": emission
		}
		# set each provided device parameter
		for param, value in parameters.items():
			if not hasattr(self.LuxX, param):
				raise DeviceParameterError(f"LuxX: unsupported parameter {param}")
			try:
				if param == "emission":
					if op_mode != 0:
						self.manage_emission(value)
				else:
					setattr(self.LuxX, param, value)
			except ParameterNotSetError as e:
				QMessageBox.information(
					None,
					"Error",
					f"Could not set {param} to {value}!\n{e}"
				)
			except Exception as e:
				QMessageBox.information(
					None,
					"Error",
					str(e)
				)

	def manage_emission(self, state: bool) -> None:
		"""
		Manage the emission and signals of the device.

		:param state: Target emission state
		:type state: bool
		:return: None
		:rtype: None
		"""
		if state and not self.LuxX.emission:
			try:
				self.LuxX.emission = True
				self.emission_status_signal.emit(f"Laser{self.index}Status", True)
			except ParameterNotSetError as e:
				self.emission_status_signal.emit(f"Laser{self.index}Status", False)
				QMessageBox.information(
					None,
					"Error",
					f"{e}\n Check error!"
				)
			return None
		elif self.LuxX.emission and not state:
			try:
				self.LuxX.emission = False
				self.emission_status_signal.emit(f"Laser{self.index}Status", False)
			except ParameterNotSetError as e:
				self.emission_status_signal.emit(f"Laser{self.index}Status", True)
				QMessageBox.information(
					None,
					"Error",
					f"{e}\n Check error!"
				)
			return None
		return None

	@Slot()
	def reset_error(self) -> None:
		"""
		Reset the laser on error

		:return: None
		:rtype: None
		"""
		# TODO this does not work as of now
		try:
			self.LuxX.reset_controller()
		except TimeoutError as e:
			QMessageBox.information(
				None,
				"Error",
				f"Reset Timeout reached!\n{e}"
			)
		except Exception as e:
			QMessageBox.information(
				None,
				"Error",
				f"Could not reset controller!\n{e}"
			)