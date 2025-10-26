import pyvisa, os
from pyvisa import errors
from serial import SerialException
from Devices.Storage import ParameterStorage
from Devices.Descriptors import Parameter
from src.utils import DeviceParameterError

## class for core TGA 1244 functions ##
class FrequencyGenerator:
	waveform = Parameter(
		name="waveform",
		method="set_waveform",
		default={1:"sine", 2:"sine", 3:"sine", 4:"sine"},
		type=dict)
	frequency = Parameter(
		name="frequency",
		method="set_frequency",
		default={1:0.0, 2:0.0, 3:0.0, 4:0.0},
		type=dict)
	amplitude = Parameter(
		name="amplitude",
		method="set_amplitude",
		default={1:0.0, 2:0.0, 3:0.0, 4:0.0},
		type=dict)
	offset = Parameter(
		name="offset",
		method="set_offset",
		default={1:0.0, 2:0.0, 3:0.0, 4:0.0},
		type=dict)
	phase = Parameter(
		name="phase",
		method="set_phase",
		default={1:0.0, 2:0.0, 3:0.0, 4:0.0},
		type=dict)
	inputmode = Parameter(
		name="inputmode",
		method=None,
		default={1: "Amp+Offset", 2: "Amp+Offset", 3: "Amp+Offset", 4: "Amp+Offset"},
		type=dict)
	lockmode = Parameter(
		name="lockmode",
		method="set_lockmode",
		default={1:"indep", 2:"indep", 3:"indep", 4:"indep"},
		type=dict)
	output = Parameter(
		name="output",
		method="set_output",
		default={1:False, 2:False, 3:False, 4:False},
		type=dict)

	def __init__(self, name: str, _storage: ParameterStorage, simulate: bool) -> None:
		# connected variable to check connected status when trying to write data #
		self.name = name
		self.connected = False
		self.simulate = simulate
		self.storage = _storage
		self.current_channel = 1
		# create recource Manager #
		sim_path = os.path.join(
			os.path.dirname(os.path.abspath(__file__)),
			"SimResp.yaml"
		)
		self.rm = pyvisa.ResourceManager(
			f"{sim_path}@sim"
			if self.simulate else ""
		)

		for param in type(self)._get_params():
			self.storage.new_parameter(name, param.name, param.default)


	@classmethod
	def _get_params(cls):
		for attr in vars(cls).values():
			if isinstance(attr, Parameter):
				yield attr

	# Function for opening serial port #
	def open_port(self, port, baudrate) -> None:
		if self.simulate:
			port = "ASRL3::INSTR"
		try:
			self.TGA = self.rm.open_resource(
				resource_name=port,
				open_timeout=2000)
			self.TGA.baudrate = baudrate
			self.TGA.read_termination = "\r"
			self.TGA.write_termination = "\r"
			self.connected = True
		except (errors.VisaIOError, SerialException) as e:
			self.connected = False
			raise ConnectionError(f"{e}")

	# Function for closing serial port #
	def close_port(self) -> None:
		if self.connected:
			self.TGA.close()

	# Function to write data to TGA #
	def _write(self, channel: int, what: str, value: str) -> None:
		if self.simulate:
			print(self.TGA.query(what+value))
			return None
		if self.connected:
			if channel != self.current_channel:
				self.TGA.write_raw(b"SETUPCH"+str(channel).encode()+b"\n")
			return self.TGA.write_raw(what.encode() + b" " + value.encode() + b"\n")
		else:
			return None

	def set_waveform(self, channel: int, waveform: str) -> None:
		waveforms = ["sine", "square", "dc", "triag"]
		if waveform not in waveforms:
			raise DeviceParameterError(f"Wavefrom {waveform} is not supported!")
		return self._write(channel, "WAVE", waveform)

	def set_frequency(self, channel: int, frequency: float) -> None:
		return self._write(channel, "WAVFREQ", str(frequency))

	def set_amplitude(self, channel: int, amplitude: float) -> None:
		mode = self.inputmode[channel]
		if mode == "Amp+Offset":
			return self._write(channel, 'AMPL', str(amplitude))
		else:
			amplitude = self.offset - amplitude
			return self._write(channel, 'AMPL', str(amplitude))

	def set_offset(self, channel: int, offset: float) -> None:
		mode = self.inputmode[channel]
		if mode == "Amp+Offset":
			return self._write(channel, 'DCOFFS', str(offset))
		else:
			offset = (offset+self.amplitude)/2
			return self._write(channel, 'DCOFFS', str(offset))

	def set_phase(self, channel: int, phase: float) -> None:
		return self._write(channel, "PHASE", str(phase))

	def set_lockmode(self, channel: int, lockmode: str) -> None:
		lockmodes = ["indep", "master", "slave", "off"]
		print(lockmode)
		if lockmode not in lockmodes:
			raise ValueError(f"Lockmode {lockmode} is not supported.")
		if lockmode == "indep":
			self._write(channel, 'LOCKMODE', 'INDEP')
			return self._write(channel, 'LOCKSTAT', 'ON')
		elif lockmode == "master":
			self._write(channel, 'LOCKMODE', 'MASTER')
			return self._write(channel, 'LOCKSTAT', 'ON')
		elif lockmode == "slave":
			self._write(channel, 'LOCKMODE', 'SLAVE')
			return self._write(channel, 'LOCKSTAT', 'ON')
		else:
			return self._write(channel, 'LOCKSTAT', 'OFF')

	def set_output(self, channel, output: bool) -> None:
		if output:
			self._write(channel, "ZLOAD", "50")
			return self._write(channel, 'OUTPUT', "ON")
		else:
			return self._write(channel, 'OUTPUT', "OFF")
