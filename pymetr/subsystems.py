# subsystems.py 
from pymetr.subsystem import Subsystem, command_property, Enum, data_property
import numpy as np

class Acquire(Subsystem):
    """
    Manages the acquisition settings of an oscilloscope or similar instrument, allowing control over the mode, type,
    sample rate, depth, and count of acquisitions. This subsystem simplifies interaction with the device's acquisition
    parameters, providing a high-level interface to configure and retrieve acquisition settings.
    """
    Modes = Enum('Modes', ['RTIM', 'SEGM'])
    Types = Enum('Types', ['NORMAL', 'AVERAGE', 'HRES', 'PEAK'])

    mode = command_property(":MODE", Modes, "Acquisition mode")
    type = command_property(":TYPE", Types, "Acquisition type")
    sample_rate = command_property(":SRATe", doc_str="Sample rate in samples per second")
    depth = command_property(":DEPTh", doc_str="Depth of the acquisition")
    count = command_property(":COUNt", doc_str="Number of acquisitions to combine")

    def __init__(self, parent):
        super().__init__(parent, ":ACQuire")

class Channel(Subsystem):
    """
    Represents a single channel on an oscilloscope or similar instrument, providing control over display state,
    vertical scale and offset, coupling mode, and probe attenuation factor. This class allows for fine-tuned control
    of each channel's visual and electrical input characteristics.
    """
    DisplayStates = Enum('DisplayStates', ['1', '0', 'On', 'Off', 'ON', 'OFF'])
    Couplings = Enum('Couplings', ['AC', 'DC'])

    display = command_property(":DISPlay", DisplayStates, "Display state of the channel")
    scale = command_property(":SCALe", doc_str="Vertical scale of the channel")
    offset = command_property(":OFFset", doc_str="Vertical offset of the channel")
    coupling = command_property(":COUPling", Couplings, "Coupling mode of the channel")
    probe_attenuation = command_property(":PROBe", doc_str="Probe attenuation factor")

    def __init__(self, parent, channel_number):
        super().__init__(parent, f":CHAN{channel_number}")
        self.channel_number = channel_number

class Timebase(Subsystem):
    """
    Controls the timebase settings of an oscilloscope, including mode, reference position, scale, position,
    and range. This subsystem is essential for adjusting how waveform data is displayed over time, affecting
    the horizontal scale and positioning of waveforms on the screen.
    """
    Modes = Enum('Modes', ['MAIN', 'WIND', 'XY', 'ROLL'])
    References = Enum('References', ['LEFT', 'CENT', 'RIGHT'])

    mode = command_property(":MODE", Modes, "Timebase mode")
    reference = command_property(":REFerence", References, "Timebase reference position")
    scale = command_property(":SCALe", doc_str="Timebase scale")
    position = command_property(":POSition", doc_str="Timebase position")
    range = command_property(":RANGe", doc_str="Timebase range")

    def __init__(self, parent):
        super().__init__(parent, ":TIMebase")

class Trigger(Subsystem):
    """
    Manages the trigger settings of an oscilloscope or similar instrument, allowing configuration of trigger
    mode, source, level, and slope. This subsystem is crucial for setting up how and when the instrument starts
    capturing data, based on specific signal conditions.
    """
    Sources = Enum('Sources', ['CHAN1', 'CHAN2', 'CHAN3', 'CHAN4', 'EXT', 'LINE', 'WGEN'])
    Modes = Enum('Modes', ['EDGE', 'GLITCH', 'PATTERN', 'SHOL'])
    Slopes = Enum('Slopes', ['POSITIVE', 'NEGATIVE'])
    Sweeps = Enum('Sweeps', ['AUTO', 'NORMAL'])

    mode = command_property(":MODe", Modes, "Trigger mode")
    source = command_property(":SOURce", Sources, "Trigger source")
    level = command_property(":LEVel", doc_str="Trigger level")
    slope = command_property(":SLOPe", Slopes, "Trigger slope")
    sweep = command_property(":SWEep", Sweeps, doc_str="This controls the sweep mode")

    def __init__(self, parent):
        super().__init__(parent, ":TRIGger")

class WaveGen(Subsystem):
    """
    Controls the built-in waveform generator (WGEN) of an instrument, managing output waveform function, frequency,
    amplitude, output state, and offset. This subsystem facilitates the generation of various waveform types for
    testing and analysis purposes.
    """
    # Nested enums for clean namespace and easy access
    Functions = Enum('Functions', ['SIN', 'SQU', 'RAMP', 'PULSE', 'NOISE', 'DC'])
    OutputStates = Enum('OutputState', ['ON', 'OFF', '1', '0', 'On', 'Off'])

    # Updated property definitions without redundant ":WGEN" prefix
    function = command_property(":FUNC", Functions, "Waveform function")
    frequency = command_property(":FREQ", doc_str="Waveform frequency")
    amplitude = command_property(":VOLT", doc_str="Waveform amplitude")
    output = command_property(":OUTP", OutputStates, "Waveform output state")
    offset = command_property(":VOLT:OFFS", doc_str="Waveform offset")

    def __init__(self, parent):
        super().__init__(parent, ":WGEN")

class Waveform(Subsystem):
    """
    Manages waveform data retrieval and configuration settings on an oscilloscope or similar instrument. It provides
    control over the waveform source, data format, points mode, and allows querying of waveform data. This subsystem
    is key for analyzing captured signal data in different formats and resolutions.
    TODO: 'WORD' not working properly yet. argg.
    """
    Formats = Enum('Formats', ['ASCII', 'WORD', 'BYTE'])
    PointsModes = Enum('PointsModes', ['NORMAL', 'MAXIMUM', 'RAW'])
    Sources = Enum('Sources', ['CHAN1', 'CHAN2','CHAN3','CHAN4','FUNC', 'MATH', 'FFT', 'WMEM', 'BUS1', 'BUS2', 'EXT'])
    # add Types

    source = command_property(":SOURce", Sources, "Waveform source")
    format = command_property(":FORMat", Formats, "Waveform data format")
    points_mode = command_property(":POINts:MODE", PointsModes, "Waveform points mode")
    points = command_property(":POINts", doc_str="Number of trace points to pull")
    preamble = command_property(":PREamble", access='read')
    unsigned = command_property(":UNSigned", doc_str="This parameter indicated if the returned data is signed or unsigned")

    # Assuming your Instrument class and data_property are correctly set up to handle dynamic data fetching
    data = data_property(":DATa", access='read', ieee_header=True, doc_str="This returns the data array of the waveform as a numpy array.")

    def __init__(self, parent):
        super().__init__(parent, ":WAVeform")
        self.x_increment = 1.0
        self.x_origin = 0.0
        self.x_reference = 0
        self.y_increment = 1.0
        self.y_origin = 0.0
        self.y_reference = 0
        self.num_points = 0

    # Special method to 
    def fetch_preamble(self):
        try:
            preamble_str = self.preamble
            preamble_values = preamble_str.split(',')

            # Assign the parsed preamble values to the relevant attributes
            self._format = int(preamble_values[0])
            self._type = int(preamble_values[1])
            self.num_points = int(preamble_values[2])
            self.count = int(preamble_values[3])
            self.x_increment = float(preamble_values[4])
            self.x_origin = float(preamble_values[5])
            self.x_reference = int(preamble_values[6])  # Added x_reference here
            self.y_increment = float(preamble_values[7])
            self.y_origin = float(preamble_values[8])
            self.y_reference = int(preamble_values[9])

        except Exception as e:
            print(f'Had an issue with preamble: {e}')

    def fetch_time(self):
        self.fetch_preamble()
        timestamps = (np.arange(self.num_points) - self.x_reference) * self.x_increment + self.x_origin
        return timestamps

    def fetch_data(self, source=None):
        
        # Set up the source.
        if source is not None:
            self.source = source

        # Lets just do this here to make it easier on the user.
        self.fetch_preamble()

        # Fetch the format once and store it in a temp variable for repeated checks
        _format = self.format
        
        # Set the data type based on the waveform format before fetching
        if _format == "ASCII":
            # ASCII data handling is direct and doesn't require setting data type
            pass
        elif _format == "BYTE":
            self._parent.data_type = 'B' if self.unsigned else 'b'  # Unsigned or signed byte
        elif _format == "WORD":
            self._parent.data_type = 'H' if self.unsigned else 'h'  # Unsigned or signed 16-bit word
        
        # Fetch waveform data
        waveform_data = self.data
        
        # Process data based on format
        if _format in ["BYTE", "WORD"]:
            # Scale binary data to voltages using numpy for efficiency
            voltages = (waveform_data - self.y_reference) * self.y_increment + self.y_origin
        else:
            # ASCII data assumed to already be in the correct format
            voltages = waveform_data

        return voltages