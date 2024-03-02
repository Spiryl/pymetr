# trigger.py

import logging
from enum import Enum
from Pymetr.instruments import InstrumentSubsystem

# Create a logger for each module. The logger will inherit the global configuration.
logger = logging.getLogger(__name__)

class Trigger(InstrumentSubsystem):

    class Mode(Enum):
        EDGE = "EDGE"
        VIDEO = "VIDEO"
        # Add other modes as needed

    class Slope(Enum):
        POSITIVE = "POS"
        NEGATIVE = "NEG"
        # Add other slopes as needed

    def __init__(self, parent):
        super().__init__(parent)
        self._mode = None
        self._source = None
        self._level = None
        self._slope = None

    @property
    def mode(self):
        # This method is unchanged; provided for completeness
        pass

    @mode.setter
    def mode(self, value):
        try:
            if isinstance(value, self.Mode):
                cmd = f":TRIGger:MODE {value.value}"
                self._parent.write(cmd)
                logger.debug(f"Sent command to oscilloscope: {cmd}")
                self._mode = value
            else:
                logger.warning(f"Attempted to set invalid trigger mode: {value}")
        except Exception as e:
            logger.exception(f"Error setting trigger mode: {e}")

    @property
    def source(self):
        # This method is unchanged; provided for completeness
        pass

    @source.setter
    def source(self, value):
        try:
            cmd = f":TRIGger:SOURCE {value}"
            self._parent.write(cmd)
            logger.debug(f"Sent command to oscilloscope: {cmd}")
            self._source = value
        except Exception as e:
            logger.exception(f"Error setting trigger source: {e}")

    @property
    def level(self):
        # This method is unchanged; provided for completeness
        pass

    @level.setter
    def level(self, value):
        try:
            cmd = f":TRIGger:LEVel {value}"
            self._parent.write(cmd)
            logger.debug(f"Sent command to oscilloscope: {cmd}")
            self._level = value
        except Exception as e:
            logger.exception(f"Error setting trigger level: {e}")

    @property
    def slope(self):
        # This method is unchanged; provided for completeness
        pass

    @slope.setter
    def slope(self, value):
        try:
            if isinstance(value, self.Slope):
                cmd = f":TRIGger:SLOPe {value.value}"
                self._parent.write(cmd)
                logger.debug(f"Sent command to oscilloscope: {cmd}")
                self._slope = value
            else:
                logger.warning(f"Attempted to set invalid trigger slope: {value}")
        except Exception as e:
            logger.exception(f"Error setting trigger slope: {e}")

    def sync(self):
        """Ensures the trigger settings are synchronized with the oscilloscope's current configuration."""
        try:
            super().sync()
            logging.info("Synchronized trigger settings with oscilloscope.")
        except Exception as e:
            logging.error(f"Error synchronizing trigger settings: {e}")
