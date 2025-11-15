"""
Module for the FrequencyGenerator functions. This handles most of the logic outside the backend driver.
@autor: Merlin Schmidt
@date: 2025-15-10
@file: Classes/App/TgaFunc.py
@note: use at your own risk.
"""

from PySide6.QtCore import QObject, Slot, Signal
from PySide6.QtWidgets import QMessageBox
from Devices.TGA import FrequencyGenerator
from src.utils import DeviceParameterError

class FrequencyGeneratorFunctions(QObject):
	"""
	FrequencyGeneratorFunctions for handling TGA functions and logic.

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

	def __init__(self, port: str, _storage, _simulate) -> None:
		"""Constructor method
		"""
		super().__init__()

		# save port and storage in self
		# TODO connected variable completely useless?
		self.port = port
		self.storage = _storage
		self.connected = False
		# create OmicronLaser backend driver
		self.TGA1244 = FrequencyGenerator(
			name="TGA",
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
			self.TGA1244.open_port(self.port, baudrate=9600)
			self.connected = True
			# emit port status signal to change indicator
			self.port_status_signal.emit("TGAPort", True)
		except ConnectionError:
			self.connected = False
			# if it fails send close signal
			self.port_status_signal.emit("TGAPort", False)

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
				self.TGA1244.open_port(self.port, baudrate=9600)
				self.connected = True
				self.port_status_signal.emit("TGAPort", True)
			except ConnectionError as e:
				self.connected = False
				self.port_status_signal.emit("TGAPort", False)
				QMessageBox.information(
					None,
					"Error",
					"Could not open TGA Port!\n%s"%e
				)
			return None
		else:
			self.TGA1244.close_port()
			self.connected = False
			self.port_status_signal.emit("TGAPort", False)
			return None

	@Slot(int, str, float, float, float, float, str, str, bool)
	def apply(
			self,
			channel,
			waveform,
			amplitude,
			offset,
			phase,
			frequency,
			inputmode,
			lockmode,
			output
	) -> None:
		"""
		Apply the changed parameters to the TGA1244.

		:param channel: Index of the selected channel
		:type channel: int
		:param waveform: Selected waveform
		:type waveform: str
		:param amplitude: Target amplitude
		:type amplitude: float
		:param offset: Target offset
		:type offset: float
		:param phase: Target phase
		:type phase: float
		:param frequency: Target modulation frequency
		:type frequency: float
		:param inputmode: Selected input mode
		:type inputmode: str
		:param lockmode: Selected lock mode
		:type lockmode: str
		:param output: Output state of the channel
		:type output: bool
		:raises DeviceParameterError: If a unsupported parameter get passed.
				This cannot happen for normal LabSync use.
		:return: None
		:rtype: None
		"""
		parameters = {
			"waveform":	waveform,
			"amplitude": amplitude,
			"offset": offset,
			"phase": phase,
			"frequency": frequency,
			"inputmode": inputmode,
			"lockmode": lockmode,
			"output": output
		}
		# set current channel
		self.TGA1244.current_channel = channel
		# set each provided device parameter
		for param, value in parameters.items():
			if not hasattr(self.TGA1244, param):
				raise DeviceParameterError(f"TGA1244: unsupported parameter {param}")
			try:
				value = (channel, value)
				setattr(self.TGA1244, param, value)
			except Exception as e:
				QMessageBox.information(
					None,
					"Error",
					"TGA ERROR" + str(e)
				)
		return None
	@Slot(int, str, float, float, str, bool, int)
	def apply_on_normal(
			self,
			channel,
			waveform,
			frequency,
			power,
			lockmode,
			output,
			laser_index
	) -> None:
		"""
		This is for the special parameters on the normal LabSync tab.
		This calls the 'apply' method after calculating necessary parameters.

		:param channel: Index of the selected channel
		:type channel: int
		:param waveform: Selected waveform
		:type waveform: str
		:param frequency: Target modulation frequency
		:type frequency: float
		:param power: Target laser power
		:type power: float
		:param lockmode: Selected lock mode
		:type lockmode: str
		:param output: Ouput state of the channel
		:type output: bool
		:param laser_index: Index of the laser
		:type laser_index: int
		:return: None
		:rtype: None
		"""
		# calculate all device parameters out of look up table
		values = self._calc_values(power)
		amplitude = values[0] if laser_index == 1 else values[2]
		offset = values[1] if laser_index == 1 else values[3]

		# call apply method with calculated parameters
		self.apply(channel=channel,
				waveform=waveform,
				amplitude=amplitude,
				offset=offset,
				phase=0.0,
				frequency=frequency,
				inputmode="Amp+Offset",
				lockmode=lockmode,
				output=output
	)
		return None

	@staticmethod
	def _calc_values(power: float) -> list:
		"""
		Look up table for the laser power and sine modulation for each laser power in %.

		:param power: Target laser power
		:type power: float
		:return: The list of amplitude and offset for the laser power
				 [amplitude 1, offset 1, amplitude 2, offset 2]
		:rtype: list
		"""
		table = {
			5: [2.30, 4.45, 1.75, 2.65],
			10: [2.80, 4.00, 2.50, 2.30],
			15: [3.30, 3.80, 2.85, 2.25],
			20: [3.65, 3.70, 2.95, 2.10],
			25: [3.85, 3.60, 3.00, 2.05],
			30: [3.95, 3.55, 3.05, 2.06],
			35: [4.10, 3.50, 3.05, 1.90],
			40: [4.20, 3.40, 3.05, 1.90],
			45: [4.40, 3.35, 3.10, 1.90],
			50: [4.45, 3.30, 3.30, 2.00],
			55: [4.50, 3.30, 3.30, 1.95],
			60: [4.60, 3.25, 3.40, 1.96],
			65: [4.65, 3.20, 3.40, 1.90],
			70: [4.75, 3.20, 3.45, 1.90],
			75: [4.80, 3.15, 3.50, 1.90],
			80: [4.85, 3.15, 3.55, 1.90],
			85: [4.87, 3.15, 3.53, 1.90],
			90: [4.87, 3.15, 3.50, 1.90],
			95: [4.93, 3.12, 3.40, 1.82],
			100: [4.97, 3.09, 3.56, 1.90]
		}
		return table[power]
