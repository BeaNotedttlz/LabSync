import pyvisa
from pyvisa import errors
from serial import SerialException
from Devices.Descriptors import Parameter
from Devices.Storage import ParameterStorage
'''
Factors to calculate encoder position and speed have been calculated experimentally, but seem to be of sufficient precision
# TODO Factors to calculate encoder acceleration and deacceleration have also been calculated experimentally, but dont meet the precision needed

Communication with the EcoVario-Controller usually follows the SDO communication protocol. (The exact protocol can found in ~/documentation/...). 
This needed a python 32-bit environment on windows only, which is not ideal, so the communication has been split up in raw serial communication using information bytes.
'''

## class for core EcoConnect functions ##
class EcoConnect():
	position = Parameter("position", "set_position", 0.0, float)
	speed = Parameter("speed", "set_speed", 35.0, float)
	accell = Parameter("accel", "set_accel", 501.30, float)
	deaccell = Parameter("deccel", "set_deaccel", 501.30, float)

	def __init__(self, name: str, _storage: ParameterStorage, simulate: bool) -> None:
		# connected variable to check connected status when trying to write data #
		self.storage = _storage
		self.name = name
		self.connected = False
		self.simulate = simulate
		# create Recource Manager #
		self.rm = pyvisa.ResourceManager(
			"/home/merlin/Desktop/LabSync 2.2/Devices/SimResp.yaml@sim"
			if self.simulate else "")

		# add attr to storage #
		for param in type(self)._get_params():
			_storage.new_parameter(name, param.name, param.default)

	@classmethod
	def _get_params(cls):
		for attr in vars(cls).values():
			if isinstance(attr, Parameter):
				yield attr

	# Function for opening serial port #
	def open_port(self, port: str, baudrate: int) -> None:
		if self.simulate:
			port = "ASRL4::INSTR"
		try:
			self.eco = self.rm.open_resource(port, open_timeout=2000)
			self.eco.baudrate = baudrate
			self.eco.read_termination = "\r"
			self.eco.write_termination = "\r"
			self.connected = True
		except (errors.VisaIOError, SerialException) as e:
			self.connected = False
			raise ConnectionError(f"{e}")

	# Function for closing serial port #
	def close_port(self) -> None:
		if self.connected:
			self.eco.close()

	# Function for calculating checksum for serial communication #
	def _calculate_checksum(self, message) -> hex:
		sum_bytes = sum(message)
		lsb = sum_bytes & 0xFF
		checksum = (~lsb + 1) & 0xFF
		return checksum

	# Function for inverting hex values #
	def _invert_hex(self, hex_string: str) -> hex:
		bytes_list = [hex_string[i:i+2] for i in range(0, len(hex_string), 2)]
		inverse_bytes_list = bytes_list[::-1]
		inverse_hex = "".join(inverse_bytes_list)
		return inverse_hex

	# Function for writing command and reading response #
	# TODO subindex nicht fest sondern in object? muss nicht zwingend 0x00 sein! #
	def _read_sdo(self, id: hex, object: hex) -> hex:
		if self.connected:
			# calculate message bytes #
			object_1 = object >> 8
			object_2 = object & 0xFF
			message = [id, 0x40, object_2, object_1, 0x00, 0x00, 0x00, 0x00, 0x00]
			trailing_byte = self._calculate_checksum(message)
			message.append(trailing_byte)

			# write message and listen for response #
			self.eco.write_raw(message)

			#self.eco.flush(pyvisa.constants.VI_READ_BUF_DISCARD)
			response = self.eco.read_bytes(20).hex()[20:][10:-2]

			response_hex = self._invert_hex(response)
			return response_hex
		else:
			return None

	# Function for writing command without reading response #
	def _write_sdo(self, id: hex, object: hex, value: int) -> None:
		if self.connected:
			# calculate message bytes #
			object_1 = object >> 8
			object_2 = object & 0xFF
			hex_value = value.to_bytes(4, byteorder='little')
			value_list = list(hex_value)

			message = [id, 0x22, object_2, object_1, 0x00, value_list[0], value_list[1], value_list[2], value_list[3]]
			trailing_byte = self._calculate_checksum(message)
			message.append(trailing_byte)

			# write message #
			self.eco.write_raw(message)
			_ = self.eco.read_bytes(20)
		else:
			return None

	def set_position(self, position: float) -> None:
		if self.simulate:
			print(self.eco.query(f"pos{position}"))
			return None
		else:
			encoder_position = position / 0.001253258
			encoder_position_int = round(encoder_position)
			return self._write_sdo(0x01, 0x607A, encoder_position_int)

	def set_speed(self, speed: float) -> None:
		if self.simulate:
			print(self.eco.query(f"speed{speed}"))
			return None
		else:
			encoder_speed = speed / 0.000019585
			encoder_speed_int = round(encoder_speed)
			return self._write_sdo(0x01, 0x6081, encoder_speed_int)

	def set_accel(self, accel: float, deaccel: float, sync: bool) -> None:
		if self.simulate:
			print(self.eco.query(f"accel{accel}"))
			return None
		else:
			encoder_accel = accel / 0.020059880
			encoder_accel_int = round(encoder_accel)
			return self._write_sdo(0x01, 0x6083, encoder_accel_int)

	def set_deaccel(self, deaccel: float) -> None:
		if self.simulate:
			print(self.eco.query(f"deaccel{deaccel}"))
			return None
		else:
			encoder_deaccel = deaccel / 0.020059880
			encoder_deaccel_int = round(encoder_deaccel)
			return self._write_sdo(0x01, 0x6084, encoder_deaccel_int)

	def set_control_word(self, control_word: hex) -> None:
		if self.simulate:
			print(self.eco.query("control word"))
			return None
		else:
			return self._write_sdo(0x01, 0x6040, control_word)

	def get_current_position(self) -> float:
		if self.simulate:
			return float(self.eco.query("currpos")) * 0.00125328
		else:
			position_hex = self._read_sdo(0x01, 0x6063)
			try:
				position_mm = int(position_hex, 16) * 0.001253258 # factor needed to get from encoer position to mm #
			except TypeError:
				position_mm = 0.0
			return position_mm

	def get_status_word(self) -> hex:
		if self.simulate:
			return self.eco.query("currstatus")
		else:
			status_hex = self._read_sdo(0x01, 0x6041)
			return status_hex

	def get_last_error(self) -> hex:
		if self.simulate:
			return self.eco.query("currerror")
		else:
			error_code = self._read_sdo(0x01, 0x603F)
			return error_code

	# Function to start stage #
	def start(self) -> None:
		if self.simulate:
			print(self.eco.query("start"))
			return None
		else:
			return self._write_sdo(0x01, 0x6040, 0x003F) # TODO This should only be 0x002F -> was 0x003F

	# TODO this should set the reference position of the stage #
	def set_homing(self) -> None:
		if self.simulate:
			print("homing...")
			return None
		else:
			return self._write_sdo(0x01, 0x6040, 0x002F)

	def reset_error(self) -> None:
		if self.simulate:
			print("resetting error...")
			return None
		else:
			return self._write_sdo(0x01, 0x6040, 0x01AF)

	# Function to immediately stop stage #
	def stop(self) -> None:
		if self.simulate:
			print(self.eco.query("stop"))
			return None
		else:
			return self._write_sdo(0x01, 0x6040, 0x0037)