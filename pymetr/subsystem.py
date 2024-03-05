import logging

class Subsystem:
    """
    Represents a subsystem of an instrument command hierarchy. Dynamically constructs and executes 
    SCPI commands based on the class hierarchy and property access. Supports direct property access 
    and method invocation for setting and querying values. Integrates logging at various points 
    to facilitate debugging and tracking of operations.
    """

    # Set up a logger for this class.
    logger = logging.getLogger(__name__)

    def __init__(self, parent=None, cmd_str="", index=None):
        """
        Initializes a new instance of Subsystem.
        
        Args:
            parent (Subsystem): The parent subsystem or None if this is the root.
            cmd_str (str): The SCPI command string for this subsystem.
            index (int, optional): The numerical index for commands that require it (e.g., CHANNEL1).
        """
        self._parent = parent
        self._cmd_str = cmd_str
        self._index = index
        self._value = None  # To hold the value if it's a settable property.

        # Log the initialization of the subsystem.
        self.logger.debug(f"Subsystem '{self._cmd_str}' with index '{self._index}' initialized.")

    def _build_command(self, action=""):
        """
        Constructs the full SCPI command string for this subsystem by traversing
        up the hierarchy and appending command string segments.

        Args:
            action (str): An optional action to append, such as '?' for queries.

        Returns:
            str: The fully constructed SCPI command string.
        """
        # Append index if present and start building the command from this subsystem.
        parts = [f"{self._cmd_str}{self._index}" if self._index is not None else self._cmd_str]
        
        # Traverse up the hierarchy to build the full command string.
        parent = self._parent
        while parent:
            parent_cmd = f"{parent._cmd_str}{parent._index}" if parent._index is not None else parent._cmd_str
            parts.insert(0, parent_cmd)
            parent = parent._parent
        
        # Join all parts and append the action if provided.
        full_command = ":".join(filter(None, parts))  # Filter out empty strings.
        full_command += action

        # Log the constructed command.
        self.logger.debug(f"Constructed command: '{full_command}'")
        return full_command

    def _execute(self, command):
        """
        Executes the constructed SCPI command. This is a placeholder that should be replaced 
        with the actual communication mechanism of the instrument.

        Args:
            command (str): The SCPI command to execute.

        Returns:
            The response from the instrument or a mock response for testing.
        """
        # Log the execution of the command.
        self.logger.info(f"Executing command: '{command}'")
        print(f"Executing: {command}")  # Placeholder for the actual execution.

        # Mock response for demonstration purposes.
        response = "Mock response"
        self.logger.debug(f"Received response: '{response}'")
        return response

    def query(self):
        """
        Queries the current value of the subsystem's SCPI command by executing a constructed query command.
        
        Returns:
            The response from the instrument for the query.
        """
        query_command = self._build_command("?")
        return self._execute(query_command)

    @property
    def value(self):
        """
        The property representing the value of the subsystem's SCPI command. Getting the property
        will query the value. Setting the property will set the value.

        Returns:
            The value of the query if getting the property.
        """
        return self.query()

    @value.setter
    def value(self, val):
        """
        Sets the value associated with the subsystem's SCPI command.

        Args:
            val: The value to set for the command.
        """
        set_command = self._build_command(f" {val}")
        self._execute(set_command)
        self._value = val  # Store the value if needed later.

    def __call__(self, val=None):
        """
        Allows the instance to be called like a function. If a value is provided, sets the value.
        Otherwise, gets the value.

        Args:
            val (optional): The value to set for the command.

        Returns:
            The value of the query if no value is provided, otherwise None after setting the value.
        """
        if val is not None:
            self.value = val
        else:
            return self.value

    def __getattr__(self, name):
        """
        Dynamically handles access to nested attributes that do not exist on the instance. This allows
        for the dynamic creation of further nested subsystems or commands.

        Args:
            name (str): The name of the attribute being accessed.

        Returns:
            A new `Subsystem` instance representing the nested subsystem or command.
        """
        if name.startswith("_"):
            raise AttributeError(f"Attribute {name} is not accessible")
        return Subsystem(self, cmd_str=name)

    def __getitem__(self, index):
        """
        Allows for indexed access to commands that require a numerical index, such as 'TRACE<n>'.
        This enables using the subsystem in an array-like fashion to specify an index for the command.

        Args:
            index (int or str): The numerical index or string label for the command.

        Returns:
            A new `Subsystem` instance representing the indexed command.
        """
        if not isinstance(index, (int, str)):
            raise TypeError("Index must be an integer or a string label")
        # Create a new subsystem with the same command string but with the provided index
        return Subsystem(self._parent, self._cmd_str, index=index)

class Acquire(Subsystem):
    """
    Manages the acquisition parameters of the oscilloscope, utilizing the dynamic capabilities
    of the `Subsystem` base class for streamlined SCPI command construction and execution.
    """

    def __init__(self, parent):
        super().__init__(parent, "ACQuire")
        # Initialize nested Subsystems correctly with 'self' as their parent
        self.mode = self.Mode(self)
        self.type = self.Type(self)
        self.sample_rate = Subsystem(self, ":SRATe")
        self.depth = Subsystem(self, ":DEPTh")
        self.count = Subsystem(self, ":COUNT")

    class Mode(Subsystem):
        def __init__(self, parent):
            super().__init__(parent, ":MODE")
        RTIM = "RTIM"
        SEGM = "SEGM"

    class Type(Subsystem):
        def __init__(self, parent):
            super().__init__(parent, ":TYPE")
        NORMAL = "NORM"
        AVERAGE = "AVER"
        HRES = "HRES"
        PEAK = "PEAK"

class WaveGen(Subsystem):
    """
    Manages the built-in waveform generator (WGEN) of the oscilloscope, harnessing
    the dynamic and streamlined SCPI command execution capabilities of the Subsystem
    base class. Controls waveform output and modulation settings with elegance and ease.
    """

    def __init__(self, parent):
        super().__init__(parent, "WGEN")
        # Initialize nested Subsystems for each waveform parameter
        self.frequency = Subsystem(self, "FREQuency")
        self.function = Subsystem(self, "FUNCtion")
        self.amplitude = Subsystem(self, "VOLTage")
        self.output = Subsystem(self, "OUTPut")
        self.offset = Subsystem(self, "VOLTage:OFFSet")

    class Function(Subsystem):
        """
        Nested Subsystem for waveform function settings.
        """
        SINusoid = 'SIN'
        SQUare = 'SQU'
        RAMP = 'RAMP'
        PULSe = 'PULS'
        NOISe = 'NOIS'
        DC = 'DC'

    class OutputState(Subsystem):
        """
        Nested Subsystem for waveform output state settings.
        """
        ON = '1'
        OFF = '0'

# Example on how to use this optimized class structure:
# wavegen = WaveGen(instrument)
# wavegen.frequency.value = 1e6  # Set frequency to 1 MHz
# wavegen.function.value = WaveGen.Function.SINusoid  # Set function to SINusoid
# wavegen.amplitude.value = 5  # Set amplitude to 5 V
# wavegen.output.value = WaveGen.OutputState.ON  # Turn the output ON
# wavegen.offset.value = 0.1  # Set offset to 0.1 V

class Timebase(Subsystem):
    """
    Manages the timebase settings of the oscilloscope, controlling the horizontal sweep functions
    with grace and precision. It's all about getting that horizontal axis dialed in just right,
    whether you're zooming in on the action or taking in the whole scene.
    """

    class Mode:
        MAIN = "MAIN"
        WINDOW = "WIND"
        XY = "XY"
        ROLL = "ROLL"

    class Reference:
        LEFT = "LEFT"
        CENTER = "CENT"
        RIGHT = "RIGHT"  # Assuming you meant to include a RIGHT or similar in your original Reference Enum

    def __init__(self, parent):
        super().__init__(parent, "TIMebase")
        self.logger = logging.getLogger(__name__)

    @property
    def mode(self):
        """
        The timebase mode, setting the stage for how you view the passage of time on your scope.
        Choose from MAIN, WINDOW, XY, or ROLL to fit the scene you're setting.
        """
        response = self.query(":MODE?")
        return self.Mode(response.strip())

    @mode.setter
    def mode(self, value):
        if value in self.Mode.__members__:
            self(self.Mode[value].value, ":MODE")
        else:
            self.logger.error(f"Invalid timebase mode: {value}")

    @property
    def position(self):
        """
        The horizontal position of the timebase, letting you shift the viewpoint left or right.
        It's like scrolling through your timeline, finding the perfect moment.
        """
        response = self.query(":POSition?")
        return float(response)

    @position.setter
    def position(self, value):
        self(value, ":POSition")

    @property
    def range(self):
        """
        The range of the timebase, essentially zooming in or out on your waveform.
        This sets the width of your time window, showing you more or less of your signal.
        """
        response = self.query(":RANGe?")
        return float(response)

    @range.setter
    def range(self, value):
        self(value, ":RANGe")

    @property
    def reference(self):
        """
        The reference position for the timebase, anchoring your view in the time domain.
        Choose from LEFT, CENTER, or RIGHT to set your baseline for the horizontal sweep.
        """
        response = self.query(":REFerence?")
        return self.Reference(response.strip())

    @reference.setter
    def reference(self, value):
        if value in self.Reference.__members__:
            self(self.Reference[value].value, ":REFerence")
        else:
            self.logger.error(f"Invalid timebase reference: {value}")

    @property
    def scale(self):
        """
        The scale of the timebase, adjusting the granularity of your temporal view.
        Dial in the detail of your waveform, making each division represent more or less time.
        """
        response = self.query(":SCALe?")
        return float(response)

    @scale.setter
    def scale(self, value):
        self(value, ":SCALe")

class Waveform(Subsystem):
    """
    Manages waveform data acquisition and processing for an oscilloscope channel.
    Utilizes the dynamic command construction and execution capabilities of the Subsystem
    base class to interact with waveform settings in an intuitive and flexible manner.
    """

    class Format(Subsystem):
        """
        Nested Subsystem for managing waveform format settings.
        """
        ASCII = 'ASC'
        WORD = 'WORD'
        BYTE = 'BYTE'

    class Source(Subsystem):
        """
        Nested Subsystem for specifying the waveform source.
        """
        CHANNEL = "CHAN"
        FUNCTION = "FUNC"
        MATH = "MATH"
        FFT = "FFT"
        WMEM = "WMEM"  # For waveform memory
        BUS1 = "BUS1"
        BUS2 = "BUS2"
        EXT = "EXT"  # External, only for 2-channel oscilloscopes

    def __init__(self, parent):
        super().__init__(parent, "WAVeform")
        self.points = self.Points(self)  # Initializing the Points nested subsystem

    class Points(Subsystem):
        """
        Manages the number of points and points mode for waveform data acquisition.
        """
        def __init__(self, parent):
            super().__init__(parent, "POINts")
            self.MODE = self.Mode(self)

        class Mode(Subsystem):
            """
            Nested Subsystem for managing points mode settings.
            """
            NORMAL = 'NORM'
            MAXIMUM = 'MAX'
            RAW = 'RAW'

            def __init__(self, parent):
                super().__init__(parent, "MODE")

    @property
    def format(self):
        """
        Gets or sets the waveform data format.
        """
        return self.query(":FORMat?")

    @format.setter
    def format(self, value):
        self(value, ":FORMat")

    @property
    def source(self):
        """
        Gets or sets the waveform data source.
        """
        return self.query(":SOURce?")

    @source.setter
    def source(self, value):
        self(value, ":SOURce")

    # Utilize the dynamically created properties for accessing and setting
    # the waveform format, source, points, and points mode.
    # The usage becomes intuitively mapped to SCPI command structures,
    # with the ability to directly set/query properties and execute commands.

# Example usage:
# waveform = Waveform(parent_instrument)
# waveform.source = Waveform.Source.CHANNEL + '1'  # Set source to CHANNEL1
# waveform.format = Waveform.Format.ASCII  # Set format to ASCII
# waveform.points = 1000  # Set points to 1000
# waveform.points.MODE = Waveform.Points.Mode.MAXIMUM  # Set points mode to MAXIMUM
