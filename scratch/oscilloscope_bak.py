# oscilloscope.py
from pyinstrument.instruments import Instrument, InstrumentSubsystem
from enum import Enum
import logging
from utilities import debug, timeit
import numpy as np

class Oscilloscope(Instrument):

    def __init__(self, resource_string):
        super(Oscilloscope, self).__init__(resource_string)
        self.trigger = self.Trigger(self)
        self.timebase = self.Timebase(self)
        self.waveform = self.Waveform(self)
        self.wavegen = self.WaveGen(self)
        self.acquire = self.Acquire(self)
        self.channels = {ch: self.Channel(self, ch) for ch in range(1, 5)}
        self.continuous_fetch = False

    def run(self):
        self.write(":RUN")

    def stop(self):
        self.write(":STOP")

    def single(self):
        self.write(":SINGLE")

    class Acquire(InstrumentSubsystem):
        """
        Manages the acquisition parameters of the oscilloscope, including the mode, type, 
        sample rate, and depth of acquisition. 

        Attributes:
            _mode (Mode): The current acquisition mode.
            _type (Type): The type of acquisition (e.g., normal, average).
            _sample_rate (float): The sample rate in samples per second.
            _depth (int): The depth of the acquisition.
        """

        class Mode(Enum):
            RTIM = "RTIM"
            SEGM = "SEGM"

        class Type(Enum):
            NORMAL = "NORM"
            AVERAGE = "AVER"
            HRES = "HRES"
            PEAK = "PEAK"

        def __init__(self, parent):
            super().__init__(parent)
            self._mode = None
            self._type = None
            self._sample_rate = None
            self._depth = None

        @property
        def mode(self):
            response = self._parent.query(":ACQuire:MODE?")
            self._mode = self.Mode(response.strip())
            return self._mode

        @mode.setter
        def mode(self, value):
            if isinstance(value, self.Mode):
                self._parent.write(f":ACQuire:MODE {value.value}")
                self._mode = value
            else:
                raise ValueError(f"Invalid mode: {value}. Choose from {[mode.value for mode in self.Mode]}.")

        @property
        def type(self):
            response = self._parent.query(":ACQuire:TYPe?")
            self._type = self.Type(response.strip())
            return self._type

        @type.setter
        def type(self, value):
            if isinstance(value, self.Type):
                self._parent.write(f":ACQuire:TYPe {value.value}")
                self._type = value
            else:
                raise ValueError(f"Invalid type: {value}. Choose from {[type.value for type in self.Type]}.")

        @property
        def sample_rate(self):
            response = self._parent.query(":ACQuire:SRATe?")
            self._sample_rate = float(response)
            return self._sample_rate

        @sample_rate.setter
        def sample_rate(self, value):
            self._parent.write(f":ACQuire:SRATe {value}")
            self._sample_rate = value

        @property
        def depth(self):
            response = self._parent.query(":ACQuire:DEPTh?")
            self._depth = int(response)
            return self._depth

        @depth.setter
        def depth(self, value):
            self._parent.write(f":ACQuire:DEPTh {value}")
            self._depth = value

        def sync(self):
            """Ensures the acquisition settings are synchronized with the oscilloscope's current configuration."""
            super().sync()

    class Trigger(InstrumentSubsystem):
        """
        Manages the trigger settings of the oscilloscope, controlling when the oscilloscope starts acquiring data.
        
        The trigger settings include the trigger mode, source, level, and slope. This class allows for intuitive
        control over these parameters, automatically updating the oscilloscope with any changes made, and verifying
        the applied settings by querying the oscilloscope.
        
        Attributes:
            _parent (Oscilloscope): A reference to the parent oscilloscope instance.
            _mode (str): The trigger mode ('EDGE', 'VIDEO', etc.).
            _source (str): The input source for the trigger (e.g., 'CHANnel1').
            _level (float): The voltage level at which the trigger occurs.
            _slope (str): The slope condition of the trigger ('POSITIVE' or 'NEGATIVE').

        Properties:
            mode: Gets or sets the trigger mode.
            source: Gets or sets the trigger source.
            level: Gets or sets the trigger level.
            slope: Gets or sets the trigger slope.

        Usage:
            osc = Oscilloscope("TCPIP0::192.168.1.111::hislip0::INSTR")
            trig = osc.trigger
            trig.mode = 'EDGE'  # Sets the trigger mode and validates it by querying the oscilloscope
            current_mode = trig.mode  # Gets the current trigger mode
        """
        def __init__(self, parent):
            self._parent = parent
            self._mode = None
            self._source = None
            self._level = None
            self._slope = None

        @property
        def mode(self):
            self._mode = self._parent.query(":TRIGger:MODE?").strip()
            return self._mode

        @mode.setter
        def mode(self, value):
            self._parent.write(f":TRIGger:MODE {value.upper()}")
            self._mode = self._parent.query(":TRIGger:MODE?").strip()

        @property
        def source(self):
            self._source = self._parent.query(f":TRIGger:{self._mode}:SOURce?").strip()
            return self._source

        @source.setter
        def source(self, value):
            self._parent.write(f":TRIGger:{self._mode}:SOURce {value}")
            self._source = self._parent.query(f":TRIGger:{self._mode}:SOURce?").strip()

        @property
        def level(self):
            self._level = float(self._parent.query(f":TRIGger:{self._mode}:LEVel?"))
            return self._level

        @level.setter
        def level(self, value):
            self._parent.write(f":TRIGger:{self._mode}:LEVel {value}")
            self._level = float(self._parent.query(f":TRIGger:{self._mode}:LEVel?"))

        @property
        def slope(self):
            self._slope = self._parent.query(f":TRIGger:{self._mode}:SLOPe?").strip()
            return self._slope

        @slope.setter
        def slope(self, value):
            self._parent.write(f":TRIGger:{self._mode}:SLOPe {value.upper()}")
            self._slope = self._parent.query(f":TRIGger:{self._mode}:SLOPe?").strip()

        def sync(self):
            # Ensure superclass sync method is called to handle any additional generic synchronization logic
            super().sync()

    class Timebase(InstrumentSubsystem):
        """
        Handles the timebase settings of the oscilloscope which control the horizontal sweep functions.
        
        The timebase settings include the mode, scale, position, and range of the oscilloscope's horizontal axis. 
        This class provides a Pythonic interface for getting and setting these properties, with changes being 
        immediately written to the oscilloscope and verified through queries.
        
        Attributes:
            _parent (Oscilloscope): A reference to the parent oscilloscope instance.
            _mode (str): The current timebase mode of the oscilloscope ('MAIN', 'WINDOW', 'XY', 'ROLL').
            _scale (float): The current time/division scale setting of the oscilloscope.
            _position (float): The current timebase position setting of the oscilloscope.
            _range (float): The full-scale range of the timebase in seconds.
        
        Properties:
            mode: Gets or sets the timebase mode.
            scale: Gets or sets the time/division scale.
            position: Gets or sets the timebase position.
            range: Gets or sets the full-scale range of the timebase.
            
        The setter for each property updates the oscilloscope with the new value and then retrieves the 
        setting from the oscilloscope to ensure it was applied correctly. If an invalid setting is detected, 
        a ValueError is raised.
        
        Usage:
            osc = Oscilloscope("TCPIP0::192.168.1.111::hislip0::INSTR")
            timebase = osc.timebase
            timebase.mode = 'MAIN'  # Sets the mode and validates it by querying the oscilloscope
            current_mode = timebase.mode  # Gets the current timebase mode
        """
        def __init__(self, parent):
            self._parent = parent
            self._mode = None
            self._scale = None
            self._position = None
            self._range = None

        @property
        def mode(self):
            self._mode = self._parent.query(":TIMebase:MODE?").strip()
            return self._mode

        @mode.setter
        def mode(self, value):
            valid_modes = ['MAIN', 'WINDOW', 'XY', 'ROLL']
            if value.upper() not in valid_modes:
                raise ValueError(f"Invalid mode: {value}. Choose from {valid_modes}.")
            self._parent.write(f":TIMebase:MODE {value.upper()}")
            self._mode = self._parent.query(":TIMebase:MODE?").strip()

        @property
        def scale(self):
            self._scale = float(self._parent.query(":TIMebase:SCALe?"))
            return self._scale

        @scale.setter
        def scale(self, value):
            self._parent.write(f":TIMebase:SCALe {value}")
            self._scale = float(self._parent.query(":TIMebase:SCALe?"))

        @property
        def position(self):
            self._position = float(self._parent.query(":TIMebase:POSition?"))
            return self._position

        @position.setter
        def position(self, value):
            self._parent.write(f":TIMebase:POSition {value}")
            self._position = float(self._parent.query(":TIMebase:POSition?"))

        @property
        def range(self):
            self._range = float(self._parent.query(":TIMebase:RANGe?"))
            return self._range

        @range.setter
        def range(self, value):
            self._parent.write(f":TIMebase:RANGe {value}")
            self._range = float(self._parent.query(":TIMebase:RANGe?"))

        def sync(self):
            # Ensure superclass sync method is called to handle any additional generic synchronization logic
            super().sync()

    class Channel(InstrumentSubsystem):
        """
        Represents an individual channel on the oscilloscope, allowing control over its display, scaling, 
        and other properties.

        Each channel can be configured for different acquisition parameters and can be queried for its current 
        settings, making sure the channel is set up correctly before acquiring data.

        Attributes:
            _parent (Oscilloscope): Reference to the parent oscilloscope instance to use for communication.
            channel_number (int): The specific channel number on the oscilloscope.
            _display (str): The display state of the channel ('ON' or 'OFF').
            _scale (float): The vertical scale (volts per division) of the channel.
            _offset (float): The vertical offset (volts) of the channel.
            _coupling (str): The input coupling of the channel ('AC' or 'DC').
            _probe_attenuation (float): The attenuation factor of the probe connected to the channel.

        Properties:
            display: Gets or sets the channel's display state.
            scale: Gets or sets the channel's vertical scale.
            offset: Gets or sets the channel's vertical offset.
            coupling: Gets or sets the channel's input coupling.
            probe_attenuation: Gets or sets the probe attenuation for the channel.

        Usage:
            osc = Oscilloscope("TCPIP0::192.168.1.111::hislip0::INSTR")
            ch1 = osc.channels[1]
            ch1.display = 'ON'  # Enable channel 1 display
            ch1.scale = 0.5  # Set scale to 0.5 V/div
        """
        def __init__(self, parent, channel_number):
            self._parent = parent
            self.channel_number = channel_number
            self._display = None
            self._scale = None
            self._offset = None
            self._coupling = None
            self._probe_attenuation = None

        @property
        def display(self):
            # Read the current display state from the oscilloscope
            self._display = 'ON' if self._parent.query(f":CHANnel{self.channel_number}:DISPlay?").strip() == '1' else 'OFF'
            return self._display

        @display.setter
        def display(self, value):
            # Write the new display state to the oscilloscope
            scpi_value = '1' if value == 'ON' else '0'
            self._parent.write(f":CHANnel{self.channel_number}:DISPlay {scpi_value}")
            # Read back the display state to confirm the change
            confirmed_state = self._parent.query(f":CHANnel{self.channel_number}:DISPlay?").strip() == '1'
            self._display = 'ON' if confirmed_state else 'OFF'

        @property
        def scale(self):
            self._scale = float(self._parent.query(f":CHANnel{self.channel_number}:SCALe?"))
            return self._scale

        @scale.setter
        def scale(self, value):
            self._parent.write(f":CHANnel{self.channel_number}:SCALe {value}")
            self._scale = float(self._parent.query(f":CHANnel{self.channel_number}:SCALe?"))

        @property
        def offset(self):
            self._offset = float(self._parent.query(f":CHANnel{self.channel_number}:OFFSet?"))
            return self._offset

        @offset.setter
        def offset(self, value):
            self._parent.write(f":CHANnel{self.channel_number}:OFFSet {value}")
            self._offset = float(self._parent.query(f":CHANnel{self.channel_number}:OFFSet?"))

        @property
        def coupling(self):
            self._coupling = self._parent.query(f":CHANnel{self.channel_number}:COUPling?").strip()
            return self._coupling

        @coupling.setter
        def coupling(self, value):
            valid_couplings = ['AC', 'DC']
            if value not in valid_couplings:
                raise ValueError(f"Invalid coupling: {value}. Choose from {valid_couplings}.")
            self._parent.write(f":CHANnel{self.channel_number}:COUPling {value}")
            self._coupling = self._parent.query(f":CHANnel{self.channel_number}:COUPling?").strip()

        @property
        def probe_attenuation(self):
            self._probe_attenuation = float(self._parent.query(f":CHANnel{self.channel_number}:PROBe?"))
            return self._probe_attenuation

        @probe_attenuation.setter
        def probe_attenuation(self, value):
            self._parent.write(f":CHANnel{self.channel_number}:PROBe {value}")
            self._probe_attenuation = float(self._parent.query(f":CHANnel{self.channel_number}:PROBe?"))

        def sync(self):
            # Ensure superclass sync method is called to handle any additional generic synchronization logic
            super().sync()

    class WaveGen(InstrumentSubsystem):
        """
        Manages the built-in waveform generator (WGEN) of the oscilloscope, controlling waveform output and modulation.

        This class allows you to set waveform parameters such as frequency, function, amplitude, and more.
        It offers a Pythonic interface to the oscilloscope's WGEN subsystem for generating various signal types.

        Attributes:
            _parent (Oscilloscope): Reference to the parent oscilloscope instance.
            _frequency (float): Output frequency of the waveform generator.
            _function (str): The waveform function type (e.g., 'SINusoid', 'SQUare', 'RAMP').
            _amplitude (float): Amplitude of the output waveform.
            _output (bool): Output state of the waveform generator (ON or OFF).
            ... (other attributes for different parameters)

        Properties:
            frequency: Gets or sets the waveform frequency.
            function: Gets or sets the waveform function type.
            amplitude: Gets or sets the waveform amplitude.
            output: Enables or disables the waveform output.
            ... (other properties for different parameters)

        Usage:
            osc = Oscilloscope("TCPIP0::192.168.1.111::hislip0::INSTR")
            wgen = osc.waveformGenerator
            wgen.frequency = 1e6  # Set frequency to 1 MHz
            wgen.function = 'SINusoid'  # Set function to sinusoid
            wgen.output = True  # Enable the waveform output
        """
        def __init__(self, parent):
            super().__init__(parent)
            self._frequency = None
            self._function = None
            self._amplitude = None
            self._output = None

        @property
        def frequency(self):
            self._frequency = float(self._parent.query(":WGEN:FREQuency?"))
            return self._frequency

        @frequency.setter
        def frequency(self, value):
            self._parent.write(f":WGEN:FREQuency {value}")

        @property
        def function(self):
            self._function = self._parent.query(":WGEN:FUNCtion?").strip()
            return self._function

        @function.setter
        def function(self, value):
            valid_functions = ['SINusoid', 'SQUare', 'RAMP', 'PULSe', 'NOISe', 'DC']
            value = self._parent._match_command_option(value, valid_functions)
            self._parent.write(f":WGEN:FUNCtion {value}")

        @property
        def amplitude(self):
            self._amplitude = float(self._parent.query(":WGEN:VOLTage?"))
            return self._amplitude

        @amplitude.setter
        def amplitude(self, value):
            self._parent.write(f":WGEN:VOLTage {value}")

        @property
        def output(self):
            output_state = self._parent.query(":WGEN:OUTPut?").strip()
            self._output = 'ON' if output_state == '1' else 'OFF'
            return self._output

        @output.setter
        def output(self, value):
            scpi_value = '1' if value.upper() == 'ON' else '0'
            self._parent.write(f":WGEN:OUTPut {scpi_value}")

        def sync(self):
            super().sync()

    class Waveform(InstrumentSubsystem):
        """
        Manages waveform data acquisition and processing for an oscilloscope channel.

        This class allows for detailed control over waveform data formatting, retrieval, and interpretation,
        ensuring that you can capture and analyze signal data effectively.

        Attributes:
            _parent (Oscilloscope): A reference to the parent oscilloscope instance.
            _format (str): The data format for waveform points (e.g., 'BYTE', 'WORD', 'ASCII').
            _points_mode (str): The mode for waveform points acquisition ('NORMal', 'MAXimum', 'RAW').
            _num_points (int): The number of waveform points to retrieve.
            ... (other attributes for additional parameters)

        Properties:
            format: Gets or sets the waveform data format.
            points_mode: Gets or sets the waveform points mode.
            num_points: Gets or sets the number of waveform points.
            ... (other properties for additional parameters)

        Usage:
            osc = Oscilloscope("TCPIP0::192.168.1.111::hislip0::INSTR")
            wf = osc.waveform
            wf.format = 'BYTE'  # Set data format to BYTE
            wf.points_mode = 'NORMal'  # Set points mode to NORMal
            wf.num_points = 500  # Retrieve 500 points
            ... (use other properties as needed)
        """
        def __init__(self, parent):
            super().__init__(parent)
            self._format = None
            self._points_mode = None
            self._num_points = 500  
            self.x_increment = 1.0
            self.x_origin = 0.0
            self.y_increment = 1.0
            self.y_origin = 0.0
            self.y_reference = 0
            self.is_data_unsigned = False  

        @property
        def format(self):
            return self._parent.query(":WAVeform:FORMat?").strip()

        @format.setter
        def format(self, value):
            valid_formats = {'ASCII', 'WORD', 'BYTE'}
            if value not in valid_formats:
                raise ValueError(f"Invalid format: {value}. Choose from {valid_formats}.")
            self._parent.write(f":WAVeform:FORMat {value}")
            self._format = self._parent.query(":WAVeform:FORMat?").strip()

        @property
        def points_mode(self):
            self._points_mode = self._parent.query(":WAVeform:POINts:MODE?").strip()
            return self._points_mode

        @points_mode.setter
        def points_mode(self, value):
            valid_modes = ['NORMAL', 'MAXIMUM', 'RAW']
            value = self._parent._match_command_option(value, valid_modes)
            self._parent.write(f":WAVeform:POINts:MODE {value}")
            self._points_mode = value

        @property
        def num_points(self):
            self._num_points = int(self._parent.query(":WAVeform:POINts?"))
            return self._num_points

        @num_points.setter
        def num_points(self, value):
            self._parent.write(f":WAVeform:POINts {value}")
            self._num_points = value

        def sync(self):
            # Ensure superclass sync method is called to handle any additional generic synchronization logic
            super().sync()

        def setup_trace(self, channel="CHANnel1", points_mode="NORMAL", num_points=500, data_format='BYTE'):
            self.points_mode = points_mode  # This will use the points_mode setter
            self.num_points = num_points    # This will use the num_points setter
            self.source = channel           # This should be updated to use a proper setter or handled differently if "source" property is added
            self.format = data_format       # This will use the format setter

        def fetch_preamble(self):
            try:
                preamble_str = self._parent.query(":WAVeform:PREamble?")
                preamble_values = preamble_str.split(',')

                # Assign the parsed preamble values to the relevant attributes
                self._num_points = int(preamble_values[2])
                self.x_increment = float(preamble_values[4])
                self.x_origin = float(preamble_values[5])
                self.y_increment = float(preamble_values[7])
                self.y_origin = float(preamble_values[8])
                self.y_reference = int(preamble_values[9])
                self.is_data_unsigned = bool(int(self._parent.query(":WAVeform:UNSigned?")))

                # Logging to check preamble values
                logging.debug(f"Preamble values: {preamble_values}")
                logging.debug(f"Number of points: {self._num_points}")
                logging.debug(f"X increment: {self.x_increment}")
                logging.debug(f"Y increment: {self.y_increment}")
                logging.debug(f"Data is unsigned: {self.is_data_unsigned}")

            except Exception as e:
                logging.error(f'Had an issue with preamble: {e}')

        @debug
        def fetch_trace(self, channel):
            self.fetch_preamble()  # Ensure preamble attributes are up to date

            format_setting = self.format  # Directly use the property
            if format_setting == 'BYTE':
                try:
                    trace_data_raw = self.query_binary_values(":WAVeform:DATA?", datatype='B', container=bytes)
                    dtype = np.uint8 if self.is_data_unsigned else np.int8
                    trace_data = np.frombuffer(trace_data_raw, dtype=dtype)
                    voltages = (trace_data - self.y_reference) * self.y_increment + self.y_origin
                    return voltages
                except Exception as e:
                    raise ValueError(f"Failed to fetch or interpret binary data: {e}")
            elif format_setting == 'ASCII':
                # ASCII format assumes the oscilloscope has scaled the data
                try:
                    trace_data_raw = self._parent.handle.query(":WAVeform:DATA?").strip()
                    if trace_data_raw.startswith('#'):
                        header_end = trace_data_raw.find(' ')  # Find the end of the preamble
                        if header_end != -1:
                            trace_data_raw = trace_data_raw[header_end + 1:]  # Skip the preamble
                        else:
                            raise ValueError("Preamble format unrecognized, cannot find data start.")
                    voltages = np.array([float(data) for data in trace_data_raw.split(',') if data], dtype=np.float32)
                except ValueError as e:
                    raise ValueError(f"Error converting ASCII data to float: {e}")
            else:
                raise ValueError(f"Unsupported data format: {self.format}")

            return voltages
        
        def query_binary_values(self, query, datatype='B', container=bytes):
            """
            Queries binary data from the instrument after ensuring the connection handle is open.

            Args:
                query (str): The SCPI query command to be sent to the instrument.
                datatype (char): The datatype character for the binary data. Defaults to 'B'.
                container: The type of the container to store the data. Defaults to bytes.

            Returns:
                The binary data returned from the instrument as specified by the container type.

            Raises:
                ValueError: If the instrument handle is not open.
            """
            if not self._parent.handle:
                raise ValueError("Instrument handle not open")
            return self._parent.handle.query_binary_values(query, datatype=datatype, container=container)

# Unit Test
if __name__ == "__main__":
    osc = Oscilloscope("TCPIP0::192.168.1.111::hislip0::INSTR")
    osc.open()
    osc.handle.timeout = 15000
    
    # Test identification string
    print(f"Identification string: '{osc.identity()}'")
    
    # Test Trigger settings
    osc.trigger.mode = 'EDGE'
    osc.trigger.level = 1.5
    print(f"Trigger mode set to: {osc.trigger.mode}, level set to: {osc.trigger.level}")
    
    # Test Timebase settings
    osc.timebase.scale = 1e-3
    osc.timebase.position = 0
    print(f"Timebase scale set to: {osc.timebase.scale}, position set to: {osc.timebase.position}")
    
    # Test Channel settings
    channel = 1
    osc.channels[channel].display = 'ON'
    osc.channels[channel].scale = 0.2
    print(f"Channel {channel} display set to: {osc.channels[channel].display}, scale set to: {osc.channels[channel].scale}")
    
    # Test WaveformGenerator settings
    osc.wavegen.function = 'SIN'
    osc.wavegen.frequency = 1e6
    osc.wavegen.output = 1
    print(f"WaveGen function set to: {osc.wavegen.function}, frequency set to: {osc.wavegen.frequency}")
    
    # Setup and fetch trace data
    osc.waveform.setup_trace(channel="CHANnel1", points_mode="NORM", num_points=500, data_format='BYTE')
    trace_data = osc.waveform.fetch_trace("CHANnel1")
    print(f"Trace data points retrieved: {len(trace_data)}")

    osc.close()
    print("Oscilloscope operations completed.")
