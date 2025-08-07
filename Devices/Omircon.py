import pyvisa
from pyvisa import errors
from serial import SerialException
from Devices.Storage import ParameterStorage
from Devices.Descriptors import Parameter
import time

from Exceptions import ParameterNotSetError, ParameterOutOfRangeError


# TODO - andere commands hinzufügen?

## class for core Omicron LuxX functions ##
class OmicronLaser:
    firmware = Parameter("firmware", None, ["ND", "ND", "ND"], list)
    specs = Parameter("specs", None, ["ND", "ND"], list)
    max_power = Parameter("max_power", None, 1, int)
    op_mode = Parameter("op_mode", "set_op_mode", 0, int)
    temp_power = Parameter("temp_power","set_temp_power", 0.0, float)
    power = Parameter("power", "set_power", 0.0, float)
    emission = Parameter("emission", "set_emission", False, bool)
    error_code = Parameter("error_code", "", "0x00", str)

    def __init__(self, name: str, _storage: ParameterStorage, simulate: bool) -> None:
        # connected variable to check connected status when trying to write data #
        self.Laser = None
        self.storage = _storage
        self.name = name
        self.connected = False
        self.simulate = simulate
        # create Recource Manager #
        self.rm = pyvisa.ResourceManager(
            "/home/merlin/Desktop/LabSync 2.2/Devices/SimResp.yaml@sim"
            if self.simulate else "")

        for param in type(self)._get_params():
            _storage.new_parameter(name, param.name, param.default)

    @classmethod
    def _get_params(cls):
        for attr in vars(cls).values():
            if isinstance(attr, Parameter):
                yield attr

    # Function to write command to laser and read response #
    def _ask(self, command: str) -> list:
        if self.connected:
            response = self.Laser.query("?" + command)
            return response[4:].split("|")
        return [""]

    # Function to write command to laser without reading direct response #
    def _set(self, what: str, value: str) -> str:
        if self.connected:
            response = self.Laser.query("?" + what + value)
            return response[4:]
        return ""

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
            self.max_power = int(self._ask("GMP")[0])

            # store laser information #
        except (errors.VisaIOError, SerialException) as e:
            self.connected = False
            raise ConnectionError(f"{e}")

    # Function for closing serial port #
    def close_port(self) -> None:
        if self.connected:
            self.Laser.close()

    '''
        List of operating modes:

        0 - Standby, no emission
        1 - CW ACC
        2 - CW APC
        3 - Analog modulation, with ACC only
        4 - Digital modulation, with ACC only
        5 - Analog and Digital modulation, with ACC only
    '''
    def set_op_mode(self, value) -> None:
        response = self._set("ROM", str(value))
        if response != ">":
            raise ParameterNotSetError("Operating mode could not be set")
        else:
            return None
    '''
        Permanent power can set and will stay after reboot or reset of the laser.
        Though this should not be used most of the time! The memory can only be set a certain finite amount of times!

        For most power setting operations, temporary power should be used!
        (for further information please read ~/documentation/luxx_programmers_guide)
        '''

    def set_power(self, value) -> None:
        response = self._set("SLP", str(value))
        if response != ">":
            raise ParameterNotSetError("Power could not be set")
        else:
            return None

    def set_temp_power(self, value) -> None:
        if value > 100.0:
            raise ParameterOutOfRangeError(f"Temporary power {value} is out of range (0.0 - 100.0)")
        response = self._set("TTP", str(value))
        if response != ">":
            raise ParameterNotSetError("Temporary power could not be set")
        else:
            return None

    def get_op_mode(self) -> str:
        response = self._ask("ROM")[0]
        return response

    def get_power(self) -> str:
        response = self._ask("GLP")[0]
        return response

    def get_temp_power(self) -> str:
        response = self._ask("TTP")[0]
        return response

    def set_emission(self, value) -> None:
        if value:
            response = self._ask("LOn")[0]
            if response != ">":
                raise ParameterNotSetError("Emission could not be set")
            else:
                return None
        else:
            response = self._ask("LOf")[0]
            if response != ">":
                raise ParameterNotSetError("Emission could not be set")
            else:
                return None

    def get_error_byte(self) -> hex:
        response = self._ask("GLF")[0]
        return bin(int(response, 16))

    def reset_controller(self) -> None:
        timeout = time.time() + 10
        self.Laser.write("?RsC")
        while True:
            response = self.Laser.read()
            if response.strip() == "!RsC>":
                break
            if time.time() > timeout:
                raise TimeoutError("Timeout while waiting for !RsC response")
            time.sleep(0.1)




