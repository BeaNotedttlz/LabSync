"""
Module for controlling EcoVario linear stages via EcoVario-Controller over serial communication.
In contrast to the official EcoConnect library, this implementation uses PyVISA for communication,
allowing for communication without Python 32-bit and enabling usage for Unix based operating systems.
@autor: Merlin Schmidt
@date: 2025-15-10
@file: src/backend/devices/eco_connect.py
@note: Use at your own risk.
"""

import os, pyvisa
from typing import Any
from pyvisa import errors
from serial import SerialException
from src.backend.connection_status import ConnectionStatus
from src.core.context import DeviceConnectionError

class EcoConnect:
	"""
	EcoConnect class for serial communication with EcoVario linear stage. Using PyVISA for communication protocols.

	:param name: Name of the device instance.
	:type name: str
	:param simulate: Flag to indicate simulation mode.
	:type simulate: bool
	:return None
	:rtype: None
	"""
	def __init__(self, name: str, simulate: bool) -> None :
		"""Constructor method
		"""
		# save variables to self
		self.name = name
		self.simulate = simulate
		self.EcoVario = None
		# connection status
		self.status = ConnectionStatus.DISCONNECTED

		sim_path = os.path.join(
			os.path.dirname(os.path.abspath(__file__)),
			"simulation.yaml"
		)
		# create Resource
		self.rm = pyvisa.ResourceManager(
			f"{sim_path}@sim"
			if self.simulate else ""
		)

	def open_port(self, port: str, baudrate: int) -> None:
		"""
		Open serial port for communication with EcoVario controller.

		:param port: Serial port address
		:type port: str
		:param baudrate: Baudrate for serial communication
		:type baudrate: int
		:raises ConnectionError: If port cannot be opened
		:return: None
		:rtype: None
		"""
		# port for simulation
		if self.simulate:
			port = "ASRL4::INSTR"

		try:
			# open serial port
			self.EcoVario = self.rm.open_resource(port, open_timeout=2000)
			self.EcoVario.baudrate = baudrate
			self.EcoVario.write_termination = "\r"
			self.EcoVario.read_termination = "\r"
			# if successful
			self.status = ConnectionStatus.CONNECTED
		except (errors.VisaIOError, SerialException) as e:
			self.status = ConnectionStatus.DISCONNECTED
			raise DeviceConnectionError(device_id=self.name, original_error=e) from e

	def close_port(self) -> None:
		"""
		Close serial port for EcoVario controller.

		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			self.EcoVario.close()
			self.status = ConnectionStatus.DISCONNECTING
		return None

	def start(self) -> None:
		"""
		Start stage. Move to latest set position.

		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				# only print command in simulation mode
				print(self.EcoVario.query("start"))
			else:
				self._write_sdo(0x01, 0x6040, 0x003F)
		return None

	def stop(self) -> None:
		"""
		Stop all stage movement.

		:return: None
		:rtype: None
		"""

		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(self.EcoVario.query("stop"))
			else:
				self._write_sdo(0x01, 0x6040, 0x0037)
		return None

	def _write_sdo(self, id: int, object: int, value: int) -> None:
		"""
		Write sdo to EcoVario controller.
		This method sends a write request to EcoVario controller and waits for the appropraite response.


		:param id: Id of the SDO
		:type id: int
		:param object: Object to write
		:tyoe object: int
		:param value: Value to write to device
		:type value: int
		:return: None
		:rtype: None
		"""
		# calculate message bytes
		object_1 = object >> 8
		object_2 = object & 0xFF
		hex_value = value.to_bytes(4, byteorder="little")
		value_list = list(hex_value)

		# generate message
		message = [id, 0x22, object_2, object_1, value_list[0], value_list[1], value_list[2], value_list[3]]
		# caculate and append checksum
		trailing_byte = self._calculate_checksum(message)
		message.append(trailing_byte)

		# write message and read response
		self.EcoVario.write(message)
		# but response can generally be ignored
		_ = self.EcoVario.read_bytes(20)
		return None

	def _read_sdo(self, id, object) -> str:
		"""
		Send a read requrest to EcoVario controller.
		This method sends a read request to EcoVario controller and waits for the appropraite response.

		:param id: Id of the SDO
		:type id: int
		:param object: Object to read
		:type object: int
		:return: The hex response of the device
		:rtype: str
		"""
		# calculate message bytes
		object_1 = object >> 8
		object_2 = object & 0xFF
		message = [id, 0x40, object_2, object_1, 0x00, 0x00, 0x00, 0x00, 0x00]
		# get trailing checksum byte
		trailing_byte = self._calculate_checksum(message)
		message.append(trailing_byte)

		# write message and listen for response
		self.EcoVario.write_raw(message)

		# Read bytes and remove header and checksum
		# [20:] is necessary to remove the request that is returned by the device
		response = self.EcoVario.read_bytes(20).hex()[20:][10:-2]

		# Invert the byte order of the response
		response_hex = self._invert_hex(response)
		return response_hex

	@staticmethod
	def _invert_hex(hex_string: str) -> str:
		"""
		Private method to invert byte order of hex string.

		:param hex_string: Hex number to invert
		:type hex_string: str
		:return: inverted hex string
		:rtype: str
		"""
		bytes_list = [hex_string[i:i + 2] for i in range(0, len(hex_string), 2)]
		inverse_bytes_list = bytes_list[::-1]
		inverse_hex = "".join(inverse_bytes_list)
		return inverse_hex

	@staticmethod
	def _calculate_checksum(message: Any) -> int:
		"""
		Private method to calculate checksum for EcoVario communication protocol.

		:param message: Message to calculate checksum for
		:type message: Any
		:return: Returns checksum byte
		:rtype: int
		"""

		sum_bytes = sum(message)
		lsb = sum_bytes & 0xFF
		checksum = (~lsb + 1) & 0xFF
		return checksum

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
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(self.EcoVario.query(f"pos{position}"))
			else:
				# convert position from mm to encoder units
				encoder_position = position / 0.001253258
				encoder_position_int = round(encoder_position)
				# write position to stage and ignore return
				self._write_sdo(0x01, 0x607A, encoder_position_int)
		return None

	def set_speed(self, speed: float) -> None:
		"""
		Set target speed of EcoVario stage.
		This method converts the speed from mm/s to the encoder units used by the controller.

		:param speed: Set speed in mm/s
		:type speed: float
		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(self.EcoVario.query(f"speed{speed}"))
			else:
				# convert speed from mm/s to encoder units
				encoder_speed = speed / 0.000019585
				encoder_speed_int = round(encoder_speed)
				# write speed to stage and ignore return
				self._write_sdo(0x01, 0x6081, encoder_speed_int)
		return None

	def set_acceleration(self, acceleration: float) -> None:
		"""
		Set target acceleration of EcoVario stage.
		This method converts the acceleration from mm/s² to the encoder units used by the controller.

		:param acceleration: Set acceleration in mm/s²
		:type acceleration: float
		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(self.EcoVario.query(f"accel{acceleration}"))
			else:
				# convert acceleration from mm/s² to encoder units
				encoder_acceleration = acceleration / 0.020059880
				encoder_acceleration_int = round(encoder_acceleration)
				# write acceleration to stage and ignore return
				self._write_sdo(0x01, 0x6083, encoder_acceleration_int)
		return None

	def set_deacceleration(self, deacceleration: float) -> None:
		"""
		Set target deceleration of EcoVario stage.
		This method converts the deceleration from mm/s² to the encoder units used by the controller

		:param deacceleration: Set deceleration in mm/s²
		:type deacceleration: float
		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(self.EcoVario.query(f"deaccel{deacceleration}"))
			else:
				# convert deceleration from mm/s² to encoder units
				encoder_deacceleration = deacceleration / 0.020059880
				encoder_deacceleration_int = round(encoder_deacceleration)
				# write deceleration to stage and ignore return
				self._write_sdo(0x01, 0x6084, encoder_deacceleration_int)
		return None

	def get_current_position(self) -> float | None:
		"""
		Get current position of EcoVario stage.

		:raises: TypeError: if position cannot be converted to mm
		:return: Current Stage position in mm, or None if the device is not conncted
		:rtype: float | NOne
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				# only print command and response in simulation mode
				return float(self.EcoVario.query("currpos")) * 0.00125328
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
		else:
			return None

	def get_current_error(self) -> str | None:
		"""
		Get last error code from stage.
		The value is a hex string, therefore further interpretation is necessary.
		This is not currently supported.

		:return: Hex value of last error code, or None if the device is not connected
		:rtype: str | None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				# only print command and response in simulation mode
				return self.EcoVario.query("currerror")
			else:
				# get last error code hex value
				error_code = self._read_sdo(0x01, 0x603F)
				return error_code
		else:
			return None

	def reset_current_error(self) -> None:
		"""
		Reset the latest error code to allow movement again.

		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print("resetting error...")
			else:
				self._write_sdo(0x01, 0x6040, 0x01AF)
		return None

	def set_control_word(self, control_word: int) -> None:
		"""
		Set control word of EcoVario stage.


		:param control_word: Set control word hex value
		:type control_word: int
		:return: None
		:rtype: None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				print(self.EcoVario.query("control word"))
			else:
				self._write_sdo(0x01, 0x6040, control_word)
		return None

	def get_status_word(self) -> str | None:
		"""
		Get current status word of EcoVario stage.

		:return: Hex status word or None if the device is not connected
		:rtype: str | None
		"""
		if self.status == ConnectionStatus.CONNECTED:
			if self.simulate:
				return self.EcoVario.query("currstatus")
			else:
				status_hex = self._read_sdo(0x01, 0x6041)
				return status_hex
		else:
			return None

	def home_stage(self) -> None:
		if self.simulate:
			print("homing stage ...")
		else:
			# Turning on Stage / Ready to start
			self._write_sdo(0x01, 0x6040, 0xF)
			# Set the homing method
			self._write_sdo(0x01, 0x6098, 0x11)
			# Set the operating mode to homing
			self._write_sdo(0x01, 0x6060, 0x6)
			# Start the homing process
			self._write_sdo(0x01, 0x6040, 0x1F)
		return