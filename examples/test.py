import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from pymetr import Instrument

# TODO modify to accept an enum for IDE autocompletion, string list won't auto complete.
def command_property(cmd_str, valid_values=None, doc_str="", read_only=False):
    """
    Factory function to create a property in a subsystem class for interacting with instrument commands.
    Supports query-only properties by disabling the setter functionality if needed.

    Args:
        cmd_str (str): The base command string associated with the property.
        valid_values (list of str, optional): A list of valid values that the property can accept. 
                                               Only relevant for settable properties.
        read_only (bool, optional): Indicates if the property is query-only. Defaults to False.
        doc_str (str): Documentation string for the property.

    Returns:
        property: A property object with custom getter and setter for instrument communication.
    """
    def getter(self):
        logging.debug(f"Getting {cmd_str}")
        return self.query(cmd_str)

    if read_only:
        setter = None
    else:
        def setter(self, value):
            if valid_values is not None and value not in valid_values:
                error_msg = f"Invalid value for {cmd_str}. Valid values are {valid_values}."
                logger.error(error_msg)
                raise ValueError(error_msg)
            logger.debug(f"Setting {cmd_str} to {value}")
            self.write(f"{cmd_str} {value}")

    return property(fget=getter, fset=setter, doc=doc_str)

# Turn this in to subsystem base class.  We don't need teh local parameters since this class should not be used by itself.
# I need to make sure that people know right away they shouldn't instatiate this class only inhereit from it.
# Is that possible?  I'd also like this class documented with doc-strings.
class Subsystem:
    # Subsystem Parameters "Using System for base example"
    date = command_property(":DATe", doc_str="The date saved in the system")
    time = command_property(":TIMe", doc_str="The time saved in the system")
    error = command_property(":ERRor", doc_str="Current error flag state", read_only=True)
    error_count = command_property(":ERRor:COUNt", doc_str="Current error state", read_only=True)

    # Base class structure
    def __init__(self, parent, cmd_prefix=":SYStem"):
        self._mode = None
        self._parent = parent
        self.cmd_prefix = cmd_prefix
    def write(self, command):
        """
        Sends a write command to the instrument, logging the command sent.

        Args:
            command (str): The command to be sent to the instrument.
        """
        full_command = f"{self.cmd_prefix}{command}"
        logger.info(f"Writing command to instrument: {full_command}")
        self._parent.write(full_command)
    def query(self, command):
        """
        Sends a query to the instrument, logs the query sent, and returns the response.

        Args:
            command (str): The query command to be sent to the instrument.

        Returns:
            str: The response from the instrument.
        """
        full_command = f"{self.cmd_prefix}{command}{'?'}"
        logger.info(f"Querying instrument with command: {full_command}")
        response = self._parent.query(full_command)
        logger.debug(f"Received response: {response}")
        return response
    
    # Example subsystem methods
    # These methods will automatically add the subsystem prefex
    def local(self):
        """Sets the instrument control to local"""
        self.write(":LOCal") # Result in :SYSTem:LOCal
    def preset(self):
        """Presets the instrument to default settings"""
        self.write(":PREset") # Result in :SYSTem:PREset
    def beep(self):
        """Issues a beep in the system"""
        self.write(":BEEper") # Result in :SYSTem:BEEPer

# TODO: Create new enum factory
        
# Everythign below here is just test code to see if its working.        
class WaveGen(Subsystem):
    FUNCTIONS = ["SIN", "SQU", "RAMP", "PULSE", "NOISE", "DC"]
    function = command_property(":FUNC", FUNCTIONS, "Waveform function")
    frequency = command_property(":FREQ", doc_str="Waveform frequency")
    
    def __init__(self, parent):
        super().__init__(parent, ":WGEN")

# Example usage
class my_inst(Instrument):
    def __init__(self, resource_string):
        super().__init__(resource_string)
        logger.info("Initializing Instrument with resource string: %s", resource_string)
        self.subsyst = Subsystem(self)  # Generic subsystem 
        self.wavegen = WaveGen(self) # Specific Subsystem 

# Instrument discovery and selection
instrument_address = Instrument.select_resources("TCPIP?*INSTR")
inst = my_inst(instrument_address)
inst.open()

# Engaging with the instrument
print(inst.identity())
print("The instruments date is: ", inst.subsyst.date)
print("The instruments time is: ", inst.subsyst.time)
print("The instruments error status: ", inst.subsyst.error)

# Specific subsystem test
print(inst.wavegen.function)
print("The wavegen frequency is: ", inst.wavegen.frequency)
inst.wavegen.frequency = '1k'
print("The wavegen frequency now is: ", inst.wavegen.frequency)

# Lets Beep!
inst.subsyst.beep()
print("The instruments error status: ", inst.subsyst.error)
inst.subsyst.preset()
inst.status()

inst.close()