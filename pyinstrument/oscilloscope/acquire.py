# acquire.py

import logging
from enum import Enum
from pyinstrument.instruments import InstrumentSubsystem

class Acquire(InstrumentSubsystem):
    """
    Manages the acquisition parameters of the oscilloscope, including mode, type,
    sample rate, depth, and count of acquisition.

    Attributes:
        _mode (Mode): The current acquisition mode.
        _type (Type): The type of acquisition (e.g., normal, average).
        _sample_rate (float): The sample rate in samples per second.
        _depth (int): The depth of the acquisition.
        _count (int): The number of acquisitions to combine.
    """

    class Mode(Enum):
        RTIM = "RTIM"
        SEGM = "SEGM"

    class Type(Enum):
        NORMAL = "NORM"
        AVERAGE = "AVER"
        HRES = "HRES"
        PEAK = "PEAK"

    def __init__(self, parent):
        super().__init__(parent)
        self._mode = None
        self._type = None
        self._sample_rate = None
        self._depth = None
        self._count = None

    @property
    def mode(self):
        response = self._parent.query(":ACQuire:MODE?")
        self._mode = self.Mode(response.strip())
        logging.debug(f"Acquired mode: {self._mode}")
        return self._mode

    @mode.setter
    def mode(self, value):
        if isinstance(value, self.Mode):
            self._parent.write(f":ACQuire:MODE {value.value}")
            logging.info(f"Set acquisition mode to: {value.value}")
            self._mode = value
        else:
            logging.error(f"Invalid acquisition mode: {value}")

    @property
    def type(self):
        try:
            response = self._parent.query(":ACQuire:TYPe?").strip()
            self._type = self.Type(response)
            logging.debug(f"Acquire type fetched: {self._type}")
            return self._type
        except Exception as e:
            logging.error(f"Error fetching acquire type: {e}")
            return None

    @type.setter
    def type(self, value):
        try:
            if isinstance(value, self.Type):
                self._parent.write(f":ACQuire:TYPe {value.value}")
                logging.info(f"Acquire type set to: {value.value}")
                self._type = value
            else:
                raise ValueError(f"Invalid type: {value}. Choose from {[type.value for type in self.Type]}.")
        except Exception as e:
            logging.error(f"Error setting acquire type: {e}")

    @property
    def sample_rate(self):
        try:
            response = self._parent.query(":ACQuire:SRATe?").strip()
            self._sample_rate = float(response)
            logging.debug(f"Sample rate fetched: {self._sample_rate}")
            return self._sample_rate
        except Exception as e:
            logging.error(f"Error fetching sample rate: {e}")
            return None

    @sample_rate.setter
    def sample_rate(self, value):
        try:
            self._parent.write(f":ACQuire:SRATe {value}")
            logging.info(f"Sample rate set to: {value}")
            self._sample_rate = value
        except Exception as e:
            logging.error(f"Error setting sample rate: {e}")

    @property
    def depth(self):
        try:
            response = self._parent.query(":ACQuire:DEPTh?").strip()
            self._depth = int(response)
            logging.debug(f"Depth fetched: {self._depth}")
            return self._depth
        except Exception as e:
            logging.error(f"Error fetching depth: {e}")
            return None

    @depth.setter
    def depth(self, value):
        try:
            self._parent.write(f":ACQuire:DEPTh {value}")
            logging.info(f"Depth set to: {value}")
            self._depth = value
        except Exception as e:
            logging.error(f"Error setting depth: {e}")

    @property
    def count(self):
        response = self._parent.query(":ACQuire:COUNT?")
        self._count = int(response)
        logging.debug(f"Acquired count: {self._count}")
        return self._count

    @count.setter
    def count(self, value):
        self._parent.write(f":ACQuire:COUNT {value}")
        logging.info(f"Set acquisition count to: {value}")
        self._count = value

    def sync(self):
        """Synchronizes acquisition settings with the oscilloscope's current configuration."""
        super().sync()
        logging.info("Synchronized acquisition settings with oscilloscope.")