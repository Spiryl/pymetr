import logging
from collections.abc import Iterable
import numpy as np

logger = logging.getLogger(__name__)
from pymetr import Instrument, Subsystem, SwitchProperty, SelectProperty, ValueProperty, StringProperty, DataProperty, Sources

class Oscilloscope(Instrument):
    """
    Represents an oscilloscope instrument.
    
    Args:
        resource_string (str): VISA resource string for connecting to the oscilloscope.
    """
    def __init__(self, resource_string):
        super().__init__(resource_string)
        logger.info("Initializing Oscilloscope with resource string: %s", resource_string)

        self._format = "ASCII"
        # The following and the init method should work with the class visitor and the code?!
        self.sources = Sources(['CHAN1', 'CHAN2', 'CHAN3', 'CHAN4', 'MATH', 'FFT'])

        # Create subsystem instances
        self.waveform = Waveform.build(self, ':WAVeform')
        self.trigger = Trigger.build(self, ':TRIGger')
        self.timebase = Timebase.build(self, ':TIMebase')
        self.wavegen = WaveGen.build(self, ':WGEN')
        self.acquire = Acquire.build(self, ':ACQuire')
        self.channel = Channel.build(self, ':CHANnel', indices=4)

        # Current default setting
        # self.sources.source = self.waveform.source

    def set_format(self, format):
        if format in ["ASCII", "BYTE", "WORD"]:
            self._format = format
            logger.debug(f"Data format set to {format}")
        else:
            logger.debug("Invalid data format.")

    def set_sources(self, *sources):
        self.sources.source(*sources)
        self.blank()
        self.view(sources)
        self.source_changed.emit(sources)  # Emit the signal when sources change

    @Sources.source_command(":AUTOScale {}")
    def autoscale(self, *sources):
        pass

    @Sources.source_command(":DIGItize {}")
    def digitize(self, *sources):
        pass

    @Sources.source_command(":VIEW {}")
    def view(self, *sources):
        pass

    @Sources.source_command(":BLANK {}")
    def blank(self, *sources):
        pass

    def run(self):
        self.write(":RUN")

    def stop(self):
        self.write(":STOP")

    def single(self):
        self.write(":SINGLE")

    def fetch_preamble(self):
        logger.debug("Attempting to fetch preamble...")
        try:
            preamble_str = self.waveform.preamble
            preamble_values = [float(val) for val in preamble_str.split(',')]
            self._x_increment, self._x_origin, self._x_reference = preamble_values[4], preamble_values[5], int(preamble_values[6])
            self._y_increment, self._y_origin, self._y_reference = preamble_values[7], preamble_values[8], int(preamble_values[9])
        except Exception as e:
            logger.error(f'Issue fetching or parsing preamble: {e}')

    def fetch_time(self, source=None):
        logger.debug(f"Fetching time for source: {source}")
        if source:
            self.waveform.source = source

        self.waveform.format = self._format
        self.fetch_preamble()
        timestamps = (np.arange(self.waveform.points) - self._x_reference) * self._x_increment + self._x_origin
        return timestamps

    def fetch_data(self, source=None):
        """
        Fetches and returns waveform data in voltage units.
        """
        logger.debug(f"Fetching data for source: {source}")
        if source:
            self.waveform.source = source

        self.waveform.format = self._format
        _unsigned = self.waveform.unsigned

        if self._format == "BYTE":
            _data_type = 'B' if _unsigned else 'b'
        elif self._format == "WORD":
            _data_type = 'H' if _unsigned else 'h'
        else:
            _data_type = None

        self.data_mode = "ASCII" if self._format == "ASCII" else "BINARY"
        self.data_type = _data_type if _data_type else 'B'
        probe_attenuation = 1

        if source.startswith("CHAN"):
            channel_index = int(source.replace("CHAN", "")) - 1
            probe_attenuation = int(self.channel[channel_index].probe)

        self.fetch_preamble()
        waveform_data = self.waveform.data

        if self._format in ["BYTE", "WORD"]:
            voltages = ((waveform_data - self._y_reference) * self._y_increment + self._y_origin)
        elif self._format == "ASCII":
            voltages = waveform_data
        else:
            raise ValueError(f"Unsupported data format: {self.format}")
        
        return voltages
    
    @Sources.source_command(":DIGitize {}")
    def fetch_trace(self, *sources):
        """
        Fetches trace data from the oscilloscope.
        """
        
        self.query_operation_complete() # let it digitize

        if not sources:
            sources = self.sources.source

        trace_data_dict = {}
        for source in sources:
            data_range = self.fetch_time(source)
            data_values = self.fetch_data(source)
            trace_data_dict[source] = {
                'data': data_values,
                'range': data_range,
                'visible': True,
            }

        self.trace_data_ready.emit(trace_data_dict)  # Emit the trace data for the GUI
        return trace_data_dict  # For scripting use
    
    # def fetch_trace(self, *sources):
    #     """
    #     Fetches trace data from the oscilloscope.
    #     """
    #     trace_data_dict = {}
    #     sources_to_fetch = sources or self.sources.get_active_sources() or [
    #         f"CHAN{num}" for num in range(1, 5) if getattr(self.channel[num-1], 'display', False)
    #     ]

    #     if not sources_to_fetch:
    #         logger.warning("No sources specified for fetching traces, and no channels marked as displayed.")
    #         return trace_data_dict
        
    #     logger.info(f"Fetching traces for sources: {', '.join(sources_to_fetch)}")
    #     self.digitize(*sources_to_fetch)
    #     self.query_operation_complete()

    #     for source in sources_to_fetch:
    #         data_range = self.fetch_time(source)
    #         data_values = self.fetch_data(source)
    #         trace_data_dict[source] = {
    #             'data': data_values,
    #             'range': data_range,
    #             'visible': True,
    #         }

    #     self.trace_data_ready.emit(trace_data_dict)  # Emit the trace data for the GUI
    #     return trace_data_dict  # For scripting use
    
class Acquire(Subsystem):
    """
    Manages the acquisition settings of an oscilloscope or similar instrument.
    """
    mode = SelectProperty(":MODE", ['RTIMe', 'SEGMmented'], "Acquisition mode")
    type = SelectProperty(":TYPE", ['NORMal', 'AVERage', 'HRESolution', 'PEAK'], "Acquisition type")
    sample_rate = ValueProperty(":SRATe", type="float", range=[0.1, 1e9], units="S/s", doc_str="Sample rate in samples per second")
    count = ValueProperty(":COUNt", type="int", range=[1, 10000], doc_str="Number of acquisitions to combine")

class Channel(Subsystem):
    """
    Represents a single channel on an oscilloscope or similar instrument.
    """
    coupling = SelectProperty(":COUPling", ['AC', 'DC'], "Coupling mode of the channel")
    display = SwitchProperty(":DISPlay", "Display state of the channel")
    scale = ValueProperty(":SCALe", type="float", range=[1e-3, 1e3], units="V", doc_str="Vertical scale of the channel")
    offset = ValueProperty(":OFFset", type="float", range=[-1e2, 1e2], units="V", doc_str="Vertical offset of the channel")
    probe = ValueProperty(":PROBe", type="float", doc_str="Probe attenuation factor")

class Timebase(Subsystem):
    """
    Controls the timebase settings of an oscilloscope.
    """
    mode = SelectProperty(":MODE", ['MAIN', 'WIND', 'XY', 'ROLL'], "Timebase mode")
    reference = SelectProperty(":REFerence", ['LEFT', 'CENTer', 'RIGHT'], "Timebase reference position")
    scale = ValueProperty(":SCALe", type="float", range=[1e-9, 1e0], units="s", doc_str="Timebase scale")
    position = ValueProperty(":POSition", type="float", range=[-5e0, 5e0], units="s", doc_str="Timebase position")
    range = ValueProperty(":RANGe", type="float", range=[2e-9, 50e0], units="s", doc_str="Timebase range")

class Trigger(Subsystem):
    """
    Manages the trigger settings of an oscilloscope or similar instrument.
    """
    mode = SelectProperty(":MODe", ['EDGE', 'GLITch', 'PATTern', 'SHOL', 'NONE'], "Trigger mode")
    source = SelectProperty(":SOURce", ['CHAN1', 'CHAN2', 'CHAN3', 'CHAN4', 'EXT', 'LINE', 'WGEN'], "Trigger source")
    slope = SelectProperty(":SLOPe", ['POSitive', 'NEGative'], "Trigger slope")
    sweep = SelectProperty(":SWEep", ['AUTO', 'NORMAL'], "Sweep mode")
    level = ValueProperty(":LEVel", type="float", range=[-5e0, 5e0], units="V", doc_str="Trigger level")

class WaveGen(Subsystem):
    """
    Controls the built-in waveform generator (WGEN) of an instrument.
    """
    function = SelectProperty(":FUNC", ['SIN', 'SQUare', 'RAMP', 'PULSe', 'NOISe', 'DC'], "Waveform function")
    output = SwitchProperty(":OUTP", "Waveform output state")
    frequency = ValueProperty(":FREQ", type="float", range=[1e-3, 1e8], units="Hz", doc_str="Waveform frequency")
    amplitude = ValueProperty(":VOLT", type="float", range=[1e-3, 10e0], units="V", doc_str="Waveform amplitude")
    offset = ValueProperty(":VOLT:OFFS", type="float", range=[-5e0, 5e0], units="V", doc_str="Waveform offset")

class Waveform(Subsystem):
    """
    Manages waveform data retrieval and configuration settings on an oscilloscope or similar instrument.
    """
    source = SelectProperty(":SOURce", ['CHAN1', 'CHAN2', 'CHAN3', 'CHAN4', 'FUNC', 'MATH', 'FFT', 'WMEM', 'BUS1', 'BUS2', 'EXT'], "Waveform source")
    format = SelectProperty(":FORMat", ['ASCII', 'WORD', 'BYTE'], "Waveform data format")
    points_mode = SelectProperty(":POINts:MODE", ['NORMal', 'MAXiumum', 'RAW'], "Waveform points mode")
    byte_order = SelectProperty(":BYTeorder", ['LSBFirst', 'MSBFirst'], "Byte order for 16 bit data capture")
    unsigned = SwitchProperty(":UNSigned", "Indicates if the returned data is signed or unsigned")
    points = ValueProperty(":POINts", type="float", doc_str="Number of trace points to pull")
    x_increment = ValueProperty(":XINCrement", type="float", doc_str="Waveform X increment")
    x_origin = ValueProperty(":XORigin", type="float", doc_str="Waveform X origin")
    x_reference = ValueProperty(":XREFerence", type="int", doc_str="Waveform X reference point")
    y_increment = ValueProperty(":YINCrement", type="float", doc_str="Waveform Y increment")
    y_origin = ValueProperty(":YORigin", type="float", doc_str="Waveform Y origin")
    y_reference = ValueProperty(":YREFerence", type="int", doc_str="Waveform Y reference point")
    preamble = StringProperty(":PREamble", access='read', doc_str="Preamble info including scale factors and offsets.")
    data = DataProperty(":DATa", access='read', ieee_header=True, doc_str="Returns the data array of the waveform as a numpy array.")