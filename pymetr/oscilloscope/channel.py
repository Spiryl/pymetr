# _Channel.py

import logging
from enum import Enum, auto
from pymetr.instrument import InstrumentSubsystem

class Channel(InstrumentSubsystem):
    """
    Represents an individual channel on the oscilloscope, allowing control over its display, scaling, 
    and other properties.
    """
    
    class DisplayState(Enum):
        ON = '1'
        OFF = '0'

    class Coupling(Enum):
        AC = 'AC'
        DC = 'DC'

    def __init__(self, parent, channel_number):
        super().__init__(parent)
        self.channel_number = channel_number
        self._display = None
        self._scale = None
        self._offset = None
        self._coupling = None
        self._probe_attenuation = None

    @property
    def display(self):
        response = self._parent.query(f":CHANnel{self.channel_number}:DISPlay?")
        self._display = self.DisplayState(response.strip())
        logging.debug(f"Channel {self.channel_number} display state fetched: {self._display.name}")
        return self._display.name

    @display.setter
    def display(self, value):
        if value in self.DisplayState.__members__:
            self._parent.write(f":CHANnel{self.channel_number}:DISPlay {self.DisplayState[value].value}")
            logging.info(f"Channel {self.channel_number} display state set to: {value}")
            self._display = self.DisplayState[value]
        else:
            logging.error(f"Invalid display state: {value} for Channel {self.channel_number}")

    @property
    def scale(self):
        response = self._parent.query(f":CHANnel{self.channel_number}:SCALe?")
        self._scale = float(response)
        logging.debug(f"Channel {self.channel_number} scale fetched: {self._scale}")
        return self._scale

    @scale.setter
    def scale(self, value):
        self._parent.write(f":CHANnel{self.channel_number}:SCALe {value}")
        logging.info(f"Channel {self.channel_number} scale set to: {value}")
        self._scale = float(self._parent.query(f":CHANnel{self.channel_number}:SCALe?"))

    @property
    def offset(self):
        response = self._parent.query(f":CHANnel{self.channel_number}:OFFSet?")
        self._offset = float(response)
        logging.debug(f"Channel {self.channel_number} offset fetched: {self._offset}")
        return self._offset

    @offset.setter
    def offset(self, value):
        self._parent.write(f":CHANnel{self.channel_number}:OFFSet {value}")
        logging.info(f"Channel {self.channel_number} offset set to: {value}")
        self._offset = float(self._parent.query(f":CHANnel{self.channel_number}:OFFSet?"))

    @property
    def coupling(self):
        response = self._parent.query(f":CHANnel{self.channel_number}:COUPling?")
        self._coupling = self.Coupling(response.strip())
        logging.debug(f"Channel {self.channel_number} coupling fetched: {self._coupling.name}")
        return self._coupling.name

    @coupling.setter
    def coupling(self, value):
        if value in self.Coupling.__members__:
            self._parent.write(f":CHANnel{self.channel_number}:COUPling {self.Coupling[value].value}")
            logging.info(f"Channel {self.channel_number} coupling set to: {value}")
            self._coupling = self.Coupling[value]
        else:
            logging.error(f"Invalid coupling: {value} for Channel {self.channel_number}")

    @property
    def probe_attenuation(self):
        response = self._parent.query(f":CHANnel{self.channel_number}:PROBe?")
        self._probe_attenuation = float(response)
        logging.debug(f"Channel {self.channel_number} probe attenuation fetched: {self._probe_attenuation}")
        return self._probe_attenuation

    @probe_attenuation.setter
    def probe_attenuation(self, value):
        self._parent.write(f":CHANnel{self.channel_number}:PROBe {value}")
        logging.info(f"Channel {self.channel_number} probe attenuation set to: {value}")
        self._probe_attenuation = float(self._parent.query(f":CHANnel{self.channel_number}:PROBe?"))

    def sync(self):
        """ Synchronizes channel settings with the oscilloscope's current configuration. """
        super().sync()
        logging.info(f"Synchronized channel {self.channel_number} settings with oscilloscope.")
