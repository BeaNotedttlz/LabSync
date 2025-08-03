'''
Interface of backend OmicronLaser functions and PySide6 frontend
'''
from Devices.Omircon import OmicronLaser
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QMessageBox
from Exceptions import ParameterNotSetError, ParameterOutOfRangeError, DeviceParameterError


class LaserFunctions(QObject):
	port_status_signal = Signal(str, bool)
	emission_status_signal = Signal(str, bool)

	def __init__(self, port: str, _storage, index) -> None:
		super().__init__()

		self.port = port
		self.storage = _storage
		self.index = index
		self.connected = False
		self.LuxX = OmicronLaser(
			name="LuxX"+str(index),
			_storage=self.storage,
			simulate=True
		)

	def __post_init__(self) -> None:
		try:
			self.LuxX.open_port(self.port, baudrate=500000)
			self.connected = True
			self.port_status_signal.emit(f"Laser{self.index}Port", True)
		except ConnectionError:
			self.connected = False
			self.port_status_signal.emit(f"Laser{self.index}Port", False)

	@Slot(bool)
	def manage_port(self, state: bool) -> None:
		if state:
			try:
				self.LuxX.open_port(self.port, baudrate=500000)
				self.connected = True
				self.port_status_signal.emit(f"Laser{self.index}Port", True)
			except ConnectionError as e:
				self.connected = False
				self.port_status_signal.emit(f"Laser{self.index}Port", False)
				QMessageBox.information(
					None,
					"Error",
					"Could not open LuxX Port!\n%s"%e
				)
				return
		else:
			self.LuxX.close_port()
			self.connected = False
			self.port_status_signal.emit(f"Laser{self.index}Port", False)

	@Slot( float, int, bool)
	def apply(self, temp_power, op_mode, emission) -> None:
		if temp_power > 100.0:
			raise ParameterOutOfRangeError("Laser power cant exceed max power!")
		parameters = {
			"temp_power": temp_power,
			"op_mode": op_mode,
			"emission": emission
		}
		for param, value in parameters.items():
			if not hasattr(self.LuxX, param):
				raise DeviceParameterError(f"LuxX: unsupported parameter {param}")
			try:
				if param == "emission":
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

	def manage_emission(self, state: bool)-> None:
		if state and not self.LuxX.emission:
			try:
				self.LuxX.emission = True
				self.emission_status_signal.emit("LuxX", True)
			except ParameterNotSetError as e:
				self.emission_status_signal.emit("LuxX", False)
				QMessageBox.information(
					None,
					"Error",
					f"{e}\n Check error!"
				)
		elif self.LuxX.emission and not state:
			try:
				self.LuxX.emission = False
				self.emission_status_signal.emit("LuxX", False)
			except ParameterNotSetError as e:
				self.emission_status_signal.emit("LuxX", True)
				QMessageBox.information(
					None,
					"Error",
					f"{e}\n Check error!"
				)

	@Slot()
	def reset_error(self) -> None:
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