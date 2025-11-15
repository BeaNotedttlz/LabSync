"""
Module for the EcoConnect functions. This handles most of the logic outside the backend driver.
@author: Merlin Schmidt
@date: 2025-15-10
@file: Classes/App/EcoFunc.py
@note: use at your own risk.
"""

from Devices.EcoConnect import EcoConnect
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QMessageBox
import math
from src.utils import ParameterOutOfRangeError, DeviceParameterError

class EcoFunctions(QObject):
	"""
	EcoFunctions class for handling EcoConnect functions and logic.

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
	position_status_signal = Signal(str, bool)

	def __init__(self, port: str, _storage, _simulate: bool) -> None:
		"""Constructor method
		"""
		super().__init__()
		# save port and storage in self
		self.port = port
		self.storage = _storage
		# create EcoVario backend driver
		self.EcoVario = EcoConnect(
		    name="EcoVario",
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
			self.EcoVario.open_port(self.port, baudrate=9600)
			# emit port status signal to change indicator
			self.port_status_signal.emit("EcoVarioPort", True)
		except ConnectionError:
			# if it fails send closed signal
			self.port_status_signal.emit("EcoVarioPort", False)

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
				self.EcoVario.open_port(self.port, baudrate=9600)
				self.port_status_signal.emit("EcoVarioPort", True)
			except ConnectionError as e:
				self.port_status_signal.emit("EcoVarioPort", False)
				QMessageBox.information(
					None,
					"Error",
					"Could not open Stage Port!\n%s"%e
				)
			return None
		else:
			self.EcoVario.close_port()
			self.port_status_signal.emit("EcoVarioPort", False)
			return None

	@staticmethod
	def trunctate(number: float, decimals: int) -> float:
		"""
		Trunacte the position number to 4 digits. Further accurarcy is not needed due to the device variation.

		:param number: Number to trunctate
		:type number: float
		:param decimals: amount of decimals to use
		:type decimals: int
		:return: The trunctated number
		:rtype: float
		"""
		nbdecimals = len(str(number).split('.')[1])
		if nbdecimals <= decimals:
			return number
		stepper = 10.0 ** decimals
		return math.trunc(stepper * number) / stepper

	def get_current_position(self) -> float:
		"""
		Get the current position of the device. This method is supposed to be used in the loop call.

		:return: The current device position in mm
		:rtype: float
		"""
		# get the current device position
		current_position = self.EcoVario.get_current_position()
		if current_position is None:
			# return 0.0 if the device is not connected
			return 0.0
		# trunctate the position and get the target position
		current_position = float(self.trunctate(current_position, 4))
		target_position = float(self.EcoVario.position)

		# determine if actual position is roughly the target position
		if target_position-0.002 <= current_position <= target_position+0.002:
			self.position_status_signal.emit("EcoVarioStatus", True)
		else:
			self.position_status_signal.emit("EcoVarioStatus", False)

		# return the current position
		return current_position

	def get_current_error_code(self) -> str:
		"""
		Get the current device error code. This is supposed to be used in the loop call.

		:return: The current device error code
		:rtype: str
		"""
		# get current device error code
		current_error_code = self.EcoVario.get_last_error()
		if current_error_code is None:
			# return not connected on no return
			return "not connected"
		else:
			# otherwise return errorcode as string
			return str(current_error_code)

	@Slot(float, float, float, float)
	def start(self, position, speed, accell, deaccell) -> None:
		"""
		Get the current target parameters and start the stage.

		:param position: Target position for the stage
		:type position: float
		:param speed: Target speed for the stage
		:type speed: float
		:param accell: Target acceleration for the stage
		:type accell: float
		:param deaccell: Target deceleration for the stage
		:type deaccell: float
		:raises ParameterOutOfRangeError: If the stage position exceeds the maximal position
		:raises DeviceParameterError: If a unsupported parameter get passed.
				This cannot happen for normal LabSync use.
		:return: None
		:rtype: None
		"""
		if position >= 2530:
			# raise error if target position exceeds maximal position
			raise ParameterOutOfRangeError(f"{position} is out of range")
		parameters = {
			"position": position,
			"speed": speed,
			"accell": accell,
			"deaccell": deaccell
		}
		# set each provided device parameter
		for param, value in parameters.items():
			if not hasattr(self.EcoVario, param):
				raise DeviceParameterError(f"Stage: Unsupported parameter {param}")
			try:
				setattr(self.EcoVario, param, value)
			except Exception as e:
				QMessageBox.information(
					None,
					"Error",
					f"Could not set {param} to {value}!\n{e}"
				)
		try:
			# Start the stage
			self.EcoVario.start()
		except Exception as e:
			QMessageBox.information(
				None,
				"Error",
				f"Could not start Stage!\n{e}"
			)

	@Slot()
	def stop(self) -> None:
		"""
		Stop the stage.

		:return: None
		:rtype: None
		"""
		self.EcoVario.stop()

	@Slot()
	def reference_stage(self):
		"""
		Start stage referencing.

		:return: None
		:rtype: None
		"""
		# TODO this does not work as of now!
		try:
			self.EcoVario.set_homing()
		except Exception as e:
			QMessageBox.information(
				None,
				"Error",
				f"Could not set reference position!\n{e}"
			)