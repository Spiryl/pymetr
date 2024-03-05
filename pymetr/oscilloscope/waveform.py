import logging
from enum import Enum
from pymetr.instruments import InstrumentSubsystem
import numpy as np  # Make sure to import numpy for handling the data

class Waveform(InstrumentSubsystem):
    """
    Manages waveform data acquisition and processing for an oscilloscope channel.
    """

    class Format(Enum):
        ASCII = 'ASC'
        WORD = 'WORD'
        BYTE = 'BYTE'

    class PointsMode(Enum):
        NORMAL = 'NORM'
        MAXIMUM = 'MAX'
        RAW = 'RAW'

    class Source(Enum):
        CHANNEL = "CHAN"
        FUNCTION = "FUNC"
        MATH = "MATH"
        FFT = "FFT"
        WMEM = "WMEM"  # For waveform memory
        BUS1 = "BUS1"
        BUS2 = "BUS2"
        EXT = "EXT"  # External, only for 2-channel oscilloscopes

    def __init__(self, parent):
        super().__init__(parent)
        self._source = self.Source.CHANNEL.value + '1'  # Default to CHANNEL1
        self._format = self.Format.ASCII  # Default format
        self._points_mode = self.PointsMode.NORMAL  # Default points mode
        self._num_points = 500  # Default number of points
        self.x_increment = 1.0
        self.x_origin = 0.0
        self.y_increment = 1.0
        self.y_origin = 0.0
        self.y_reference = 0
        self.is_data_unsigned = False

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        if isinstance(value, int):
            # Assuming the integer value is for the analog channel source
            self._source = f"{self.Source.CHANNEL.value}{value}"
        elif isinstance(value, self.Source):
            self._source = value.value
        else:
            logging.error(f"Invalid source setting: {value}")

        self._parent.write(f":WAVeform:SOURce {self._source}")
        logging.info(f"Waveform source set to: {self._source}")

    @property
    def format(self):
        response = self._parent.query(":WAVeform:FORMat?")
        self._format = self.Format(response.strip())
        return self._format.name

    @format.setter
    def format(self, value):
        if value in self.Format.__members__:
            self._parent.write(f":WAVeform:FORMat {self.Format[value].value}")
            self._format = self.Format[value]
        else:
            logging.error(f"Invalid format: {value}")

    @property
    def points_mode(self):
        response = self._parent.query(":WAVeform:POINts:MODE?")
        self._points_mode = self.PointsMode(response.strip())
        return self._points_mode.name

    @points_mode.setter
    def points_mode(self, value):
        if value in self.PointsMode.__members__:
            self._parent.write(f":WAVeform:POINts:MODE {self.PointsMode[value].value}")
            self._points_mode = self.PointsMode[value]
        else:
            logging.error(f"Invalid points mode: {value}")

    @property
    def num_points(self):
        response = self._parent.query(":WAVeform:POINts?")
        self._num_points = int(response)
        return self._num_points

    @num_points.setter
    def num_points(self, value):
        self._parent.write(f":WAVeform:POINts {value}")
        self._num_points = value

    def sync(self):
        super().sync()
        logging.info("Synchronized waveform settings with oscilloscope.")

    def setup_trace(self, channel=1, points_mode="NORMAL", num_points=500, data_format='ASCII'):
        # Map the numeric channel input to the appropriate source string
        self.source = channel  # This will use the source setter

        self.points_mode = self.PointsMode[points_mode].name if points_mode in self.PointsMode.__members__ else "NORMAL"
        self.num_points = num_points
        self.format = self.Format[data_format].name if data_format in self.Format.__members__ else "BYTE"

        logging.info(f"Trace setup: Channel {channel}, Points mode {points_mode}, Number of points {num_points}, Data format {data_format}")

    def fetch_preamble(self, return_type='dict'):
        """
        Fetches the preamble information from the oscilloscope.

        :param return_type: Specifies the return type. 'dict' returns a dictionary,
                            anything else returns the raw string response.
        :return: Depending on return_type, either a dictionary with preamble values or a raw string.
        """
        try:
            preamble_str = self._parent.query(":WAVeform:PREamble?")
            preamble_values = preamble_str.split(',')

            self._num_points = int(preamble_values[2])
            self.x_increment = float(preamble_values[4])
            self.x_origin = float(preamble_values[5])
            self.y_increment = float(preamble_values[7])
            self.y_origin = float(preamble_values[8])
            self.y_reference = int(preamble_values[9])
            self.is_data_unsigned = bool(int(self._parent.query(":WAVeform:UNSigned?")))

            logging.debug(f"Preamble values: {preamble_values}")
            logging.debug(f"Number of points: {self._num_points}")
            logging.debug(f"X increment: {self.x_increment}")
            logging.debug(f"X origin: {self.x_origin}")  # Logging x_origin
            logging.debug(f"Y increment: {self.y_increment}")
            logging.debug(f"Y origin: {self.y_origin}")  # Logging y_origin
            logging.debug(f"Y reference: {self.y_reference}")  # Logging y_reference
            logging.debug(f"Data is unsigned: {self.is_data_unsigned}")

            # Prepare the dictionary if requested
            if return_type == 'dict':
                preamble_dict = {
                    'num_points': self._num_points,
                    'x_increment': self.x_increment,
                    'x_origin': self.x_origin,
                    'y_increment': self.y_increment,
                    'y_origin': self.y_origin,
                    'y_reference': self.y_reference,
                    'is_data_unsigned': self.is_data_unsigned,
                }
                return preamble_dict

            # Default to returning the raw string if return_type is not 'dict'
            return preamble_str

        except Exception as e:
            logging.error(f'Had an issue with preamble: {e}')
            return {} if return_type == 'dict' else ""  # Return an empty dict or string on error

    def fetch_trace(self, channel):
        """
        Fetches the waveform trace from the specified channel, automatically adjusting to the
        data format (ASCII, BYTE, WORD) for optimal data retrieval and processing.

        Parameters:
            channel (int): The oscilloscope channel to fetch the waveform from.

        Returns:
            np.ndarray: The waveform data as voltages, adjusted based on the oscilloscope's preamble settings.
        """
        self.fetch_preamble()  # Ensure preamble settings are up to date
        if self._format == self.Format.BYTE:
            data = self._fetch_binary_trace()
        elif self._format == self.Format.WORD:
            data = self._fetch_binary_trace(datatype='h')  # 'h' for signed 2-byte integer
        elif self._format == self.Format.ASCII:
            data = self._fetch_ascii_trace()
        else:
            logging.error("Unsupported data format: {}".format(self._format))
            return np.array([])  # Return an empty array if format is unsupported

        # Convert binary data to voltage values if necessary
        if self._format in [self.Format.BYTE, self.Format.WORD]:
            data = (data - self.y_reference) * self.y_increment + self.y_origin
        
        return data

    def _fetch_binary_trace(self, datatype='b'):
        """
        Fetches binary waveform data from the oscilloscope and interprets it according to the specified datatype.

        Parameters:
            datatype (str): The datatype to interpret the binary data as. Defaults to 'b' (signed byte).

        Returns:
            np.ndarray: The waveform data as raw binary values.
        """
        command = ":WAVeform:DATA?"
        try:
            raw_data = self._parent.query_binary(command, datatype=datatype, is_big_endian=False)
            return np.array(raw_data, dtype=datatype)
        except Exception as e:
            logging.error(f"Failed to fetch or interpret binary data: {e}")
            return np.array([])  # Return an empty array in case of error

    def _fetch_ascii_trace(self):
        """
        Fetches ASCII waveform data from the oscilloscope and converts it to a numpy array.

        Returns:
            np.ndarray: The waveform data as a numpy array of floats.
        """
        command = ":WAVeform:DATA?"
        try:
            ascii_data = self._parent.query(command).strip()
            # Convert ASCII data to a numpy array of floats
            data_array = np.fromstring(ascii_data, sep=',', dtype=float)
            return data_array
        except Exception as e:
            logging.error(f"Error parsing ASCII data: {e}")
            return np.array([])  # Return an empty array in case of error