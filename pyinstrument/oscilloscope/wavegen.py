# wavegen.py

import logging
from enum import Enum
from pyinstrument.instruments import InstrumentSubsystem

class WaveGen(InstrumentSubsystem):
    """
    Manages the built-in waveform generator (WGEN) of the oscilloscope, controlling waveform output and modulation.
    """
    
    class Function(Enum):
        SINusoid = 'SIN'
        SQUare = 'SQU'
        RAMP = 'RAMP'
        PULSe = 'PULS'
        NOISe = 'NOIS'
        DC = 'DC'
        
    class OutputState(Enum):
        ON = '1'
        OFF = '0'

    def __init__(self, parent):
        super().__init__(parent)
        self._frequency = None
        self._function = None
        self._amplitude = None
        self._output = None

    @property
    def frequency(self):
        response = self._parent.query(":WGEN:FREQuency?")
        self._frequency = float(response)
        logging.debug(f"WaveGen frequency fetched: {self._frequency}")
        return self._frequency

    @frequency.setter
    def frequency(self, value):
        self._parent.write(f":WGEN:FREQuency {value}")
        logging.info(f"WaveGen frequency set to: {value}")

    @property
    def function(self):
        response = self._parent.query(":WGEN:FUNCtion?")
        self._function = self.Function(response.strip())
        logging.debug(f"WaveGen function fetched: {self._function.name}")
        return self._function.name

    @function.setter
    def function(self, value):
        if value in self.Function.__members__:
            self._parent.write(f":WGEN:FUNCtion {self.Function[value].value}")
            logging.info(f"WaveGen function set to: {value}")
            self._function = self.Function[value]
        else:
            logging.error(f"Invalid WaveGen function: {value}")

    @property
    def amplitude(self):
        response = self._parent.query(":WGEN:VOLTage?")
        self._amplitude = float(response)
        logging.debug(f"WaveGen amplitude fetched: {self._amplitude}")
        return self._amplitude

    @amplitude.setter
    def amplitude(self, value):
        self._parent.write(f":WGEN:VOLTage {value}")
        logging.info(f"WaveGen amplitude set to: {value}")

    @property
    def output(self):
        response = self._parent.query(":WGEN:OUTPut?")
        self._output = self.OutputState(response.strip())
        logging.debug(f"WaveGen output state fetched: {self._output.name}")
        return self._output.name

    @output.setter
    def output(self, value):
        if value in self.OutputState.__members__:
            self._parent.write(f":WGEN:OUTPut {self.Output[value].value}")
            logging.info(f"WaveGen output state set to: {value}")
            self._output = self.OutputState[value]
        else:
            logging.error(f"Invalid WaveGen output state: {value}")

    def sync(self):
        """ Synchronizes WaveGen settings with the oscilloscope's current configuration. """
        super().sync()
        logging.info("Synchronized WaveGen settings with oscilloscope.")