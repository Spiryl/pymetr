# timebase.py

import logging
from enum import Enum
from pyinstrument.instruments import InstrumentSubsystem

class Timebase(InstrumentSubsystem):
    """
    Handles the timebase settings of the oscilloscope which control the horizontal sweep functions.
    
    The timebase settings include the mode, scale, position, and range of the oscilloscope's horizontal axis. 
    This class provides a Pythonic interface for getting and setting these properties, with changes being 
    immediately written to the oscilloscope and verified through queries.
    """

    class Mode(Enum):
        MAIN = "MAIN"
        WINDOW = "WIND"
        XY = "XY"
        ROLL = "ROLL"

    class Reference(Enum):
        LEFT = "LEFT"
        CENTER = "CENT"
        XY = "XY"
        ROLL = "ROLL"
        
    def __init__(self, parent):
        super().__init__(parent)
        self._mode = None
        self._scale = None
        self._position = None
        self._range = None
        self._reference = None

    @property
    def mode(self):
        response = self._parent.query(":TIMebase:MODE?").strip()
        self._mode = self.Mode(response)
        logging.debug(f"Timebase mode fetched: {self._mode}")
        return self._mode

    @mode.setter
    def mode(self, value):
        if isinstance(value, self.Mode):
            self._parent.write(f":TIMebase:MODE {value.value}")
            logging.info(f"Timebase mode set to: {value.value}")
            self._mode = value
        else:
            logging.error(f"Invalid timebase mode: {value}")

    @property
    def position(self):
        response = self._parent.query(":TIMebase:POSition?")
        self._position = float(response)
        logging.debug(f"Timebase position fetched: {self._position}")
        return self._position

    @position.setter
    def position(self, value):
        try:
            self._parent.write(f":TIMebase:POSition {value}")
            logging.info(f"Timebase position set to: {value}")
            self._position = float(self._parent.query(":TIMebase:POSition?"))
        except ValueError as e:
            logging.error(f"Error setting timebase position: {e}")

    @property
    def range(self):
        response = self._parent.query(":TIMebase:RANGe?")
        self._range = float(response)
        logging.debug(f"Timebase range fetched: {self._range}")
        return self._range

    @range.setter
    def range(self, value):
        try:
            self._parent.write(f":TIMebase:RANGe {value}")
            logging.info(f"Timebase range set to: {value}")
            self._range = float(self._parent.query(":TIMebase:RANGe?"))
        except ValueError as e:
            logging.error(f"Error setting timebase range: {e}")

    @property
    def reference(self):
        """
        Gets the reference position for the timebase.
        """
        response = self._parent.query(":TIMebase:REFerence?").strip()
        # Here we're gonna map the response to the Reference Enum
        self._reference = self.Reference(response)
        logging.debug(f"Timebase reference fetched: {self._reference}")
        return self._reference

    @reference.setter
    def reference(self, value):
        """
        Sets the reference position for the timebase.
        """
        if isinstance(value, self.Reference):
            self._parent.write(f":TIMebase:REFerence {value.value}")
            logging.info(f"Timebase reference set to: {value.value}")
            # Directly updating the internal state, no need to query again
            self._reference = value
        else:
            logging.error(f"Invalid timebase reference: {value}")
            
    @property
    def scale(self):
        response = self._parent.query(":TIMebase:SCALe?")
        self._scale = float(response)
        logging.debug(f"Timebase scale fetched: {self._scale}")
        return self._scale

    @scale.setter
    def scale(self, value):
        try:
            self._parent.write(f":TIMebase:SCALe {value}")
            logging.info(f"Timebase scale set to: {value}")
            self._scale = float(self._parent.query(":TIMebase:SCALe?"))
        except ValueError as e:
            logging.error(f"Error setting timebase scale: {e}")

    def sync(self):
        """ Synchronizes timebase settings with the oscilloscope's current configuration. """
        super().sync()
        logging.info("Synchronized timebase settings with oscilloscope.")
