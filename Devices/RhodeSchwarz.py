from RsInstrument.RsInstrument import RsInstrument
from Devices.Descriptors import Parameter
from Devices.Storage import ParameterStorage


class SpectrumAnalyzer:
	center_frequency = Parameter("center_frequency", "set_enter_frequency", 1e3, float)
	span = Parameter("span", "set_span", 1e3, float)
	sweep_type = Parameter("sweep_type", "set_sweep_type", "SWE", str)
	bandwidth = Parameter("bandwidth", "set_bandwidth", 100, float)
	unit = Parameter("unit", "set_unit", "DBM", str)
	sweep_points = Parameter("sweep_points", "set_sweep_points", 2001, int)
	avg_count = Parameter("avg_count", "set_avg_count", 64, int)

	def __init__(self, name: str, _storage: ParameterStorage, simulate: bool) -> None:
		self.FSV3000 = None
		self.storage = _storage
		self.name = name
		self.connected = False
		self.simulate = simulate

		for param in type(self)._get_params():
			_storage.new_parameter(name, param.name, param.default)

	@classmethod
	def _get_params(cls):
		for attr in vars(cls).values():
			if isinstance(attr, Parameter):
				yield attr

	def open_port(self, ip: str):
		if self.simulate:
			return print("Port opened (simulation)")
		try:
			self.FSV3000 = RsInstrument(ip, True, True, "SelectVisa='rs'")
			self.FSV3000.visa_timeout = 5000
			self.FSV3000.instrument_status_checking = True
			self.FSV3000.clear_status()
			self.FSV3000.opc_timeout = 10000
			self.connected = True
		except Exception as e:
			self.connected = False
			raise ConnectionError(e)

	def _com_check(self) -> str:
		if self.connected:
			idn_response = self.FSV3000.query_str('*IDN?')
			return idn_response
		return "not connected"

	def close_port(self) -> None:
		if self.simulate:
			return print("Port closed (simulation)")
		if self.connected:
			self.FSV3000.close()
			self.connected = False

	def set_enter_frequency(self, value: float):
		if self.simulate:
			print("set enter frequency to", value)
		if self.connected:
			self.FSV3000.write_str_with_opc('FREQuency:CENTer ' + str(value))
		else:
			pass

	def set_span(self, value: float):
		if self.simulate:
			print("set span to", value)
		if self.connected:
			self.FSV3000.write_str_with_opc('FREQuency:SPAN ' + str(value))
		else:
			pass

	def set_bandwidth(self, value: int):
		if self.simulate:
			print("set bandwidth to", value)
		if self.connected:
			self.FSV3000.write_str_with_opc('SENSe:BANDwidth ' + str(value))
		else:
			pass

	def set_sweep_type(self, value: str):
		if self.simulate:
			print("set sweep type to", value)
		if self.connected:
			self.FSV3000.write_str_with_opc('SENSe:SWEep:TYPE ' + value)
		else:
			pass

	def set_unit(self, value: str):
		if self.simulate:
			print("set unit to", value)
		if self.connected:
			self.FSV3000.write_str_with_opc('UNIT:POW ' + value)
		else:
			pass

	def set_sweep_points(self, value: int):
		if self.simulate:
			print("set sweep points to", value)
		if self.connected:
			self.FSV3000.write_str_with_opc('WEep:POINts ' + str(value))
		else:
			pass

	def set_avg_count(self, value: int):
		if self.simulate:
			print("set average count to", value)
		if self.connected:
			self.FSV3000.write_str_with_opc('SENSe:AVERage:COUNt ' + str(value))
		else:
			pass

	def start_single_measurement(self) -> tuple:
		if self.simulate:
			print("start single measurement")
		if self.connected:
			self.FSV3000.write_str_with_opc('ABORt')
			self.FSV3000.write_str_with_opc('FORMat ASCii')
			self.FSV3000.write_str_with_opc('INITiate:CONTinuous OFF')

			self.FSV3000.write_str_with_opc('DISPlay:TRACe1:MODE WRITe')
			self.FSV3000.write_str_with_opc('SENSe:SWEep:TYPE ' + str(self.sweep_type))
			self.FSV3000.write_str_with_opc('INITiate:IMMediate; *WAI')
			trace_data = self.FSV3000.query_str('Trace:DATA? TRACe1')
			trace_points = self.FSV3000.query_str('Trace:DATA:X? TRACe1')
			nr_sweep_points = self.FSV3000.query_str('SWEep:POINts?')

			return trace_data, trace_points, nr_sweep_points
		else:
			return None, None, None

	def start_avg_measurement(self) -> tuple:
		if self.simulate:
			print("start average measurement")
		if self.connected:
			self.FSV3000.write_str_with_opc('ABORt')
			self.FSV3000.write_str_with_opc('FORMat ASCii')
			self.FSV3000.write_str_with_opc('INITiate:CONTinuous OFF')

			self.FSV3000.write_str_with_opc('SENSe:SWEep:TYPE ' + str(self.sweep_type))
			self.FSV3000.write_str_with_opc('DISPlay:TRACe1:MODE AVERage')
			self.FSV.write_str_with_opc('SWEep:COUNt ' + str(self.avg_count))
			self.FSV3000.write_str_with_opc('INITiate:IMMediate; *WAI')
			trace_data = self.FSV3000.query_str('Trace:DATA? TRACe1')
			trace_points = self.FSV3000.query_str('Trace:DATA:X? TRACe1')
			nr_sweep_points = self.FSV3000.query_str('SWEep:POINts?')

			return trace_data, trace_points, nr_sweep_points
		else:
			return None, None, None
