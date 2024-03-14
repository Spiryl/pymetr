import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
from pymetr.instrument import Instrument

logger.setLevel(logging.DEBUG)  # Set the logger to handle DEBUG messages.
def command_property(cmd_str, valid_values=None, doc_str="Doc-string not added. Shame on you!"):
    """
    Factory function to create a property in a subsystem class for interacting with instrument commands.
    Supports handling multiple values as arguments, includes validation against a list of valid values, and
    dynamically constructs the property's docstring.

    Args:
        cmd_str (str): The base command string associated with the property.
        valid_values (list of str, optional): A list of valid values that the property can accept.
        doc_str (str): Base documentation string for the property.

    Returns:
        property: A property object with custom getter and setter for instrument communication.
    """

    # Dynamically construct the property's docstring
    value_docs = f" Valid values: {', '.join(valid_values)}." if valid_values else ""
    doc_str = f"{doc_str}{value_docs}"

    def getter(self):
        logger.debug(f"Getting value for {cmd_str}")
        return self.query(f"{cmd_str}?")

    def setter(self, *values):
        if len(values) == 1:
            value_str = str(values[0])
        else:
            value_str = ', '.join(map(str, values))

        if valid_values and not all(value in valid_values for value in values):
            error_msg = f"Invalid value(s): {values}. Valid options are: {valid_values}."
            logger.error(error_msg)
            raise ValueError(error_msg)

        logging.debug(f"Setting {cmd_str} with {value_str}")
        self.write(f"{cmd_str} {value_str}")

    return property(fget=getter, fset=setter, doc=doc_str)


class Subsystem:
    """
    Represents a subsystem of an instrument, encapsulating the logic to communicate with the instrument.
    This base class provides structured methods for sending commands and queries, complete with logging.

    Attributes:
        _parent (Instrument): Reference to the parent instrument object this subsystem communicates with.
        cmd_prefix (str): Prefix for SCPI commands specific to this subsystem, prepended to all commands.
    """
    __slots__ = ['_parent', 'cmd_prefix']

    def __init__(self, parent, cmd_prefix=""):
        self._parent = parent
        self.cmd_prefix = cmd_prefix
        self.logger = logging.getLogger(__name__)

    def write(self, command):
        """
        Sends a write command to the instrument, logging the command sent.

        Args:
            command (str): The command to be sent to the instrument.
        """
        full_command = f"{self.cmd_prefix}{command}"
        self.logger.info(f"Writing command to instrument: {full_command}")
        self._parent.write(full_command)

    def query(self, command):
        """
        Sends a query to the instrument, logs the query sent, and returns the response.

        Args:
            command (str): The query command to be sent to the instrument.

        Returns:
            str: The response from the instrument.
        """
        full_command = f"{self.cmd_prefix}{command}"
        self.logger.info(f"Querying instrument with command: {full_command}")
        response = self._parent.query(full_command)
        self.logger.debug(f"Received response: {response}")
        return response

class Timebase(Subsystem):
    """
    Handles the timebase settings of the oscilloscope, controlling the horizontal sweep functions.
    """
    MODES = ["MAIN", "WINDOW", "XY", "ROLL"]
    REFERENCES = ["LEFT", "CENTER", "RIGHT"]

    def __init__(self, parent):
        super().__init__(parent, ":TIMebase:")
        self.mode = command_property("MODE", Timebase.MODES, doc_str="Adjusts the display mode.")
        self.position = command_property("POSition", doc_str="Modifies the horizontal position on the screen.")
        self.range = command_property("RANGe", doc_str="Sets the visible time range of the waveform display.")
        self.reference = command_property("REFerence", Timebase.REFERENCES, doc_str="Determines the reference position for measurements.")
        self.scale = command_property("SCALe", doc_str="Changes the scale for time division on the display.")

# Example usage
class instrument(Instrument):
    def __init__(self, resource_string):
        super().__init__(resource_string)
        logger.info("Initializing instrument with resource string: %s", resource_string)
        self.timebase = Timebase(self)

if __name__ == "__main__":
    # # Example Usage
    inst = instrument('TCPIP0::192.168.1.111::hislip0::INSTR')  # Placeholder for actual Instrument initialization
    inst.open()

    print(inst.identity())

    inst.timebase.mode = "MAIN"  # Set mode
    print(inst.timebase.mode)  # Query mode

    inst.timebase.position = 5.0  # Set position with single value
    inst.timebase.scale = "2.5"  # Assume scale can accept a single value as string

