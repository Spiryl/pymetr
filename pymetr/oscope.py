from instrument import Instrument, Subsystem
from properties import switch_property, select_property, value_property, data_property
from enum import Enum
import numpy as np
import logging

# Set up logging
logger = logging.getLogger(__name__)

class Acquire(Subsystem):
    """
    Manages the acquisition settings of an oscilloscope or similar instrument.
    """
    Modes = Enum('Modes', 'RTIMe SEGMmented')
    Types = Enum('Types', 'NORMal AVERage HRESolution PEAK')

    mode = select_property(":MODE", Modes, "Acquisition mode")
    type = select_property(":TYPE", Types, "Acquisition type")
    sample_rate = value_property(":SRATe", doc_str="Sample rate in samples per second [S/s]")
    count = value_property(":COUNt", doc_str="Number of acquisitions to combine [n]")

    def __init__(self, parent):
        super().__init__(parent, ":ACQuire")

class Channel(Subsystem):
    """
    Represents a single channel on an oscilloscope or similar instrument.
    """
    Couplings = Enum('Couplings', 'AC DC')

    display = switch_property(":DISPlay", "Display state of the channel")
    coupling = select_property(":COUPling", Couplings, "Coupling mode of the channel")
    scale = value_property(":SCALe", doc_str="Vertical scale of the channel [V/div]")
    offset = value_property(":OFFset", doc_str="Vertical offset of the channel [V]")
    probe_attenuation = value_property(":PROBe", doc_str="Probe attenuation factor [n]")

    def __init__(self, parent, channel_number=1):
        super().__init__(parent, f":CHAN{channel_number}")
        self.channel_number = channel_number

class Timebase(Subsystem):
    """
    Controls the timebase settings of an oscilloscope.
    """
    Modes = Enum('Modes', 'MAIN WIND XY ROLL')
    References = Enum('References', 'LEFT CENTer RIGHT')

    mode = select_property(":MODE", Modes, "Timebase mode")
    reference = select_property(":REFerence", References, "Timebase reference position")
    scale = value_property(":SCALe", doc_str="Timebase scale [s/div]")
    position = value_property(":POSition", doc_str="Timebase position [s]")
    range = value_property(":RANGe", doc_str="Timebase range [s]")

    def __init__(self, parent):
        super().__init__(parent, ":TIMebase")

class Trigger(Subsystem):
    """
    Manages the trigger settings of an oscilloscope or similar instrument.
    """
    Sources = Enum('Sources', 'CHAN1 CHAN2 CHAN3 CHAN4 EXT LINE WGEN')
    Modes = Enum('Modes', 'EDGE GLITch PATTern SHOL')
    Slopes = Enum('Slopes', 'POSitive NEGative')
    Sweeps = Enum('Sweeps', 'AUTO NORMAL')

    mode = select_property(":MODe", Modes, "Trigger mode")
    source = select_property(":SOURce", Sources, "Trigger source")
    slope = select_property(":SLOPe", Slopes, "Trigger slope")
    sweep = select_property(":SWEep", Sweeps, "This controls the sweep mode")
    level = value_property(":LEVel", doc_str="Trigger level [V]")

    def __init__(self, parent):
        super().__init__(parent, ":TRIGger")

class WaveGen(Subsystem):
    """
    Controls the built-in waveform generator (WGEN) of an instrument.
    """
    Functions = Enum('Functions', 'SIN SQUare RAMP PULSe NOISe DC')

    output = switch_property(":OUTP", "Waveform output state")
    function = select_property(":FUNC", Functions, "Waveform function")
    frequency = value_property(":FREQ", doc_str="Waveform frequency [Hz]")
    amplitude = value_property(":VOLT", doc_str="Waveform amplitude [V]")
    offset = value_property(":VOLT:OFFS", doc_str="Waveform offset [V]")

    def __init__(self, parent):
        super().__init__(parent, ":WGEN")

class Waveform(Subsystem):
    """
    Manages waveform data retrieval and configuration settings on an oscilloscope or similar instrument.
    """
    Formats = Enum('Formats', 'ASCII WORD BYTE')
    PointsModes = Enum('PointsModes', 'NORMal MAXiumum RAW')
    Sources = Enum('Sources', 'CHAN1 CHAN2 CHAN3 CHAN4 FUNC MATH FFT WMEM BUS1 BUS2 EXT')

    unsigned = switch_property(":UNSigned", "Indicates if the returned data is signed or unsigned")
    source = select_property(":SOURce", Sources, "Waveform source")
    format = select_property(":FORMat", Formats, "Waveform data format")
    points_mode = select_property(":POINts:MODE", PointsModes, "Waveform points mode")
    points = value_property(":POINts", doc_str="Number of trace points to pull")
    preamble = data_property(":PREamble", access='read', doc_str="Pre-amble info including scale factors and offsets.")
    data = data_property(":DATa", access='read', ieee_header=True, doc_str="Returns the data array of the waveform as a numpy array.")

    def __init__(self, parent):
        super().__init__(parent, ":WAVeform")
        self.x_increment = 1.0
        self.x_origin = 0.0
        self.x_reference = 0
        self.y_increment = 1.0
        self.y_origin = 0.0
        self.y_reference = 0
        self.num_points = 0

    def fetch_preamble(self):
        """
        Fetches and parses the preamble from the instrument, updating class attributes for waveform scaling.
        """
        try:
            preamble_str = self.preamble  # Utilizes the getter from the value_property
            preamble_values = [float(val) for val in preamble_str.split(',')]

            self.format = preamble_values[0]
            # self.type is not used here, assuming a typo or legacy. If it's needed, consider adding it properly.
            self.num_points = int(preamble_values[2])
            # Count is not directly used here, assuming part of legacy or specific logic not shown.
            self.x_increment, self.x_origin, self.x_reference = preamble_values[4], preamble_values[5], int(preamble_values[6])
            self.y_increment, self.y_origin, self.y_reference = preamble_values[7], preamble_values[8], int(preamble_values[9])
        except Exception as e:
            logger.error(f'Issue fetching preamble: {e}')

    def fetch_time(self):
        """
        Calculates and returns the time array for the waveform data based on preamble info.
        """
        self.fetch_preamble()
        timestamps = (np.arange(self.num_points) - self.x_reference) * self.x_increment + self.x_origin
        return timestamps

    def fetch_data(self, source=None):
        """
        Fetches and returns waveform data in voltage units, performing necessary conversions based on format.
        """
        if source:
            self.source = source

        self.fetch_preamble()
        
        if self.format in ["BYTE", "WORD"]:
            data_type = 'B' if self.unsigned else 'b'  # Adjust for BYTE
            if self.format == "WORD":
                data_type = 'H' if self.unsigned else 'h'  # Adjust for WORD
            self._parent.data_type = data_type

        waveform_data = self.data  # Fetch waveform data

        if self.format in ["BYTE", "WORD"]:
            voltages = (waveform_data - self.y_reference) * self.y_increment + self.y_origin
        else:  # ASCII or other formats not requiring conversion
            voltages = waveform_data

        return voltages
