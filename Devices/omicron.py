import pyvisa
from pyvisa import errors
from serial import SerialException
from Devices.storage import ParameterStorage
# TODO - andere commands hinzufügen?

## class for core Omicron LuxX functions ##
class OmicronLaser():
	def __init__(self, simulate: bool) -> None:
		# connected variable to check connected status when trying to write data #
		self.connected = False
		self.simulate = simulate
		# create Recource Manager #
		self.rm = pyvisa.ResourceManager("Devices/SimResp.yaml@sim" if self.simulate else "")

		# create storage module #
		self.storage = ParameterStorage()
		self.storage._add_parameter("Laser", "firmware", ["ND", "ND", "ND"])
		self.storage._add_parameter("Laser", "specs", ["ND", "ND"])
		self.storage._add_parameter("Laser", "max_power", 1)

		self.storage._add_parameter("Laser", "operating_mode", 0)
		self.storage._add_parameter("Laser", "control_mode", 0)
		self.storage._add_parameter("Laser", "temporary_power", 0.0)
		self.storage._add_parameter("Laser", "if_active", False)

	# Function to write command to laser and read response #
	def _ask(self, command: bytes) -> str:
		if self.connected:
			response = self.Laser.query("?" + command)
			return response[4:].split("|")
		else:
			raise ConnectionError

	# Function to write command to laser without reading direct response #
	def _set(self, what: bytes, value: bytes) -> str:
		if self.connected:
			response = self.Laser.query("?" + what + value)
			return response[4:]
		else:
			raise ConnectionError

	# Function for opening serial port and asking for firmware, specs and maximum power of laser diode #
	def open_port(self, port: str, baudrate: int) -> None:
		if self.simulate:
			port = "ASRL1::INSTR"
		try:
			# open serial port #
			self.Laser = self.rm.open_resource(port)
			self.Laser.baud_rate = 500000
			self.Laser.query_delay = 0.1
			self.Laser.read_termination = "\r"
			self.Laser.write_termination = "\r"
			self.connected = True

			# get laser information #
			self.firmware = self._ask("GFw|")
			self.specs = self._ask("GSI")
			self.max_power = self._ask("GMP")[0]

			# store laser information #
			self.storage._set_parameter("Laser", "firmware", self.firmware)
			self.storage._set_parameter("Laser", "specs", self.specs)
			self.storage._set_parameter("Laser", "max_power", self.max_power)
		except (errors.VisaIOError, SerialException) as e:
			self.connected = False
			raise ConnectionError(f"{e}")

	# Function for closing serial port #
	def close_port(self) -> None:
		if self.connected:
			self.Laser.close()

	# Function for getting laser operating mode #
	def get_operating_mode(self) -> str:
		try:
			response = self._ask("ROM")
			self.storage._set_parameter("Laser", "operating_mode", response)
			return response
		except ConnectionError:
			return -1
	'''
	List of operating modes:

	0 - Standby, no emission
	1 - CW ACC
	2 - CW APC
	3 - Analog modulation, with ACC only
	4 - Digial modulation, with ACC only
	5 - Analog and Digital modulation, with ACC only
	'''

	# Function for setting new operating mode #
	def set_operating_mode(self, mode: int) -> bool:
		try:
			response = self._set("ROM", str(mode))
			if response == ">":
				# update storage if successful #
				self.storage._set_parameter("Laser", "operating_mode", mode)
			return response == ">"
		except ConnectionError:
			return -1

	# Function for getting current permament power #
	def get_power(self) -> str:
		try:
			response = self._ask("GLP")[0]
			# update storage #
			self.storage._set_parameter("Laser", "power",)
			return response
		except ConnectionError:
			return -1

	# Function for setting new permanent power #
	def set_power(self, value: float) -> bool:
		try:
			response = self._set("SLP", hex(value)[2:])
			if response == ">":
				# update storage if successful #
				self.storage._set_parameter("Laser", "power", value)
			return response == ">"
		except ConnectionError:
			return -1

	'''
	Permament power can set and will stay after reboot or reset of the laser.
	Though this should not be used most of the time! The memory can only be set a certain finite amount of times!

	For most power setting operations, temporary power should be used!
	(for further information please read ~/documentation/luxx_programmers_guide)
	'''

	# Function for getting temporary power #
	def get_temporary_power(self) -> str:
		try:
			response = self._ask("TPP")[0]
			# update storage #
			self.storage._set_parameter("Laser", "temporary_power", float(response))
			return response
		except ConnectionError:
			return -1

	# Function for setting temporary power #
	def set_temporary_power(self, value: float) -> bool:
		value = str(value)
		try:
			response = self._set('TPP',value)
			if response == ">":
				# update storage if successful #
				self.storage._set_parameter("Laser", "temporary_power", value)
			return response == ">"
		except ConnectionError:
			return -1

	# Function for starting laser emission #
	def laser_on(self) -> bool:
		try:
			response = self._ask("LOn")[0]
			if response == ">":
				# update storage if successful #
				self.storage._set_parameter("Laser", "if_active", True)
			return response == ">"
		except ConnectionError:
			return -1

	# Function for stopping laser emission #
	def laser_off(self) -> bool:
		try:
			response = self._ask("LOf")[0]
			if response == ">":
				# update storage if successful #
				self.storage._set_parameter("Laser", "if_active", True)
			return response == ">"
		except ConnectionError:
			return -1

	# Function for getting current error byte #
	def _get_error_byte(self) -> hex:
		try:
			response = self._ask("GLF")[0]
			return bin(int(response, 16))
		except ConnectionError:
			return	-1

