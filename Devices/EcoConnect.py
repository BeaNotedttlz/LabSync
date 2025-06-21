import pyvisa
from pyvisa import errors
from serial import SerialException
from Devices.descriptors import Param
'''
Factors to calculate encoder position and speed have been calculated experimentally, but seem to be of sufficient precision
# TODO Factors to calculate encoder acceleration and deacceleration have also been calculated experimentally, but dont meet the precision needed

Communication with the EcoVario-Controller usually follows the SDO communication protokoll. (The exact protokoll can found in ~/documentation/...). This needed a python 32-bit environment on windows only, which is not ideal, so the communication has been split up in raw serial communication using information bytes.
'''

## class for core EcoConnect functions ##
class EcoConnect():
    position = Param("position", 0.0)
    speed = Param("speed", 35.0)
    accelleration = Param("accel", 501.30)
    deaccelleration = Param("deccel", 501.30)

    def __init__(self, simulate: bool) -> None:
        # connected variable to check connected status when trying to write data #
        self.connected = False
        self.simulate = simulate
        # create Recource Manager #
        self.rm = pyvisa.ResourceManager("Devices/SimResp.yaml@sim" if self.simulate else "")

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
            raise ConnectionError

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

    # Function for getting current stage position #
    def _get_current_position(self) -> float:
        if self.simulate:
            return float(self.eco.query("currpos")) * 0.00125328
        try:
            position_hex = self._read_sdo(0x01, 0x6063)
            position_mm = int(position_hex, 16) * 0.001253258 # factor needed to get from encoer position to mm #
            return position_mm
        except ConnectionError:
            return -1

    # Function for getting current status word #
    def _get_status_word(self) -> hex:
        if self.simulate:
            return self.eco.query("currstatus")

        try:
            status_hex = self._read_sdo(0x01, 0x6041)
            return status_hex
        except ConnectionError:
            return -1

    # Function for getting last error code # TODO was genau gibt der zurück?
    def _get_last_error(self) -> hex:
        if self.simulate:
            return self.eco.query("currerror")

        try:
            error_code = self._read_sdo(0x01, 0x603F)
            return error_code
        except ConnectionError:
            return -1

    # Function for writing new position to stage #
    def _write_position(self, pos: float) -> None:
        # check if position is out of max. range #
        if pos >= 2530:
            raise ValueError(f"Position: {pos} out of max. range!")

        if self.simulate:
            print(self.eco.query(f"pos{pos}"))
            return

        # calculate encoder position #
        encoder_position = pos / 0.001253258
        encoder_position_int = round(encoder_position)
        self._write_sdo(0x01, 0x607A, encoder_position_int)


    # Function for writing new speed to Stage #
    def _write_speed(self, speed: float) -> None:
        if self.simulate:
            print(self.eco.query(f"speed{speed}"))
            return
        # Calculate encoder speed #
        encoder_speed = speed / 0.000019585
        encoder_speed_int = round(encoder_speed)
        self._write_sdo(0x01, 0x6081, encoder_speed_int)

    # Function for writing new acceleration and deacceleration to stage #
    def _write_accel_deaccel(self, accel: float, deaccel: float) -> None:
        if self.simulate:
            print(self.eco.query(f"accel{accel}"))
            print(self.eco.query(f"deaccel{deaccel}"))
            return
        # calculating encoder acceleration and deacceleraion #
        encoder_accel = accel / 0.020059880
        encoer_deaccel = deaccel / 0.020059880
        encoder_accel_int = round(encoder_accel)
        encoder_deaccel_int = round(encoer_deaccel)

        self._write_sdo(0x01, 0x6083, encoder_accel_int)
        self._write_sdo(0x01, 0x6084, encoder_deaccel_int)

    # Function for writing control word to stage #
    def _write_control_word(self, control_word: hex) -> None:
        if self.simulate:
            print(self.eco.query("control word"))
            return

        self._write_sdo(0x01, 0x6040, control_word)

    # Function to start stage #
    def start(self) -> None:
        if self.simulate:
            print(self.eco.query("start"))
            return

        self._write_sdo(0x01, 0x6040, 0x003F)

    # Function to immediately stop stage #
    def stop(self) -> None:
        if self.simulate:
            print(self.eco.query("stop"))
            return

        self._write_sdo(0x01, 0x6040, 0x0037)

