import logging
from enum import Enum
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
            # If no sources are explicitly provided, use the global sources or default to an empty list
            sources_to_use = sources if sources else self._sources or []

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

class Oscilloscope(Instrument):
    """
    This class represents an oscilloscope, providing a high-level interface to control and manage its functionalities.
    
    Arguments:
        resource_string (str): VISA resource string for connecting to the oscilloscope.
    
    Attributes:
        trigger (Trigger): Manages the oscilloscope's trigger settings.
        timebase (Timebase): Manages the oscilloscope's timebase settings.
        waveform (Waveform): Manages waveform acquisition and processing.
        wavegen (WaveGen): Controls the oscilloscope's waveform generator.
        acquire (Acquire): Manages the oscilloscope's data acquisition settings.
        channel (dict): Represents each oscilloscope channel as a Channel object.
    """

    class Sources(Enum):
        """
        Enumeration for the oscilloscope sources.

        This helps keep source references tight and prevents the chaos of string typos
        from messing up your slick command flow.

        Attributes:
            CH1 to CH4: Represent the four channels on the oscilloscope.
            FUNCTION: For the function source.
            MATH: Alias for the function source, 'cause math is cool like that.
            BUS: For the bus source.
            FFT: For the Fast Fourier Transform source.
            MEMORY: For memory source references.
            EXT: For external source, exclusive to those 2-channel scope ballers.
        """
        CH1 = 'CHAN1'
        CH2 = 'CHAN2'
        CH3 = 'CHAN3'
        CH4 = 'CHAN4'
        FUNCTION = 'FUNC'
        MATH = 'FUNC'
        BUS = 'BUS'
        FFT = 'FFT'
        MEMORY = 'MEMORY'
        EXT = 'EXT'

        def __str__(self):
            # When the enum is used in a string context, return its value instead of its name
            return self.value

    def __init__(self, resource_string):
        super().__init__(resource_string)
        logger.info("Initializing Oscilloscope with resource string: %s", resource_string)

        self._sources = None
        self._format = "ASCII"

        # Use the build method to create subsystem instances
        self.waveform = Waveform.build(self, ':WAVeform')
        self.trigger = Trigger.build(self, ':TRIGger')
        self.timebase = Timebase.build(self, ':TIMebase')
        self.wavegen = WaveGen.build(self, ':WGEN')
        self.acquire = Acquire.build(self, ':ACQuire')

        # For indexed subsystems, specify the number of indices in the build call
        self.channel = Channel.build(self, ':CHANnel', indices=4)

    def set_data_format(self, format):
        self._format = format

    @source_command(":VIEW {}")
    def set_data_sources(self, *sources):
        """
        Sets the data sources to be displayed on the oscilloscope. If sources are specified,
        it turns off the display for all channels and then turns on the display for the specified sources.
        If no sources are specified, it uses the global sources set previously.
        """
        self.blank()  # Turn off all sources before setting new ones
        if sources:
            # If sources are explicitly provided, update the global sources
            self._sources = sources
            logger.info(f"Sources set to: {sources}")
        else:
            # If no sources are provided, use the global sources
            if not self._sources:
                logger.warning("No sources provided and no global sources set. No action taken.")
                return
            
    @source_command(":AUTOScale {}")
    def autoscale(self, *sources):
        """
        Automatically scales the oscilloscope to optimize the display of specified sources.
        """
        pass  # The decorator handles command execution

    @source_command(":DIGItize {}")
    def digitize(self, *sources):
        """
        Digitizes the specified sources on the oscilloscope.
        """
        pass  # The decorator handles command execution

    @source_command(":VIEW {}")
    def view(self, *sources):
        """
        Turns on the display for specified sources.
        """
        pass  # The decorator handles command execution

    @source_command(":BLANk {}")
    def blank(self, *sources):
        """
        Turns off the display for specified sources.
        """
        pass  # The decorator handles command execution

    def run(self):
        """
        Engages the oscilloscope to start repetitive waveform acquisitions, just like
        hitting that Run button on its face. This function is all about keeping the waves
        coming in a steady stream.

        Parameters:
            None

        Usage:
            osc.run()  # Kick off that continuous acquisition, no stopping
        """
        logger.debug("Engaging continuous waveform acquisition.")
        self.write(":RUN")

    def stop(self):
        """
        Throws the brakes on waveform acquisition. It's like you've walked up to the
        oscilloscope and slapped the Stop button. Everything comes to a standstill, 
        nice and easy.

        Parameters:
            None

        Usage:
            osc.stop()  # Halt the waves, we need a breather
        """
        logger.debug("Halting continuous waveform acquisition.")
        self.write(":STOP")

    def single(self):
        """
        Sets the oscilloscope to snag just one trigger of data. Picture yourself
        pressing the Single key, and the scope captures a single moment in the electrical
        symphony.

        Parameters:
            None

        Usage:
            osc.single()  # One and done, grab a single wave and hold onto it
        """
        logger.debug("Initiating single waveform acquisition.")
        self.write(":SINGLE")

    def fetch_preamble(self):
        """
        Fetches and parses the preamble from the instrument, updating class attributes for waveform scaling.
        """
        logger.debug("Attempting to fetch preamble...")
        try:
            preamble_str = self.waveform.preamble  # Utilizes the getter from the string_property
            logger.debug(f"Raw preamble string: {preamble_str}")
            preamble_values = [float(val) for val in preamble_str.split(',')]
            
            # Log each preamble value for debugging
            logger.debug(f"Format: {preamble_values[0]}")
            logger.debug(f"Type: {preamble_values[1]}")
            logger.debug(f"Points: {preamble_values[2]}")
            logger.debug(f"Count: {preamble_values[3]}")
            logger.debug(f"X Increment: {preamble_values[4]}")
            logger.debug(f"X Origin: {preamble_values[5]}")
            logger.debug(f"X Reference: {preamble_values[6]}")
            logger.debug(f"Y Increment: {preamble_values[7]}")
            logger.debug(f"Y Origin: {preamble_values[8]}")
            logger.debug(f"Y Reference: {preamble_values[9]}")
            
            self._x_increment, self._x_origin, self._x_reference = preamble_values[4], preamble_values[5], int(preamble_values[6])
            self._y_increment, self._y_origin, self._y_reference = preamble_values[7], preamble_values[8], int(preamble_values[9])
            
        except Exception as e:
            logger.error(f'Issue fetching or parsing preamble: {e}')

    def fetch_time(self, source=None):
        """
        Calculates and returns the time array for the waveform data based on preamble info.
        """
        logger.info(f"Fetching time for source: {source}")
        if source:
            self.waveform.source = source  # Set the waveform source if specified.
            logger.debug(f"Waveform source set to: {source}")

        # Need to set the format to read the preamble
        self.waveform.format = self._format
        logger.debug(f"Waveform format set to: {self._format}")

        self.fetch_preamble()
        timestamps = (np.arange(self.waveform.points) - self._x_reference) * self._x_increment + self._x_origin
        return timestamps

    def fetch_data(self, source=None):
        """
        Fetches and returns waveform data in voltage units, performing necessary conversions based on the selected data format.
        Adjusts for probe attenuation.
        """
        logger.info(f"Fetching data for source: {source}")

        if source:
            self.waveform.source = source  # Set the waveform source if specified.
            logger.debug(f"Waveform source set to: {source}")

        # Set the waveform format for the specific channel - We keep them all the same!
        # What kind of mad man is swapping data formats between sources?!
        self.waveform.format = self._format

        # Check if the channel data is unsigned and set the format for binary transfer
        _unsigned = self.waveform.unsigned
        if self._format == "BYTE":
            _data_type = 'B' if _unsigned else 'b'
        elif self._format == "WORD":
            _data_type = 'H' if _unsigned else 'h'
        else:
            _data_type = None
 
        # Keep the instrument mode synced with the waveform settings
        self.data_mode = "ASCII" if self._format == "ASCII" else "BINARY"
        self.data_type = _data_type if _data_type else 'B'

        logger.debug(f"Instrument data format set to: {self.data_mode}")
        logger.debug(f"Instrument data type set to: {self.data_type}")

        # Fetch probe attenuation for the current source if it is a channel
        probe_attenuation = 1  # Default value for non-channel sources
        if source.startswith("CHAN"):
            channel_index = int(source.replace("CHAN", "")) - 1
            probe_attenuation = int(self.channel[channel_index].probe)
            logger.debug(f"Probe attenuation for {source}: {probe_attenuation}")

        # Ensure preamble attributes are up to date
        self.fetch_preamble()

        # Fetch waveform data
        waveform_data = self.waveform.data

        # Convert binary data to voltages using scaling factors from the preamble and adjust for probe attenuation
        if self._format in ["BYTE", "WORD"]:
            voltages = ((waveform_data - self._y_reference) * self._y_increment + self._y_origin)  # * probe_attenuation
            logger.debug(f"Binary data converted to voltages: {voltages}")
        elif self._format == "ASCII":
            # ASCII data is assumed to be pre-scaled by the oscilloscope and directly parsed
            voltages = waveform_data
            logger.debug(f"ASCII data assigned to voltages directly: {voltages}")
        else:
            raise ValueError(f"Unsupported data format: {self.format}")
        if self._format in ["WORD"]:
            voltages = (voltages / 2**4) # ? Only 12 out of 16 bits MSB aligned 
        return voltages

    def fetch_trace(self):
        """
        Fetches trace data from the oscilloscope, utilizing global settings for sources
        and data format if set; otherwise, defaults to fetching from displayed channels.
        """
        
        trace_data_dict = {}
        sources_to_fetch = self._sources if self._sources else [
            f"CH{num}" for num in range(1, 5) if self.channel[num-1].display == '1'
        ]
        logger.info(f"Fetching traces for sources: {sources_to_fetch}")

        self.digitize(*sources_to_fetch)
        self.query_operation_complete()  # Ensures the oscilloscope is ready

        for source in sources_to_fetch:
            data_range = self.fetch_time(source)  # Fetches time base for the source
            data_values = self.fetch_data(source)  # Fetches waveform data adjusted for probe attenuation
            
            trace_data_dict[source] = {
                'data': data_values,
                'range': data_range,
                'visible': True,  # Adjust based on your implementation or the channel's display attribute
            }
        
        self.trace_data_ready.emit(trace_data_dict) # We meed o include this to use the GUI
        return trace_data_dict # This is for using a script

class Acquire(Subsystem):
    """
    Manages the acquisition settings of an oscilloscope or similar instrument.
    """
    mode = select_property(":MODE", ['RTIMe', 'SEGMmented'], "Acquisition mode")
    type = select_property(":TYPE", ['NORMal', 'AVERage', 'HRESolution', 'PEAK'], "Acquisition type")
    sample_rate = value_property(":SRATe", type="float", range=[0.1, 1e9], doc_str="Sample rate in samples per second [S/s]")
    count = value_property(":COUNt", type="int", range=[1, 10000], doc_str="Number of acquisitions to combine [n]")

class Channel(Subsystem):
    """
    Represents a single channel on an oscilloscope or similar instrument.
    """
    coupling = select_property(":COUPling", ['AC', 'DC'], "Coupling mode of the channel")
    display = switch_property(":DISPlay", "Display state of the channel")
    scale = value_property(":SCALe", type="float", range=[1e-3, 1e3], doc_str="Vertical scale of the channel [V/div]")
    offset = value_property(":OFFset", type="float", range=[-1e2, 1e2], doc_str="Vertical offset of the channel [V]")
    probe = value_property(":PROBe", type="float", doc_str="Probe attenuation factor")

class Timebase(Subsystem):
    """
    Controls the timebase settings of an oscilloscope.
    """
    mode = select_property(":MODE", ['MAIN', 'WIND', 'XY', 'ROLL'], "Timebase mode")
    reference = select_property(":REFerence", ['LEFT', 'CENTer', 'RIGHT'], "Timebase reference position")
    scale = value_property(":SCALe", type="float", range=[1e-9, 1e0], doc_str="Timebase scale [s/div]")
    position = value_property(":POSition", type="float", range=[-5e0, 5e0], doc_str="Timebase position [s]")
    range = value_property(":RANGe", type="float", range=[2e-9, 50e0], doc_str="Timebase range [s]")

class Trigger(Subsystem):
    """
    Manages the trigger settings of an oscilloscope or similar instrument.
    """
    mode = select_property(":MODe", ['EDGE', 'GLITch', 'PATTern', 'SHOL', 'NONE'], "Trigger mode")
    source = select_property(":SOURce", ['CHAN1', 'CHAN2', 'CHAN3', 'CHAN4', 'EXT', 'LINE', 'WGEN'], "Trigger source")
    slope = select_property(":SLOPe", ['POSitive', 'NEGative'], "Trigger slope")
    sweep = select_property(":SWEep", ['AUTO', 'NORMAL'], "This controls the sweep mode")
    level = value_property(":LEVel", type="float", range=[-5e0, 5e0], doc_str="Trigger level [V]")

class WaveGen(Subsystem):
    """
    Controls the built-in waveform generator (WGEN) of an instrument.
    """
    function = select_property(":FUNC", ['SIN', 'SQUare', 'RAMP', 'PULSe', 'NOISe', 'DC'], "Waveform function")
    output = switch_property(":OUTP", "Waveform output state")
    frequency = value_property(":FREQ", type="float", range=[1e-3, 1e8], doc_str="Waveform frequency [Hz]")
    amplitude = value_property(":VOLT", type="float", range=[1e-3, 10e0], doc_str="Waveform amplitude [V]")
    offset = value_property(":VOLT:OFFS", type="float", range=[-5e0, 5e0], doc_str="Waveform offset [V]")

class Waveform(Subsystem):
    """
    Manages waveform data retrieval and configuration settings on an oscilloscope or similar instrument.
    """
    source = select_property(":SOURce", ['CHAN1', 'CHAN2', 'CHAN3', 'CHAN4', 'FUNC', 'MATH', 'FFT', 'WMEM', 'BUS1', 'BUS2', 'EXT'], "Waveform source")
    format = select_property(":FORMat", ['ASCII', 'WORD', 'BYTE'], "Waveform data format")
    points_mode = select_property(":POINts:MODE", ['NORMal', 'MAXiumum', 'RAW'], "Waveform points mode")
    byte_order = select_property(":BYTeorder", ['LSBFirst', 'MSBFirst'], "Byte order for 16 bit data capture")
    unsigned = switch_property(":UNSigned", "Indicates if the returned data is signed or unsigned")
    points = value_property(":POINts", type="float", doc_str="Number of trace points to pull")
    x_increment = value_property(":XINCrement", type="float", doc_str="Waveform X increment")
    x_origin = value_property(":XORigin", type="float", doc_str="Waveform X origin")
    x_reference = value_property(":XREFerence", type="int", doc_str="Waveform X reference point")
    y_increment = value_property(":YINCrement", type="float", doc_str="Waveform Y increment")
    y_origin = value_property(":YORigin", type="float", doc_str="Waveform Y origin")
    y_reference = value_property(":YREFerence", type="int", doc_str="Waveform Y reference point")
    preamble = string_property(":PREamble", access='read', doc_str="Preamble info including scale factors and offsets.")
    data = data_property(":DATa", access='read', ieee_header=True, doc_str="Returns the data array of the waveform as a numpy array.")