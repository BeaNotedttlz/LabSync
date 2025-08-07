'''
Interface of backend EcoVario functions and PySide6 Frontend
'''
from Devices.EcoConnect import EcoConnect
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QMessageBox
import math
from Exceptions import ParameterOutOfRangeError, DeviceParameterError

class EcoFunctions(QObject):
	port_status_signal = Signal(str, bool)
	position_status_signal = Signal(str, bool)

	def __init__(self, port: str, _storage, _simulate: bool) -> None:
		super().__init__()

		self.open_port = False
		self.port = port
		self.storage = _storage
		self.EcoVario = EcoConnect(
		    name="EcoVario",
		    _storage=self.storage,
		    simulate=_simulate
		)

	def __post_init__(self) -> None:
		try:
			self.EcoVario.open_port(self.port, baudrate=9600)
			self.open_port = True
			self.port_status_signal.emit("EcoVarioPort", True)
		except ConnectionError:
			self.open_port = False
			self.port_status_signal.emit("EcoVarioPort", False)

	@Slot(bool)
	def manage_port(self, state: bool) -> None:
		if state:
			try:
				self.EcoVario.open_port(self.port, baudrate=9600)
				self.open_port = True
				self.port_status_signal.emit("EcoVarioPort", True)
			except ConnectionError as e:
				self.open_port = False
				self.port_status_signal.emit("EcoVarioPort", False)
				QMessageBox.information(
					None,
					"Error",
					"Could not open Stage Port!\n%s"%e
				)
				return None
		else:
			self.EcoVario.close_port()
			self.open_port = False
			self.port_status_signal.emit("EcoVarioPort", False)
			return None

	@staticmethod
	def trunctate(number: float, decimals: int) -> float:
		nbdecimals = len(str(number).split('.')[1])
		if nbdecimals <= decimals:
			return number
		stepper = 10.0 ** decimals
		return math.trunc(stepper * number) / stepper

	def get_current_position(self) -> float:
		current_position = self.EcoVario.get_current_position()
		if current_position is None:
			return 0.0
		current_position = self.trunctate(current_position, 4)
		target_position = self.EcoVario.position

		if target_position-0.002 <= current_position <= target_position+0.002:
			self.position_status_signal.emit("Eco", True)
		else:
			self.position_status_signal.emit("Eco", False)

		return current_position

	def get_current_error_code(self) -> str:
		current_error_code = self.EcoVario.get_last_error()
		if current_error_code is None:
			return "not connected"
		else:
			return str(current_error_code)

	@Slot(float, float, float, float)
	def start(self, position, speed, accell, deaccell) -> None:
		if position >= 2530:
			raise ParameterOutOfRangeError(f"{position} is out of range")
		parameters = {
			"position": position,
			"speed": speed,
			"accell": accell,
			"deaccell": deaccell
		}
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
			self.EcoVario.start()
		except Exception as e:
			QMessageBox.information(
				None,
				"Error",
				f"Could not start Stage!\n{e}"
			)

	@Slot()
	def stop(self) -> None:
		self.EcoVario.stop()

	@Slot()
	def reference_stage(self):
		try:
			self.EcoVario.set_homing()
		except Exception as e:
			QMessageBox.information(
				None,
				"Error",
				f"Could not set reference position!\n{e}"
			)