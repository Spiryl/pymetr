# core.py
import logging
import sys
from enum import Enum, auto

from pymetr.instruments import Instrument
from pymetr.oscilloscope.acquire import Acquire
from pymetr.oscilloscope.trigger import Trigger
from pymetr.oscilloscope.timebase import Timebase
from pymetr.oscilloscope.channel import Channel
from pymetr.oscilloscope.wavegen import WaveGen
from pymetr.oscilloscope.waveform import Waveform

from utilities import debug, timeit

# Create a logger for the oscilloscope module
logger = logging.getLogger(__name__)

class Oscilloscope(Instrument):
    """
    Represents the oscilloscope device with all its functionalities, offering a high-level
    interface for controlling and managing the oscilloscope's various subsystems.

    Each subsystem (trigger, timebase, waveform, wavegen, acquire, channels) is represented
    by a separate class, allowing for modular control over the oscilloscope's features.

    :param resource_string: VISA resource string for oscilloscope connection.
    :type resource_string: str
    :ivar trigger: Manages the trigger settings of the oscilloscope.
    :vartype trigger: :class:`pymetr.oscilloscope.trigger.Trigger`
    :ivar timebase: Manages the timebase settings of the oscilloscope.
    :vartype timebase: :class:`pymetr.oscilloscope.timebase.Timebase`
    :ivar waveform: Manages waveform acquisition and processing.
    :vartype waveform: :class:`pymetr.oscilloscope.waveform.Waveform`
    :ivar wavegen: Controls the waveform generator of the oscilloscope.
    :vartype wavegen: :class:`pymetr.oscilloscope.wavegen.WaveGen`
    :ivar acquire: Manages data acquisition settings of the oscilloscope.
    :vartype acquire: :class:`pymetr.oscilloscope.acquire.Acquire`
    :ivar channels: Represents each channel on the oscilloscope as a :class:`pymetr.oscilloscope.channel.Channel` object.
    :vartype channels: dict
    :ivar continuous_fetch: Flag to enable or disable continuous waveform fetching.
    :vartype continuous_fetch: bool
    """
    class Source(Enum):
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
        CH1 = 'CH1'
        CH2 = 'CH2'
        CH3 = 'CH3'
        CH4 = 'CH4'
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
        self.trigger = Trigger(self)
        self.timebase = Timebase(self)
        self.waveform = Waveform(self)
        self.wavegen = WaveGen(self)
        self.acquire = Acquire(self)
        self.channels = {ch: Channel(self, ch) for ch in range(1, 5)}
        self.continuous_fetch = False

    def check_instrument_errors(self, command):
        """
        Checks the instrument for errors after executing a command.

        Continuously queries the oscilloscope for its error queue until it's empty,
        printing out any errors encountered. If an error is found, the program exits.

        :param command: The SCPI command that was executed prior to checking for errors.
        :type command: str
        """
        while True:
            error_string = self.query(":SYSTem:ERRor?")
            if error_string:  # If there is an error string value
                if not error_string.startswith("+0,"):  # Not "No error"
                    print(f"ERROR: {error_string}, command: '{command}'")
                    print("Exited because of error.")
                    sys.exit(1)
                else:  # "No error"
                    break
            else:  # :SYSTem:ERRor? should always return a string
                print(f"ERROR: :SYSTem:ERRor? returned nothing, command: '{command}'")
                print("Exited because of error.")
                sys.exit(1)

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

# Unit Test
if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
    
    osc = Oscilloscope("TCPIP0::192.168.1.111::hislip0::INSTR")
    osc.open()
    print(f"Identification string: '{osc.identity()}'")
    osc.close()
