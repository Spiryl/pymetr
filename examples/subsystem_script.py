import logging

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Assuming the Instrument class from pymetr or a similar package is available
from pymetr.instruments import Instrument

def command_property(cmd_str, valid_values=None, doc_str=""):
    def getter(self):
        full_cmd = f"{self.cmd_prefix}{cmd_str}?"
        logger.debug(f"Querying: {full_cmd}")
        return self._parent.query(full_cmd)

    def setter(self, value):
        full_cmd = f"{self.cmd_prefix}{cmd_str}"
        if valid_values is not None and value not in valid_values:
            logger.error(f"Invalid value for {cmd_str}. Valid values are {valid_values}.")
            raise ValueError(f"Invalid value for {cmd_str}. Valid values are {valid_values}.")
        logger.debug(f"Setting: {full_cmd} to {value}")
        self._parent.write(f"{full_cmd} {value}")

    return property(fget=getter, fset=setter, doc=doc_str)

class Subsystem:
    def __init__(self, parent, cmd_prefix):
        self._parent = parent
        self.cmd_prefix = cmd_prefix

class WaveGen(Subsystem):
    FUNCTIONS = ["SIN", "SQU", "RAMP", "PULSE", "NOISE", "DC"]

    def __init__(self, parent):
        super().__init__(parent, "WGEN:")
        self.function = command_property("FUNC", WaveGen.FUNCTIONS, "Waveform function")
        self.frequency = command_property("FREQ", doc_str="Waveform frequency")

class MyInstrument(Instrument):
    def __init__(self, resource_string):
        super().__init__(resource_string)
        self.wavegen = WaveGen(self)

# Example usage
oscilloscope = MyInstrument('TCPIP0::192.168.1.111::hislip0::INSTR')
oscilloscope.open()
oscilloscope.identity()
oscilloscope.wavegen.function = "SIN"
print(oscilloscope.wavegen.function)
oscilloscope.wavegen.frequency = "1000000"  # Set frequency to 1 MHz
print(oscilloscope.wavegen.frequency)
oscilloscope.close()
