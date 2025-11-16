"""
Module for controlling the Rohde & Schwarz FSV3000 Spectrum analyzer via TCP.
For this the already provided RsInstrument communication framework by R&S is used.
@autor: Merlin Schmidt
@date: 2025-16-10
@file: src/backend/devices/fsv.py
@note: Use at your own risk.
"""

from RsInstrument import RsInstrument
from src.core.storage import Parameter, ParameterStorage
from src.backend.connection_status import ConnectionStatus

class SpectrumAnalyzer:
	"""
	SpectrumAnalyzer class for controlling R&S FSV devices.

	:param name: Name of the frequency generator device.
	:type name: str
	:param _storage: ParameterStorage instance for storing device parameters.
	:type _storage: ParameterStorage
	:param simulate: Flag to indicate if simulation mode is enabled.
	:type simulate: bool
	:return: None
	:rtype: None
	"""
	# Device parameter attributes
	center_frequency = Parameter("center_frequency", "set_enter_frequency", 1e3, float)
	span = Parameter("span", "set_span", 1e3, float)
	sweep_type = Parameter("sweep_type", "set_sweep_type", "SWE", str)
	bandwidth = Parameter("bandwidth", "set_bandwidth", 100, float)
	unit = Parameter("unit", "set_unit", "DBM", str)
	sweep_points = Parameter("sweep_points", "set_sweep_points", 2001, int)
	avg_count = Parameter("avg_count", "set_avg_count", 64, int)

	def __init__(self, name: str, _storage: ParameterStorage, _simulate: bool) -> None:
		"""Constructor method
		"""
		# save variables to self and create connected variable
		self.FSV3000 = None
		self.storage = _storage
		self.name = name
		self.status = ConnectionStatus.DISCONNECTED
		self.simulate = _simulate
		# save attributes to storage
		for param in type(self)._get_params():
			_storage.new_parameter(name, param.name, param.default)

	@classmethod
	def _get_params(cls):
		"""
		Get all Parameter attributes of the class.

		:param cls: Class reference.
		:return: attributes of type Parameter.
		:rtype: generator
		"""
		for attr in vars(cls).values():
			if isinstance(attr, Parameter):
				yield attr

	def open_port(self, ip: str) -> None:
		"""
		Open serial communication port with the R&S device.

		:param ip: TCP ip of device
		:type ip: str
		:raises ConnectionError: If the port could not be opened
		:return: None
		:rtype: None
		"""
		# set port for simulation
		if self.simulate:
			return print("Port opened (simulation)")
		try:
			# open serial port
			self.FSV3000 = RsInstrument(ip, True, True, "SelectVisa='rs'")
			# set timeout and checking
			self.FSV3000.visa_timeout = 5000
			self.FSV3000.instrument_status_checking = True
			self.FSV3000.clear_status()
			self.FSV3000.opc_timeout = 10000
			# set connected variable
			self.status = ConnectionStatus.CONNECTED
		except Exception as e:
			self.status = ConnectionStatus.DISCONNECTED
			raise ConnectionError(f"{e}")

	def _com_check(self) -> str:
		"""
		Check communication with the FSV3000

		:return: Either the ID of the device or not connected
		:rtype: str
		"""
		if self.status == ConnectionStatus.CONNECTED:
			idn_response = self.FSV3000.query_str('*IDN?')
			return idn_response
		return "not connected"

	def close_port(self) -> None:
		"""
		Close the serial port of the device

		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				return print("Port closed (simulation)")
			else:
				self.FSV3000.close()
				self.status = ConnectionStatus.DISCONNECTED
		else:
			return None

	def set_enter_frequency(self, value: float) -> None:
		"""
		Set the center frequency of the current window

		:param value: The value of the desired center frequency in Hz
		:type value: float
		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(f"set center frequency to {value}")
				return None
			else:
				# write frequency if connected
				self.FSV3000.write_str_with_opc('FREQuency:CENTer ' + str(value))
				return None
		else:
			return None

	def set_span(self, value: float) -> None:
		"""
		Set the frequency span of the current window

		:param value: The value of the desired frequency span in Hz
		:type value: float
		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(f"set span to {value}")
				return None
			else:
				# write frequency if connected
				self.FSV3000.write_str_with_opc('FREQuency:SPAN ' + str(value))
				return None
		else:
			return None

	def set_bandwidth(self, value: int) -> None:
		"""
		Set the frequency sweep bandwidth of the current window

		:param value: The value of the bandwidth in Hz
		:type value: int
		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(f"set bandwidth to {value}")
				return None
			else:
				# write frequency if connected
				self.FSV3000.write_str_with_opc('SENSe:BANDwidth ' + str(value))
				return None
		else:
			return None

	def set_sweep_type(self, value: str) -> None:
		"""
		Set the sweep type. Possible types:
		- SWE (Sweep)
		- FFT (FFT)

		:param value: Desired sweep type
		:type value: str
		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(f"set sweep type to {value}")
				return None
			else:
				self.FSV3000.write_str_with_opc('SENSe:SWEep:TYPE ' + str(value))
				return None
		else:
			return None

	def set_unit(self, value: str) -> None:
		"""
		Set the Signal axis unit of the current window. Possible values:
		- V (Volt, usually mV)
		- DBMW (dBmW) ? I think so
		- DBMV (dBmV)

		:param value: Desired axis unit
		:type value: str
		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(f"set unit to {value}")
				return None
			else:
				self.FSV3000.write_str_with_opc('UNIT:POW ' + str(value))
		return None

	def set_sweep_points(self, value: int) -> None:
		"""
		Set the amount of sweep points for data saving.

		:param value: Amount of sweep points
		:type value: int
		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(f"set sweep points to {value}")
				return None
			else:
				# set sweep points if connected
				self.FSV3000.write_str_with_opc('WEep:POINts ' + str(value))
				return None
		else:
			return None

	def set_avg_count(self, value: int) -> None:
		"""
		Set the average count. This only applies if the average sweep type is selected.
		This selection is currently not available. This value only applies when running the 'start_avg_measurement' method.

		:param value: Desired average count
		:type value: int
		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(f"set average count to {value}")
				return None
			else:
				# set average count if connected
				self.FSV3000.write_str_with_opc('SENSe:AVERage:COUNt ' + str(value))
				return None
		else:
			return None

	def start_single_measurement(self) -> tuple:
		"""
		Starts a single frequency sweep and collects the spectrum data.

		:return: A tuple of (trace_data (selected unit), trace_points (Hz), nr_sweep_points).
				 The number of sweep points can be used for saving or otherwise iterating through the data.
		:rtype: tuple
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(f"start single measurement")
				return None, None, None
			else:
				# abort any running measurement
				self.FSV3000.write_str_with_opc('ABORt')
				# set the data format to ASCII
				self.FSV3000.write_str_with_opc('FORMat ASCii')
				# only run a single sweep
				self.FSV3000.write_str_with_opc('INITiate:CONTinuous OFF')

				# set mode to single run mode
				self.FSV3000.write_str_with_opc('DISPlay:TRACe1:MODE WRITe')
				# set sweep type
				self.FSV3000.write_str_with_opc('SENSe:SWEep:TYPE ' + str(self.sweep_type))
				# start frequency sweep and wait for finish
				self.FSV3000.write_str_with_opc('INITiate:IMMediate; *WAI')
				# retrieve data
				trace_data = self.FSV3000.query_str('Trace:DATA? TRACe1')
				trace_points = self.FSV3000.query_str('Trace:DATA:X? TRACe1')
				nr_sweep_points = self.FSV3000.query_str('SWEep:POINts?')

				return trace_data, trace_points, nr_sweep_points
		else:
			return None, None, None

	def start_avg_measurement(self) -> tuple:
		"""
		Starts a averaging frequency sweep for [average count] frequency sweeps and collects the spectrum data.

		:return: A tuple of (trace_data (selected unit), trace_points (Hz), nr_sweep_points).
				 The number of sweep points can be used for saving or otherwise iterating through the data.
		:rtype: tuple
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(f"start average measurement")
				return None, None, None
			else:
				# abort any running measurement
				self.FSV3000.write_str_with_opc('ABORt')
				# set the data format to ASCII
				self.FSV3000.write_str_with_opc('FORMat ASCii')
				# only run a single sweep
				self.FSV3000.write_str_with_opc('INITiate:CONTinuous OFF')

				# set the mode to average
				self.FSV3000.write_str_with_opc('DISPlay:TRACe1:MODE AVERage')
				# set the sweep type
				self.FSV3000.write_str_with_opc('SENSe:SWEep:TYPE ' + str(self.sweep_type))
				# set the [average count]
				self.FSV3000.write_str_with_opc('SWEep:COUNt ' + str(self.avg_count))
				# start frequency sweep and wait for finish
				self.FSV3000.write_str_with_opc('INITiate:IMMediate; *WAI')
				# retreive data
				trace_data = self.FSV3000.query_str('Trace:DATA? TRACe1')
				trace_points = self.FSV3000.query_str('Trace:DATA:X? TRACe1')
				nr_sweep_points = self.FSV3000.query_str('SWEep:POINts?')

				return trace_data, trace_points, nr_sweep_points
		else:
			return None, None, None