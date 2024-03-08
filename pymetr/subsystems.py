
from pymetr.subsystem import Subsystem, command_property, command_options

class Acquire(Subsystem):
    """
    Manages the acquisition settings of an oscilloscope or similar instrument, allowing control over the mode, type,
    sample rate, depth, and count of acquisitions. This subsystem simplifies interaction with the device's acquisition
    parameters, providing a high-level interface to configure and retrieve acquisition settings.
    """
    Mode = command_options('Mode', ['RTIM', 'SEGM'])
    Type = command_options('Type', ['NORMAL', 'AVERAGE', 'HRES', 'PEAK'])

    mode = command_property("ACQuire:MODE", Mode, "Acquisition mode")
    type = command_property("ACQuire:TYPE", Type, "Acquisition type")
    sample_rate = command_property("ACQuire:SRATe", doc_str="Sample rate in samples per second")
    depth = command_property("ACQuire:DEPTh", doc_str="Depth of the acquisition")
    count = command_property("ACQuire:COUNT", doc_str="Number of acquisitions to combine")

    def __init__(self, parent):
        super().__init__(parent, ":ACQuire")

class Channel(Subsystem):
    """
    Represents a single channel on an oscilloscope or similar instrument, providing control over display state,
    vertical scale and offset, coupling mode, and probe attenuation factor. This class allows for fine-tuned control
    of each channel's visual and electrical input characteristics.
    """
    DisplayState = command_options('DisplayState', ['1', '0'])
    Coupling = command_options('Coupling', ['AC', 'DC'])

    def __init__(self, parent, channel_number):
        super().__init__(parent, f":CHAN{channel_number}")
        self.channel_number = channel_number

    display = command_property(":DISPlay", DisplayState, "Display state of the channel")
    scale = command_property(":SCALe", doc_str="Vertical scale of the channel")
    offset = command_property(":OFFset", doc_str="Vertical offset of the channel")
    coupling = command_property(":COUPling", Coupling, "Coupling mode of the channel")
    probe_attenuation = command_property(":PROBe", doc_str="Probe attenuation factor")

class Timebase(Subsystem):
    """
    Controls the timebase settings of an oscilloscope, including mode, reference position, scale, position,
    and range. This subsystem is essential for adjusting how waveform data is displayed over time, affecting
    the horizontal scale and positioning of waveforms on the screen.
    """
    Mode = command_options('Mode', ['MAIN', 'WIND', 'XY', 'ROLL'])
    Reference = command_options('Reference', ['LEFT', 'CENT', 'RIGHT'])

    mode = command_property(":MODE", Mode, "Timebase mode")
    reference = command_property(":REFerence", Reference, "Timebase reference position")
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
    Source = command_options('Source', ['CH1', 'CH2', 'CH3', 'CH4', 'EXT', 'LINE', 'WGEN'])
    Mode = command_options('Mode', ['EDGE', 'VIDEO'])
    Slope = command_options('Slope', ['POSITIVE', 'NEGATIVE'])

    mode = command_property(":MODE", Mode, "Trigger mode")
    source = command_property(":SOURCE", Source, "Trigger source")
    level = command_property(":LEVel", doc_str="Trigger level")
    slope = command_property(":SLOPe", Slope, "Trigger slope")

    def __init__(self, parent):
        super().__init__(parent, "TRIGger")

class WaveGen(Subsystem):
    """
    Controls the built-in waveform generator (WGEN) of an instrument, managing output waveform function, frequency,
    amplitude, output state, and offset. This subsystem facilitates the generation of various waveform types for
    testing and analysis purposes.
    """
    # Nested enums for clean namespace and easy access
    Functions = command_options('Functions', ['SIN', 'SQU', 'RAMP', 'PULSE', 'NOISE', 'DC'])
    OutputState = command_options('OutputState', ['ON', 'OFF'])

    # Updated property definitions without redundant ":WGEN" prefix
    function = command_property(":FUNC", Functions, "Waveform function")
    frequency = command_property(":FREQ", doc_str="Waveform frequency")
    amplitude = command_property(":VOLT", doc_str="Waveform amplitude")
    output = command_property(":OUTP", OutputState, "Waveform output state")
    offset = command_property(":VOLT:OFFS", doc_str="Waveform offset")

    def __init__(self, parent):
        super().__init__(parent, ":WGEN")

class Waveform(Subsystem):
    """
    Manages waveform data retrieval and configuration settings on an oscilloscope or similar instrument. It provides
    control over the waveform source, data format, points mode, and allows querying of waveform data. This subsystem
    is key for analyzing captured signal data in different formats and resolutions.
    """
    Format = command_options('Format', ['ASCII', 'WORD', 'BYTE'])
    PointsMode = command_options('PointsMode', ['NORMAL', 'MAXIMUM', 'RAW'])
    Source = command_options('Source', ['CHANNEL1', 'FUNCTION', 'MATH', 'FFT', 'WMEM', 'BUS1', 'BUS2', 'EXT'])

    def __init__(self, parent):
        super().__init__(parent, ":WAVe")
        self._num_points = 500  # Default number of points
        self.x_increment = 1.0
        self.x_origin = 0.0
        self.y_increment = 1.0
        self.y_origin = 0.0
        self.y_reference = 0
        self.is_data_unsigned = False

    source = command_property(":SOURce", Source, "Waveform source")
    format = command_property(":FORMat", Format, "Waveform data format")
    points_mode = command_property(":POINts:MODE", PointsMode, "Waveform points mode")
    data = command_property(":DATa", "Waveform data", read_only='True')