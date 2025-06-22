import pyvisa
from pyvisa import errors
from serial import SerialException
from Devices.storage import ParameterStorage
from Devices.descriptors import Param

# Posssible waveforms, inputmodes and lockmodes #
# needed to convert combobox value to actual selection #
waveforms = ["sine", "square", "triag", "dc"]
inputmodes = ["Amp+Offset", "Low+High"]
lockmodes = ["indep", "master", "slave", "off"]

## class for core TGA 1244 functions ##
class FrequencyGenerator():
    frequency = Param("frequency", 0.0, float)
    amplitude = Param("amplitude", 0.0, float)
    offset = Param("offset", 0.0, float)
    waveform = Param("waveform", 0, int)
    phase = Param("phase", 0.0, float)
    inputmode = Param("inputmode", 0, int)
    lockmode = Param("lockmode", 0, int)
    if_active = Param("if_active", False, bool)


    def __init__(self, name: str, _storage: ParameterStorage, simulate: bool) -> None:
        # connected variable to check connected status when trying to write data #
        self.name = name
        self.connected = False
        self.simulate = simulate
        # create recource Manager #
        self.rm = pyvisa.ResourceManager("Devices/SimResp.yaml@sim" if self.simulate else "")

        for param in type(self)._get_params():
            _storage.add_parameter(name, param.name, param.default)


    @classmethod
    def _get_params(cls):
        for attr in vars(cls).values():
            if isinstance(attr, Param):
                yield

    # Function for opening serial port #
    def open_port(self, port, baudrate) -> None:
        if self.simulate:
            port = "ASRL3::INSTR"
        try:
            self.TGA = self.rm.open_resource(resource_name=port, open_timeout=2000)
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
    def _write(self, what: str, value: str) -> None:
        if self.simulate:
            print(self.TGA.query(what+value))
            return
        if self.connected:
            self.TGA.write_raw(what.encode() + b" " + value.encode() + b"\n")

    # Function for applying settings #
    def apply(self, channel: int, wave: int, frequency: float, amplitude: float, offset: float, phase: float, inputmode: int, lockmode: int, if_active: bool) -> None:
        # get actual selection #
        wave = waveforms[wave]
        inputmode = inputmodes[inputmode]
        lockmode = lockmodes[lockmode]

        # set channel to edit #
        self._write('SETUPCH', str(channel))

        # set waveform and frequency #
        self._write('WAVE', wave)
        self._write('WAVFREQ', str(frequency))

        # set unit to be Voltage peak to peak and impedance of 50Ohm #
        self._write('AMPUNIT', 'VPP')
        self._write('ZLOAD', '50')

        # calculate amplitude and offset for inputmodes #
        if inputmode == "Amp+Offset":
            self._write('AMPL', str(amplitude))
            self._write("DCOFFS", str(offset))
        elif inputmode == "Low+High":
            amplitude_temp = offset - amplitude
            offset_temp = (offset+amplitude)/2

            self._write('AMPL', str(amplitude_temp))
            self._write('DCOFFS', str(offset_temp))
        self._write('PHASE', str(phase))

        # set lockmode #
        if lockmode == "indep":
            self._write('LOCKMODE', 'INDEP')
            self._write('LOCKSTAT', 'ON')
        elif lockmode == "master":
            self._write('LOCKMODE', 'MASTER')
            self._write('LOCKSTAT', 'ON')
        elif lockmode == "slave":
            self._write('LOCKMODE', 'SLAVE')
            self._write('LOCKSTAT', 'ON')
        else:
            self._write('LOCKSTAT', 'OFF')

        # set channel output #
        if if_active:
            self._write('OUTPUT', 'ON')
        else:
            self._write('OUTPUT', 'OFF')

    # Function to toggle just the output status of a channel #
    def toggle_channel_output(self, channel: int, if_on: bool) -> None:
        self._write('SETUPCH', str(channel))
        if if_on:
            self._write('OUTPUT', 'ON')
        else:
            self._write('OUTPUT', 'OFF')

        # update storage #
        self.storage._set_parameter("C"+str(channel), "if_active", if_on)
