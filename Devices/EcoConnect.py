"""
Module for controlling EcoVario linear stages via EcoVario-Controller over serial communication.
In contrast to the official EcoConnect library, this implementation uses PyVISA for communication,
allowing for communication without Python 32-bit and enabling usage for Unix based operating systems.
@autor: Merlin Schmidt
@date: 2024-06-10
@file: Devices/EcoConnect.py
@note: Use at your own risk.
"""

import pyvisa, os
from pyvisa import errors
from serial import SerialException
from Devices.Descriptors import Parameter
from Devices.Storage import ParameterStorage

class EcoConnect:
	"""
	EcoConnect class for serial communication with EcoVario linear stage. Using PyVISA for communication protocols.

	:param name: Name of the device instance.
	:type name: str
	:param _storage: ParameterStorage instance for storing device parameters.
	:type _storage: ParameterStorage
	:param simulate: Flag to indicate simulation mode.
	:type simulate: bool
	:return None
	:rtype: None
	"""
	# Device parameter attributes
	position = Parameter("position", "set_position", 0.0, float)
	speed = Parameter("speed", "set_speed", 35.0, float)
	accell = Parameter("accel", "set_accel", 501.30, float)
	deaccell = Parameter("deccel", "set_deaccel", 501.30, float)

	def __init__(self, name: str, _storage: ParameterStorage, simulate: bool) -> None:
		"""Constructor method
		"""
		# save variables to self and create connected variable
		self.storage = _storage
		self.name = name
		self.connected = False
		self.simulate = simulate
		# create simulate path
		sim_path = os.path.join(
			os.path.dirname(os.path.abspath(__file__)),
			"SimResp.yaml"
		)
		# create Resource Manager
		self.rm = pyvisa.ResourceManager(
			f"{sim_path}@sim"
			if self.simulate else ""
		)

		# add attr to storage
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

	def open_port(self, port: str, baudrate: int) -> None:
		"""
		Open serial port for communication with EcoVario controller.

		:param port: Serial port address
		:type port: str
		:param baudrate: Baudrate for serial communication
		:type baudrate: int
		:raises ConnectionError: Ff port cannot be opened
		:return: None
		:rtype: None
		"""
		# set port for simulation
		if self.simulate:
			port = "ASRL4::INSTR"
		try:
			# open serial port
			self.eco = self.rm.open_resource(port, open_timeout=2000)
			# set baudrate and line termination
			self.eco.baudrate = baudrate
			self.eco.read_termination = "\r"
			self.eco.write_termination = "\r"
			# set connected variable
			self.connected = True
		except (errors.VisaIOError, SerialException) as e:
			# catch any serial error and set connected to false
			self.connected = False
			raise ConnectionError(f"{e}")

	# Function for closing serial port #
	def close_port(self) -> None:
		"""
		Close serial port for EcoVario controller.

		:return: None
		:rtype: None
		"""
		if self.connected:
			# only try to close port if connected
			self.eco.close()
		return None

	@staticmethod
	def _calculate_checksum(message) -> int:
		"""
		Private method to calculate checksum for EcoVario communication protocol.

		:param message: Message to calculate checksum for
		:type message: str
		:return: Returns checksum byte
		:rtype: int
		"""

		sum_bytes = sum(message)
		lsb = sum_bytes & 0xFF
		checksum = (~lsb + 1) & 0xFF
		return checksum

	@staticmethod
	def _invert_hex(hex_string: str) -> str:
		"""
		Private method to invert byte order of hex string.

		:param hex_string: Hex number to invert
		:type hex_string: str
		:return: inverted hex string
		:rtype: str
		"""
		bytes_list = [hex_string[i:i+2] for i in range(0, len(hex_string), 2)]
		inverse_bytes_list = bytes_list[::-1]
		inverse_hex = "".join(inverse_bytes_list)
		return inverse_hex

	def _read_sdo(self, id: int, object: int) -> str | None:
		"""
		Private method to read SDO communication from EvoVario controller.
		This method sends a read request and waits for the appropriate response.

		:param id: Id of the SDO
		:type id: int
		:param object: Object to read
		:type object: int
		:return: Returns either None for no Response or the hex response string
		:rtype: str | None
		"""

		if self.connected:
			# calculate message bytes
			object_1 = object >> 8
			object_2 = object & 0xFF
			message = [id, 0x40, object_2, object_1, 0x00, 0x00, 0x00, 0x00, 0x00]
			# get trailing checksum byte
			trailing_byte = self._calculate_checksum(message)
			message.append(trailing_byte)

			# write message and listen for response
			self.eco.write_raw(message)

			# Read bytes and remove header and checksum
			# [20:] is necessary to remove the request that is returned by the device
			response = self.eco.read_bytes(20).hex()[20:][10:-2]

			# Invert the byte order of the response
			response_hex = self._invert_hex(response)
			return response_hex
		else:
			# Return None if not connected
			return None

	def _write_sdo(self, id: int, object: int, value: int) -> None:
		"""
		Prive method to write SDO communication to EcoVario controller.
		This method sends a write request and waits for the appropriate response.

		:param id: Id of the SDO
		:type id: int
		:param object: Object to write
		:tyoe object: int
		:param value: Value to write to device
		:type value: int
		:return: None
		:rtype: None
		"""
		if self.connected:
			# calculate message bytes
			object_1 = object >> 8
			object_2 = object & 0xFF
			hex_value = value.to_bytes(4, byteorder='little')
			value_list = list(hex_value)

			# generate message
			message = [id, 0x22, object_2, object_1, 0x00, value_list[0], value_list[1], value_list[2], value_list[3]]
			# calculate and append checksum
			trailing_byte = self._calculate_checksum(message)
			message.append(trailing_byte)

			# write message and read response
			self.eco.write_raw(message)
			_ = self.eco.read_bytes(20)
			# response is not used currently -> can be used to check for errors
		else:
			return None

	def set_position(self, position: float) -> None:
		"""
		Set target position of EcoVario stage.
		This method converts the position from mm to the encoder units used by the controller.
		Currently only positive positions are supported.

		:param position: Set position in mm
		:type position: float
		:return: None
		:rtype: None
		"""
		if self.simulate:
			# only print command and response in simulation mode
			print(self.eco.query(f"pos{position}"))
			return None
		else:
			# convert position from mm to encoder units
			encoder_position = position / 0.001253258
			encoder_position_int = round(encoder_position)
			# write position to stage and ignore return
			return self._write_sdo(0x01, 0x607A, encoder_position_int)

	def set_speed(self, speed: float) -> None:
		"""
		Set target speed of EcoVario stage.
		This method converts the speed from mm/s to the encoder units used by the controller.

		:param speed: Set speed in mm/s
		:type speed: float
		:return: None
		:rtype: None
		"""
		if self.simulate:
			# only print command and response in simulation mode
			print(self.eco.query(f"speed{speed}"))
			return None
		else:
			# convert speed from mm/s to encoder units
			encoder_speed = speed / 0.000019585
			encoder_speed_int = round(encoder_speed)
			# write speed to stage and ignore return
			return self._write_sdo(0x01, 0x6081, encoder_speed_int)

	def set_accel(self, accel: float) -> None:
		"""
		Set target acceleration of EcoVario stage.
		This method converts the acceleration from mm/s² to the encoder units used by the controller.

		:param accel: Set acceleration in mm/s²
		:type accel: float
		:return: None
		:rtype: None
		"""
		if self.simulate:
			# only print command and response in simulation mode
			print(self.eco.query(f"accel{accel}"))
			return None
		else:
			# convert acceleration from mm/s² to encoder units
			encoder_accel = accel / 0.020059880
			encoder_accel_int = round(encoder_accel)
			# write acceleration to stage and ignore return
			return self._write_sdo(0x01, 0x6083, encoder_accel_int)

	def set_deaccel(self, deaccel: float) -> None:
		"""
		Set target deceleration of EcoVario stage.
		This method converts the deceleration from mm/s² to the encoder units used by the controller

		:param deaccel: Set deceleration in mm/s²
		:type deaccel: float
		:return: None
		:rtype: None
		"""
		if self.simulate:
			# only print command and response in simulation mode
			print(self.eco.query(f"deaccel{deaccel}"))
			return None
		else:
			# convert deceleration from mm/s² to encoder units
			encoder_deaccel = deaccel / 0.020059880
			encoder_deaccel_int = round(encoder_deaccel)
			# write deceleration to stage and ignore return
			return self._write_sdo(0x01, 0x6084, encoder_deaccel_int)

	def set_control_word(self, control_word: int) -> None:
		"""
		Set control word of EcoVario stage.


		:param control_word: Set control word hex value
		:type control_word: int
		:return: None
		:rtype: None
		"""
		if self.simulate:
			# only print command and response in simulation mode
			print(self.eco.query("control word"))
			return None
		else:
			# write control word to stage and ignore return
			return self._write_sdo(0x01, 0x6040, control_word)

	def get_current_position(self) -> float:
		"""
		Get current position of EcoVario stage.

		:raises: TypeError: if position cannot be converted to mm
		:return: Current Stage position in mm
		:rtype: float
		"""
		if self.simulate:
			# only print command and response in simulation mode
			return float(self.eco.query("currpos")) * 0.00125328
		else:
			# get current hex position
			position_hex = self._read_sdo(0x01, 0x6063)
			try:
				# convert hex position to mm
				position_mm = int(position_hex, 16) * 0.001253258
			except TypeError:
				# set position to 0.0 if conversion fails
				position_mm = 0.0
			return position_mm

	def get_status_word(self) -> str:
		"""
		Get current status word of EcoVario stage.

		:return: Hex status word
		:rtype: str
		"""
		if self.simulate:
			# only print command and response in simulation mode
			return self.eco.query("currstatus")
		else:
			# get current hex status word
			status_hex = self._read_sdo(0x01, 0x6041)
			return status_hex

	def get_last_error(self) -> str:
		"""
		Get last error code from stage.
		The value is a hex string, therefore further interpretation is necessary.
		This is not currently supported.

		:return: Hex value of last error code
		:rtype: str
		"""
		if self.simulate:
			# only print command and response in simulation mode
			return self.eco.query("currerror")
		else:
			# get last error code hex value
			error_code = self._read_sdo(0x01, 0x603F)
			return error_code

	def start(self) -> None:
		"""
		Start stage. Move to latest set position.

		:return: None
		:rtype: None
		"""
		if self.simulate:
			# only print command and response in simulation mode
			print(self.eco.query("start"))
			return None
		else:
			# write start command to stage and ignore return
			return self._write_sdo(0x01, 0x6040, 0x003F)

	# TODO this does not work as of now
	def set_homing(self) -> None:
		if self.simulate:
			print("homing...")
			return None
		else:
			return self._write_sdo(0x01, 0x6040, 0x002F)

	def reset_error(self) -> None:
		"""
		Reset the latest error code to allow movement again.

		:return: None
		:rtype: None
		"""
		if self.simulate:
			# only print command and response in simulation mode
			print("resetting error...")
			return None
		else:
			# write reset error command to stage and ignore return
			return self._write_sdo(0x01, 0x6040, 0x01AF)

	def stop(self) -> None:
		"""
		Stop all stage movement.

		:return: None
		:rtype: None
		"""
		if self.simulate:
			# only print command and response in simulation mode
			print(self.eco.query("stop"))
			return None
		else:
			# write stop command to stage and ignore return
			return self._write_sdo(0x01, 0x6040, 0x0037)