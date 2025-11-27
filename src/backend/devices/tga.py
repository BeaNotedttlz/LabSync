"""
Module for controlling the TTi instruments TGA1244 Frequency Generator via PyVISA serial communication.
This focuses on the RS232 serial interface of the device. However the GPIO should also work with minor modifications.
@autor: Merlin Schmidt
@date: 2025-16-10
@file: src/backend/devices/tga.py
@note: Use at your own risk.
"""
# TODO this needs a rework without the attributes

import pyvisa, os
from pyvisa import errors
from serial import SerialException
from src.core.context import DeviceConnectionError, DeviceRequestError
from src.backend.connection_status import ConnectionStatus

class FrequencyGenerator:
	"""
	FrequencyGenerator class for controlling TTi TGA1244 Frequency Generator devices.

	:param name: Name of the frequency generator device.
	:type name: str
	:param simulate: Flag to indicate if simulation mode is enabled.
	:type simulate: bool
	:return: None
	:rtype: None
	"""
	def __init__(self, name: str, simulate: bool) -> None:
		"""Constructor method
		"""
		# save variables to self and create connected variable
		self.name = name
		self.status = ConnectionStatus.DISCONNECTED
		self.simulate = simulate
		self.current_channel = 1
		self.TGA = None
		# create simulate path
		sim_path = os.path.join(
			os.path.dirname(os.path.abspath(__file__)),
			"simulation.yaml"
		)
		# create resource manager
		self.rm = pyvisa.ResourceManager(
			f"{sim_path}@sim"
			if self.simulate else ""
		)

	def open_port(self, port: str, baudrate: int) -> None:
		"""
		Open serial communication port with the TTi device.

		:param port: Serial port address
		:type port: str
		:param baudrate: Baudrate for serial communication
		:type baudrate: int
		:raises ConnectionError: If the port could not be opened
		:return: None
		:rtype: None
		"""
		# set port for simulation
		if self.simulate:
			port = "ASRL3::INSTR"
		try:
			# open serial port
			self.TGA = self.rm.open_resource(
				resource_name=port,
				open_timeout=2000)
			# set baudrate and line termination
			self.TGA.baudrate = baudrate
			self.TGA.read_termination = "\r"
			self.TGA.write_termination = "\r"
			# set connected variable
			self.status = ConnectionStatus.CONNECTED
			self.current_channel = 1
		except (errors.VisaIOError, SerialException) as e:
			self.status = ConnectionStatus.DISCONNECTED
			raise DeviceConnectionError(device_id=self.name, original_error=e) from e

	def close_port(self) -> None:
		"""
		Close the serial port of the device.

		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			# only close port if connected
			self.TGA.close()
		return None

	def _write(self, channel: int, what: str, value: str) -> None:
		"""
		Write Data to the device. This is used to set parameters for each channel.
		This could also be named "write".


		:param channel: Index of the selected channel
		:type channel: int
		:param what: What parameter to change
		:type what: str
		:param value: The new value
		:type value: str
		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				# dont encode message for simulation
				print(self.TGA.query(what + value))
				return None
			else:
				# write selected channel if different to lastly selected channel
				if channel != self.current_channel:
					self.TGA.write_raw(b"SETUPCH" + str(channel).encode() + b"\n")
				# write parameter and value to device
				# The TGA1244 does not yield any response
				return self.TGA.write_raw(what.encode() + b" " + value.encode() + b"\n")
		else:
			return None

	def set_waveform(self, channel: int, waveform: str) -> None:
		"""
		Set the waveform of the channel.
		The currently available waveforms are:
		- Sine (sine)
		- Square (square)
		- DC (dc)
		- Triangular (triag)

		:param channel: Index of the selected channel
		:type channel: int
		:param waveform: Desired waveform
		:type waveform: str
		:raises DeviceParameterError: If the desired waveform is not supported
										(not possible with normal LabSync usage)
		:return: None
		:rtype: None
		"""
		waveforms = ["sine", "square", "dc", "triag"]
		if waveform not in waveforms:
			# raise error if the waveform is not supported
			raise DeviceRequestError(f"Wavefrom {waveform} is not supported!")
		return self._write(channel, "WAVE", waveform)

	def set_frequency(self, channel: int, frequency: float) -> None:
		"""
		Set the modulation frequency of the selected channel in Hz.

		:param channel: Index of the selected channel
		:type channel: int
		:param frequency: Desired modulation frequency
		:type frequency: float
		:return: None
		:rtype: None
		"""
		return self._write(channel, "WAVFREQ", str(frequency))

	def set_amplitude(self, channel: int, amplitude: float) -> None:
		"""
		Set the amplitude of the selected channel in V.
		This supports two input modes, but ultimately only uses one.
		For Amp+Offset operation: No change
		For Low+High operation: amplitude = high - low

		:param channel: Index of the selected channel
		:type channel: int
		:param amplitude: Desired amplitude
		:type amplitude: float
		:return: None
		:rtype: None
		"""
		# get current input mode
		return self._write(channel, 'AMPL', str(amplitude))

	def set_offset(self, channel: int, offset: float) -> None:
		"""
		Set the offset of the selected channel in V.
		This supports two input modes, but ultimately only uses one.
		For Amp+Offset operation: No change
		For Low+High: Offset = (high + low) / 2

		:param channel: Index of the selected channel
		:type channel: int
		:param offset: Desired offset
		:type offset: float
		:return: None
		:rtype: None
		"""
		return self._write(channel, 'DCOFFS', str(offset))

	def set_phase(self, channel: int, phase: float) -> None:
		"""
		Set the phase of the selected channel in °.

		:param channel: Index of selected channel
		:type channel: int
		:param phase: Desired phase
		:type phase: float
		:return: None
		:rtype: None
		"""
		return self._write(channel, "PHASE", str(phase))

	def set_lockmode(self, channel: int, lockmode: str) -> None:
		"""
		Set the lock mode operation of the selected channel.
		This supports the lock modes:
		- off
		- indep
		- maser
		- slave

		:param channel: Index of selected channel
		:type channel: int
		:param lockmode: Desried lockmode
		:type lockmode: str
		:raises ValueError: If the lock mode is not supported
		:return: None
		:rtype: None
		"""
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
		"""
		Set the output of the selected channel.

		:param channel: Index of the selected channel
		:type channel: int
		:param output: Desired output state
		:type output: bool
		:return: None
		:rtype: None
		"""
		if output:
			# write 50 Ohms output impedance if the output is turned on
			# this is donw to always ensure the correct impedance matching
			self._write(channel, "ZLOAD", "50")
			return self._write(channel, 'OUTPUT', "ON")
		else:
			return self._write(channel, 'OUTPUT', "OFF")