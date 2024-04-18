<<<<<<< HEAD
import logging
from enum import Enum
from collections.abc import Iterable
import numpy as np
logger = logging.getLogger(__name__)
from pymetr import Instrument, Subsystem, switch_property, select_property, value_property, string_property, data_property


def source_command(command_template):
    """
    A decorator to handle oscilloscope source-related commands. It determines the correct sources
    to use (provided or global), converts Enum members to strings, generates the SCPI command,
    and executes it.

    Args:
        command_template (str): A template string for the SCPI command, with '{}' placeholder for source(s).

    Returns:
        A decorated function.
    """
    def decorator(func):
        def wrapper(self, *sources, **kwargs):
            # Check if sources is provided and not empty, otherwise use global sources or default to an empty list
            if sources:
                sources_to_use = sources
            else:
                sources_to_use = self._sources if self._sources else []

            # Ensure sources_to_use is iterable and not a single enum item
            if isinstance(sources_to_use, Enum):
                sources_to_use = [sources_to_use]
            elif not isinstance(sources_to_use, Iterable) or isinstance(sources_to_use, str):
                sources_to_use = [sources_to_use]

            # Convert Enums to their string values if necessary
            cleaned_sources = [source.value if isinstance(source, Enum) else source for source in sources_to_use]

            # Generate and execute the SCPI command
            command = command_template.format(', '.join(cleaned_sources))
            logger.debug(f"Executing command: {command}")
            self.write(command)

            # Call the original function with the cleaned source strings
            return func(self, *cleaned_sources, **kwargs)

        return wrapper
    return decorator
=======

import numpy as np
from pymetr.core import Instrument, Subsystem, Sources, Trace
from pymetr.properties import SwitchProperty, SelectProperty, ValueProperty, DataProperty, DataBlockProperty
>>>>>>> in_progress

class Oscilloscope(Instrument):
    def __init__(self, resource_string):
        super().__init__(resource_string)

        self._format = "BYTE" # Global data format for all channels
        self.sources = Sources(['CHAN1', 'CHAN2', 'CHAN3', 'CHAN4'])
        self.sources.source = ["CHAN1"]

        self.waveform = Waveform.build(self, ':WAVeform')
        self.trigger = Trigger.build(self, ':TRIGger')
        self.timebase = Timebase.build(self, ':TIMebase')
        self.wavegen = WaveGen.build(self, ':WGEN')
        self.acquire = Acquire.build(self, ':ACQuire')
        self.channel = Channel.build(self, ':CHANnel', indices=4)

    # Waveform.format must be set for each data source 
    # we keep a global setting and pull it in fetch data method
    @property
    def format(self):
        return self._format

    @format.setter
    def format(self, format):
        if format in ["ASCII", "BYTE", "WORD"]:
            self._format = format
        else:
            raise ValueError("Invalid data format. Must be 'ASCII', 'BYTE', or 'WORD'.")

# --- Methods ------------------------------------------------------------------------------

    # The source command decorator looks at the list of the instruments active sources
    # and adds them as parameter arguments for commands which accept a list of sources.
    # This allows the function to be passed with arguments of called from a GUI button
    # based on a list of active sources.
    @Sources.source_command(":AUTOScale {}")
    def autoscale(self, *sources):
        pass

    def run(self): # Start continuous
        self.write(":RUN")

    def stop(self): # Stop continuous trigger
        self.write(":STOP")

    def single(self): # Single trigger
        self.write(":SINGLE")

    def fetch_time(self, source=None):
        if source:
            self.waveform.source = source

        try: # The preamble data includes all of the information needed to built the voltages and timescales from the raw data.
            _preamble = self.waveform.preamble
            self._x_increment, self._x_origin, self._x_reference = _preamble[4], _preamble[5], int(_preamble[6])
            self._y_increment, self._y_origin, self._y_reference = _preamble[7], _preamble[8], int(_preamble[9])
            self.waveform.format = self._format
            timestamps = (np.arange(self.waveform.points) - self._x_reference) * self._x_increment + self._x_origin
            return timestamps
        except Exception as e:
            raise ValueError(f'Issue fetching or parsing preamble: {e}')

    def fetch_data(self, source=None):
        if source:
            self.waveform.source = source

        # This section is mostly just to support for all oscope data format
        self.waveform.format = self.format
        unsigned = self.waveform.unsigned

        # Binary data formats based on waveform format settings
        data_type_map = { 
            "BYTE": 'B' if unsigned else 'b',
            "WORD": 'H' if unsigned else 'h',
            "ASCII": None
        }
        data_type = data_type_map.get(self._format)

        # Instrument data type and mode attributes need to be configured before reading binary data properties
        self.data_type = data_type if data_type else 'B'
        self.data_mode = "ASCII" if self._format == "ASCII" else "BINARY"
        
        # Ready the data property
        waveform_data = self.waveform.data

        # Binary data needs to be converted from dac values to voltages
        if self._format in ["BYTE", "WORD"]:
            voltages = (waveform_data - self._y_reference) * self._y_increment + self._y_origin
        elif self._format == "ASCII":
            voltages = waveform_data
        else:
            raise ValueError(f"Unsupported data format: {self.format}")
<<<<<<< HEAD
        if self._format in ["WORD"]:
            voltages = voltages
=======

>>>>>>> in_progress
        return voltages
    
    # Trace thread is a special decorator for the abstract method 
    # fetch_trace to handle in a separate thread and emit the trace_data_ready_signal
    # with the traces list returned by this method. 
    @Instrument.trace_thread
    @Sources.source_command(":DIGitize {}")
    def fetch_trace(self, *sources):
        self.query_operation_complete()  # let it digitize

<<<<<<< HEAD
    def fetch_trace(self):
        """
        Fetches trace data from the oscilloscope, utilizing global settings for sources
        and data format if set; otherwise, defaults to fetching from displayed channels.
        """
        trace_data_dict = {}
        
        # Ensure self._sources is iterable (even if it's a single source) or find which channels are displayed
        if isinstance(self._sources, Enum):
            sources_to_fetch = [self._sources]
        elif not self._sources:
            # Fetch from displayed channels by default
            sources_to_fetch = [
                self.Sources(f"CHAN{num}") for num in range(1, 5) if getattr(self.channel[num-1], 'display', False)
            ]
        else:
            sources_to_fetch = self._sources

        if not sources_to_fetch:
            logger.warning("No sources specified for fetching traces, and no channels marked as displayed.")
            return trace_data_dict

        logger.info(f"Fetching traces for sources: {', '.join(str(source) for source in sources_to_fetch)}")
=======
        if not sources:
            sources = self.sources.source
>>>>>>> in_progress

        traces = []
        for source in sources:
            time = self.fetch_time(source)
            data = self.fetch_data(source)
            trace_data = Trace(data, x_data=time, label=source)
            print(f"*** Fetched trace data for source {source}: {trace_data} ***")
            traces.append(trace_data)

<<<<<<< HEAD
        for source in sources_to_fetch:
            # Ensure source is passed as a string to fetch_time and fetch_data
            source_str = str(source)
            data_range = self.fetch_time(source_str)  # Fetches time base for the source
            data_values = self.fetch_data(source_str)  # Fetches waveform data adjusted for probe attenuation
            
            trace_data_dict[source_str] = {
                'data': data_values,
                'range': data_range,
                'visible': True,  # Adjust based on your implementation or the channel's display attribute
            }
        
        self.trace_data_ready.emit(trace_data_dict)  # Emit the trace data for the GUI
        return trace_data_dict  # This is for using a script

class Acquire(Subsystem):
    """
    Manages the acquisition settings of an oscilloscope or similar instrument.
    """
    mode = select_property(":MODE", ['RTIMe', 'SEGMmented'], "Acquisition mode")
    type = select_property(":TYPE", ['NORMal', 'AVERage', 'HRESolution', 'PEAK'], "Acquisition type")
    sample_rate = value_property(":SRATe", type="float", range=[0.1, 1e9], doc_str="Sample rate in samples per second [S/s]")
    count = value_property(":COUNt", type="int", range=[1, 10000], doc_str="Number of acquisitions to combine [n]")
=======
        return traces
    
# --- Subsystems -----------------------------------------------------------------------------------
    
class Acquire(Subsystem):#
    mode = SelectProperty(":MODE", ['RTIMe', 'SEGMmented'], "Acquisition mode")
    type = SelectProperty(":TYPE", ['NORMal', 'AVERage', 'HRESolution', 'PEAK'], "Acquisition type")
    sample_rate = ValueProperty(":SRATe", type="float", range=[0.1, 1e9], units="S/s", doc_str="Sample rate in samples per second")
    count = ValueProperty(":COUNt", type="int", range=[1, 10000], doc_str="Number of acquisitions to combine")
>>>>>>> in_progress

class Channel(Subsystem):
    coupling = SelectProperty(":COUPling", ['AC', 'DC'], "Coupling mode of the channel")
    display = SwitchProperty(":DISPlay", "Display state of the channel")
    scale = ValueProperty(":SCALe", type="float", range=[1e-3, 1e3], units="V", doc_str="Vertical scale of the channel")
    offset = ValueProperty(":OFFset", type="float", range=[-1e2, 1e2], units="V", doc_str="Vertical offset of the channel")
    probe = ValueProperty(":PROBe", type="float", doc_str="Probe attenuation factor")

class Timebase(Subsystem):
    mode = SelectProperty(":MODE", ['MAIN', 'WIND', 'XY', 'ROLL'], "Timebase mode")
    reference = SelectProperty(":REFerence", ['LEFT', 'CENTer', 'RIGHT'], "Timebase reference position")
    scale = ValueProperty(":SCALe", type="float", range=[1e-9, 1e0], units="s", doc_str="Timebase scale")
    position = ValueProperty(":POSition", type="float", range=[-5e0, 5e0], units="s", doc_str="Timebase position")
    range = ValueProperty(":RANGe", type="float", range=[2e-9, 50e0], units="s", doc_str="Timebase range")

class Trigger(Subsystem):
    mode = SelectProperty(":MODe", ['EDGE', 'GLITch', 'PATTern', 'SHOL', 'NONE'], "Trigger mode")
    source = SelectProperty(":SOURce", ['CHAN1', 'CHAN2', 'CHAN3', 'CHAN4', 'EXT', 'LINE', 'WGEN'], "Trigger source")
    slope = SelectProperty(":SLOPe", ['POSitive', 'NEGative'], "Trigger slope")
    sweep = SelectProperty(":SWEep", ['AUTO', 'NORMAL'], "Sweep mode")
    level = ValueProperty(":LEVel", type="float", range=[-5e0, 5e0], units="V", doc_str="Trigger level")

class WaveGen(Subsystem):
    function = SelectProperty(":FUNC", ['SIN', 'SQUare', 'RAMP', 'PULSe', 'NOISe', 'DC'], "Waveform function")
    output = SwitchProperty(":OUTP", "Waveform output state")
    frequency = ValueProperty(":FREQ", type="float", range=[1e-3, 1e8], units="Hz", doc_str="Waveform frequency")
    amplitude = ValueProperty(":VOLT", type="float", range=[1e-3, 10e0], units="V", doc_str="Waveform amplitude")
    offset = ValueProperty(":VOLT:OFFS", type="float", range=[-5e0, 5e0], units="V", doc_str="Waveform offset")

class Waveform(Subsystem):
    source = SelectProperty(":SOURce", ['CHAN1', 'CHAN2', 'CHAN3', 'CHAN4', 'FUNC', 'MATH', 'FFT', 'WMEM', 'BUS1', 'BUS2', 'EXT'], "Waveform source")
    format = SelectProperty(":FORMat", ['ASCII', 'WORD', 'BYTE'], "Waveform data format")
    points_mode = SelectProperty(":POINts:MODE", ['NORMal', 'MAXiumum', 'RAW'], "Waveform points mode")
    byte_order = SelectProperty(":BYTeorder", ['LSBFirst', 'MSBFirst'], "Byte order for 16 bit data capture")
    unsigned = SwitchProperty(":UNSigned", "Indicates if the returned data is signed or unsigned")
    points = ValueProperty(":POINts", type="int", access='write', doc_str="Number of trace points to pull")
    x_increment = DataProperty(":XINCrement", doc_str="Waveform X increment")
    x_origin = DataProperty(":XORigin", doc_str="Waveform X origin")
    x_reference = DataProperty(":XREFerence", doc_str="Waveform X reference point")
    y_increment = DataProperty(":YINCrement", doc_str="Waveform Y increment")
    y_origin = DataProperty(":YORigin", doc_str="Waveform Y origin")
    y_reference = DataProperty(":YREFerence", doc_str="Waveform Y reference point")
    preamble = DataProperty(":PREamble", access='read', doc_str="Preamble info including scale factors and offsets.")
    data = DataBlockProperty(":DATa", access='read', ieee_header=True, doc_str="Returns the data array of the waveform as a numpy array.")