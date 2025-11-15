"""
Module for controlling Omicron LuxX+ laser devices via PyVISA serial communication.
It is planned to include all functionalities described in the LuxX Programmer's Guide,
however this version only implements basic operations to allow control in the LabSync context.
@autor: Merlin Schmidt
@date: 2024-06-10
@file: Devices/Omircon.py
@note: Use at your own risk.
"""

import pyvisa, os, time
from pyvisa import errors
from serial import SerialException
from Devices.Storage import ParameterStorage
from Devices.Descriptors import Parameter
from src.utils import ParameterNotSetError, ParameterOutOfRangeError


class OmicronLaser:
	"""
	OmicronLaser class for controlling Omicron LuxX+ laser devices.

	:param name: Name of the laser device.
	:type name: str
	:param _storage: ParameterStorage instance for storing device parameters.
	:type _storage: ParameterStorage
	:param simulate: Flag to indicate if simulation mode is enabled.
	:type simulate: bool
	:return: None
	:rtype: None
	"""
	# Device parameter attributes
	firmware = Parameter("firmware", None, ["ND", "ND", "ND"], list)
	specs = Parameter("specs", None, ["ND", "ND"], list)
	max_power = Parameter("max_power", None, 1, int)
	op_mode = Parameter("op_mode", "set_op_mode", 0, int)
	temp_power = Parameter("temp_power", "set_temp_power", 0.0, float)
	power = Parameter("power", "set_power", 0.0, float)
	emission = Parameter("emission", "set_emission", False, bool)
	error_code = Parameter("error_code", "", "0x00", str)

	def __init__(self, name: str, _storage: ParameterStorage, simulate: bool) -> None:
		"""Constructor method
		"""
		# save variables to self and create connected variable
		self.Laser = None
		self.storage = _storage
		self.name = name
		self.connected = False
		self.simulate = simulate
		# create simulate path
		sim_path = os.path.join(
			os.path.dirname(os.path.abspath(__file__)),
			"SimResp.yaml"
		)
		# create resource manager
		self.rm = pyvisa.ResourceManager(
			f"{sim_path}@sim"
			if self.simulate else ""
		)

		# Save attributes to storage
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

	def _ask(self, command: str) -> list:
		"""
		Ask Device and read response. Omicron devices use this convention.
		This could be also named "read".

		:param command: Command string to send to the device.
		:type command: str
		:return: Returns a list object with the response values.
		:rtype: list
		"""
		if self.connected:
			# only read if connected
			response = self.Laser.query("?" + command)
			# split response by '|' and remove first 4 characters
			return response[4:].split("|")
		# otherwise return empty list
		return [""]

	def _set(self, what: str, value: str) -> str:
		"""
		Write value to Device and get response. Omicron devices use this convention.
		This could be also named "write". The response only indicates success or failure.

		:param what: What command to send to the device. This could be seen as the parameter name.
		:type what: str
		:param value: The value of the parameter to set to.
		:type value: str
		:return: Returns either ">" for success or "x" for failure (or "" if the device is not connected).
		:rtype: str
		"""
		if self.connected:
			# send command to device if connected
			response = self.Laser.query("?" + what + value)
			# return response without first 4 characters
			return response[4:]
		# oterhwise return empty string
		return ""

	def open_port(self, port: str, baudrate: int) -> None:
		"""
		Open serial port for communication with the Omicron laser device.

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
			port = "ASRL1::INSTR"
		try:
			# open serial port
			self.Laser = self.rm.open_resource(port)
			# set baudrate, query delay, and line termination
			self.Laser.baud_rate = 500000
			self.Laser.query_delay = 0.1
			self.Laser.read_termination = "\r"
			self.Laser.write_termination = "\r"
			# set connected variable
			self.connected = True

			# get laser information
			# TODO: this could be improved to ask with own method
			self.firmware = self._ask("GFw|")
			self.specs = self._ask("GSI")
			self.max_power = int(self._ask("GMP")[0])

			# set up device after opening port
			self._setup_device()
		except (errors.VisaIOError, SerialException) as e:
			self.connected = False
			raise ConnectionError(f"{e}")

	# TODO this could break!!!
	def _setup_device(self) -> None:
		"""
		Setup Device after opening port. This should deactivate the Ad-Hoc mode and check if the power is on.

		:return: None
		:rtype: None
		"""
		if self.connected:
			# Turn on Power of device
			resp = self._ask("POn")[0]
			if not resp:
				# Dont know if this even works
				self.reset_controller()
			# Set Operating mode to Standby and disable Ad-Hoc mode
			self._set("SOM", "8000")

	def close_port(self) -> None:
		"""
		Close the serial port of the device.

		:return: None
		:rtype: None
		"""
		if self.connected:
			# close the port if connected
			self.Laser.close()
		return None

	def set_op_mode(self, value) -> None:
		"""
		Set the operation mode of the Laser. This only accepts integer values from 0 to 5.
		The full operating mode control can be done with the '' method.

		0 - Standby, no emission
        1 - CW ACC
        2 - CW APC
        3 - Analog modulation, with ACC only
        4 - Digital modulation, with ACC only
        5 - Analog and Digital modulation, with ACC only

		:param value: Index of the operating mode to set.
		:type value: int
		:raises: ParameterNotSetError: If the operating mode could not be set.
		:return: None
		:rtype: None
		"""
		# set the operating mode and wait for response
		response = self._set("ROM", str(value))
		if response != ">":
			# raise error if not successful
			raise ParameterNotSetError("Operating mode could not be set")
		else:
			return None

	def set_power(self, value) -> None:
		"""
		Set the permanent power of the laser. This value will persist after reboot or reset of the laser.
		However, it is recommended to use temporary power settings for most operations to avoid wearing out the memory.

		:param value: The desired permanent power level.
		:type value: float
		:raises ParameterNotSetError: If the power could not be set.
		:return: None
		:rtype: None
		"""
		# set the power and wait for response
		response = self._set("SLP", str(value))
		if response != ">":
			# raise error if not successful
			raise ParameterNotSetError("Power could not be set")
		else:
			return None

	def set_temp_power(self, value) -> None:
		"""
		Set the temoporary power of the laser.
		This value will be lost after reboot or reset of the laser.

		:param value: The desired temporary power level (0.0 - 100.0).
		:raises ParameterNotSetError: If the power could not be set.
		:raises ParameterOutOfRangeError: If the power value is out of range.
		:return: None
		:rtype: None
		"""
		if value > 100.0:
			# raise error if value is out of range
			raise ParameterOutOfRangeError(f"Temporary power {value} is out of range (0.0 - 100.0)")
		# set the temporary power and wait for response
		response = self._set("TPP", str(value))
		if response != ">":
			# raise error if not successful
			raise ParameterNotSetError("Temporary power could not be set")
		else:
			return None

	def get_op_mode(self) -> str:
		"""
		Get the current operating mode of the device.
		This will return the index mode as can be set with the 'set_op_mode' method.
		For the full operating mode byte use the '' method.

		:return: The index of the current operating mode.
		:rtype: str
		"""
		response = self._ask("ROM")[0]
		return response

	def get_power(self) -> str:
		"""
		Get the current permanent power of the laser.

		:return: The current permanent power level in mW.
		:rtype: str
		"""
		response = self._ask("GLP")[0]
		return response

	def get_temp_power(self) -> str:
		"""
		Get the current temporary power of the laser.

		:return: The current temporary power level in %.
		:rtype: str
		"""
		response = self._ask("TTP")[0]
		return response

	def set_emission(self, value: bool) -> None:
		"""
		Set the emission state of the laser. The state can only be set to on (True) or off (False).

		:param value: The desired emission state of the laser.
		:type value: bool
		:raises ParameterNotSetError: If the emission could not be set to the value,
		:return: None
		:rtype: None
		"""
		if value:
			# set emission to on if True
			response = self._ask("LOn")[0]
			if response != ">":
				raise ParameterNotSetError("Emission could not be set")
			else:
				return None
		# set emission to off if False
		else:
			response = self._ask("LOf")[0]
			if response != ">":
				raise ParameterNotSetError("Emission could not be set")
			else:
				return None

	def get_error_byte(self) -> str:
		"""
		Get the current error byte of the laser.

		:return: The error byte in binary format.
		:rtype: str
		"""
		response = self._ask("GLF")[0]
		return bin(int(response, 16))

	def reset_controller(self) -> None:
		"""
		Reset the controller. This will reboot the laser device.
		While the device is rebooting, it will not respond to any commands.

		:return: None
		:rtype: None
		"""
		# set a timeout for waiting for response
		timeout = time.time() + 10
		# reset controller
		self.Laser.write("?RsC")
		while True:
			# wait for response and break loop if successful
			# otherwise break after timeout
			response = self.Laser.read()
			if response.strip() == "!RsC>":
				break
			if time.time() > timeout:
				raise TimeoutError("Timeout while waiting for !RsC response")
			time.sleep(0.1)
