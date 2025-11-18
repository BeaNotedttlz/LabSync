"""
Module for controlling Omicron LuxX+ laser devices via PyVISA serial communication.
It is planned to include all functionalities described in the LuxX Programmer's Guide,
however this version only implements basic operations to allow control in the LabSync context.
@author: Merlin Schmidt
@date: 2025-16-10
@file: src/backend/devices/omicron.py
@note: Use at your own risk.
"""
# TODO implement the other functions of the lasers

import pyvisa, os, time
from pyvisa import errors
from serial import SerialException
from src.core.utilities import ParameterNotSetError, ParameterOutOfRangeError
from src.backend.connection_status import ConnectionStatus

class OmicronLaser:
	"""
	OmicronLaser class for controlling Omicron LuxX+ laser devices.

	:param name: Name of the laser device.
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
		self.Laser = None
		self.name = name
		self.status = ConnectionStatus.DISCONNECTED
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

	def _ask(self, command: str) -> list:
		"""
		Ask Device and read response. Omicron devices use this convention.
		This could be also named "read".

		:param command: Command string to send to the device.
		:type command: str
		:return: Returns a list object with the response values.
		:rtype: list
		"""
		if self.status == ConnectionStatus.CONNECTED:
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
		if self.status == ConnectionStatus.CONNECTED:
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
		else:
			try:
				# open serial port
				self.Laser = self.rm.open_resource(port)
				# set baudrate, query delay and line termination
				self.Laser.baud_rate = baudrate
				self.Laser.query_delay = 0.1
				self.Laser.read_termination = "\r"
				self.Laser.write_termination = "\r"
				# set connected variable
				self.status = ConnectionStatus.CONNECTED
				# this is only done for first communication and to set for |
				_ = self._ask("GFw|")
				self.max_power = float(self._ask("GMP")[0])
			except (errors.VisaIOError, SerialException) as e:
				self.status = ConnectionStatus.DISCONNECTED
				raise ConnectionError(f"Failed to open EcoVario port: {e}")

	def close_port(self) -> None:
		"""
		Close the serial port of the device.

		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			self.Laser.close()
		return None

	def _setup_device(self) -> None:
		"""
		Setup Device after opening port. This should deactivate the Ad-Hoc mode and check if the power is on.

		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			# Turn on device poer
			response = self._ask("POn")[0]
			if not response == ">":
				# reset controller at error
				self.reset_controller()
			# set operating made to standby without Ad-Hoc mode
			self._set("SOM", "8000")

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
		while time.time() < timeout:
			# wait for response and break loop if successful
			# otherwise break after timeout
			response = self.Laser.read()
			if response.strip() == "!RsC>":
				break
			else:
				time.sleep(0.1)

	def set_power(self, value: float) -> None:
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

	def get_power(self) -> str:
		"""
		Get the current permanent power of the laser.

		:return: The current permanent power level in mW.
		:rtype: str
		"""
		response = self._ask("GLP")[0]
		return response

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

	def get_temp_power(self) -> str:
		"""
		Get the current temporary power of the laser.

		:return: The current temporary power level in %.
		:rtype: str
		"""
		response = self._ask("TTP")[0]
		return response

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