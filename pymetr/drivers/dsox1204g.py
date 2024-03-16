from instrument import Instrument, Subsystem
from properties import switch_property, select_property, value_property, data_property
from enum import Enum
import numpy as np
import logging

# Set up logging
logger = logging.getLogger(__name__)

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
        channels (dict): Represents each oscilloscope channel as a Channel object.
        continuous_fetch (bool): Flag to enable/disable continuous waveform fetching.
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
        CHAN1 = 'CHAN1'
        CHAN2 = 'CHAN2'
        CHAN3 = 'CHAN3'
        CHAN4 = 'CHAN4'
        FUNCTION = 'FUNC'
        MATH = 'FUNC'
        BUS = 'BUS'
        FFT = 'FFT'
        MEMORY = 'MEMORY'
        EXT = 'EXT'

        def __str__(self):
            """
            Return a string representation of the source that's compatible with the oscilloscope command syntax.
            """
            return self.name

    def __init__(self, resource_string):
        super().__init__(resource_string)
        logger.info("Initializing Oscilloscope with resource string: %s", resource_string)
        self.data_format = "ASCII"
        self.continuous_fetch = False

        # Use the build method to create subsystem instances
        self.waveform = Waveform.build(self, ':WAVeform')
        self.trigger = Trigger.build(self, ':TRIGger')
        self.timebase = Timebase.build(self, ':TIMebase')
        self.wavegen = WaveGen.build(self, ':WAVegen')
        self.acquire = Acquire.build(self, ':ACQuire')

        # For indexed subsystems, specify the number of indices in the build call
        self.channels = Channel.build(self, ':CHANnel', indices=4)

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

    def autoscale(self, *sources):
        """
        Automatically scales the oscilloscope to optimize the display of specified sources.

        This method evaluates all specified input signals and automatically adjusts the oscilloscope's
        settings to display those signals optimally. If no sources are specified, it autoscales all available
        sources. It's the code equivalent of pressing the Auto Scale button on the oscilloscope.

        Parameters:
            *sources (enum.Enum or str): Variable length argument list of sources to autoscale.
                                        Sources can be specified as either enum members from
                                        Oscilloscope.Source or as strings. If no sources are
                                        specified, all sources are autoscaled.

        Examples:
            osc.autoscale()  # Autoscales all sources
            osc.autoscale(Oscilloscope.Source.CH1, Oscilloscope.Source.CH2)  # Autoscales CH1 and CH2
            osc.autoscale('CH1', 'CH2')  # Another way to autoscale CH1 and CH2
        """
        source_strings = [str(source.value) if isinstance(source, Enum) else str(source) for source in sources]
        source_str = ', '.join(source_strings)

        if source_str:
            logger.debug(f"Autoscaling specified sources: {source_str}")
            self.write(f":AUTOScale {source_str}")
        else:
            logger.debug("Autoscaling all sources.")
            self.write(":AUTOScale")

    def digitize(self, *sources):
        """
        Digitizes the specified sources on the oscilloscope.

        When called, this method sends a command to the oscilloscope to digitize the specified sources.
        If no sources are specified, it will digitize all available sources. Sources can be specified
        as either enum members from Oscilloscope.Source or as strings.

        Parameters:
            *sources (enum.Enum or str): Variable length argument list of sources to digitize.
                                        Sources can be specified as either enum members from
                                        Oscilloscope.Source or as strings. If no sources are
                                        specified, all sources are digitized.

        Examples:
            osc.digitize()  # Digitizes all sources
            osc.digitize(Oscilloscope.Source.CH1, Oscilloscope.Source.CH2)  # Digitizes CH1 and CH2
            osc.digitize('CH1', 'CH2')  # Another way to digitize CH1 and CH2
        """
        source_strings = [str(source.value) if isinstance(source, Enum) else str(source) for source in sources]
        source_str = ', '.join(source_strings)

        if source_str:
            logger.debug(f"Digitizing specified sources: {source_str}")
            self.write(f":DIGItize {source_str}")
        else:
            logger.debug("Digitizing all available channels.")
            self.write(":DIGItize")

    def view(self, *sources):
        """
        Lights up the specified source(s) on the oscilloscope's display. Whether it's one channel, two, or a full house, this method makes them shine.

        Parameters:
            *sources (enum | str): A variable-length list of sources to view. Can be either enum members from `Source` or string literals representing the sources.

        Usage:
            osc.view(osc.Source.CH1) # Show me CH1!
            osc.view('CH1', osc.Source.CH2) # CH1 and CH2, let's see what you got!

        Returns:
            None
        """
        # Convert each source to its string representation.
        source_strings = [str(source) if isinstance(source, Enum) else source for source in sources]

        # Loop through each source string and write the view command for it.
        for source_str in source_strings:
            logger.debug("Turning on the view for source: %s", source_str)
            self.write(f":VIEW {source_str}")

    def blank(self, *sources):
        """
        The master of stealth, this method turns off the display for the specified source(s). Want to clear the screen? Just don't pass any sources.

        Parameters:
            *sources (enum | str, optional): A variable-length list of sources to hide. If no sources are passed, all will be blanked.

        Usage:
            osc.blank() # Ninja mode, everything disappears
            osc.blank(osc.Source.CH1) # Just CH1, go to sleep

        Returns:
            None
        """
        # Check if any sources were passed; if not, turn off all sources.
        if not sources:
            logger.debug("Turning off all sources.")
            self.write(":BLANk")
            return

        # Convert each source to its string representation.
        source_strings = [str(source) if isinstance(source, Enum) else source for source in sources]

        # Loop through each source string and write the blank command for it.
        for source_str in source_strings:
            logger.debug("Turning off the source: %s", source_str)
            self.write(f":BLANk {source_str}")

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
    probe = select_property(":PROBe", ['1', '10'], doc_str="Probe attenuation factor")

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
    mode = select_property(":MODe", ['EDGE', 'GLITch', 'PATTern', 'SHOL'], "Trigger mode")
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
    unsigned = switch_property(":UNSigned", "Indicates if the returned data is signed or unsigned")
    points = value_property(":POINts", type="int", doc_str="Number of trace points to pull")
    preamble = data_property(":PREamble", access='read', doc_str="Pre-amble info including scale factors and offsets.")
    data = data_property(":DATa", access='read', ieee_header=True, doc_str="Returns the data array of the waveform as a numpy array.")

    def fetch_preamble(self):
        """
        Fetches and parses the preamble from the instrument, updating class attributes for waveform scaling.
        """
        try:
            preamble_str = self.preamble  # Utilizes the getter from the value_property
            preamble_values = [float(val) for val in preamble_str.split(',')]

            self.format = preamble_values[0]
            self.type = int(preamble_values[1])
            self.num_points = int(preamble_values[2])
            self.count = int(preamble_values[3])
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
