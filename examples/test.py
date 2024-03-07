import logging

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from pymetr import Instrument

def command_property(cmd_str, valid_values=None, doc_str=""):
    def getter(self):
        full_cmd = f"{self.cmd_prefix}{cmd_str}?"
        logging.debug(f"Getting {full_cmd}")
        return self.query(full_cmd)

    def setter(self, value):
        full_cmd = f"{self.cmd_prefix}{cmd_str}{'\n\r'}"
        if valid_values is not None and value not in valid_values:
            error_msg = f"Invalid value for {full_cmd}. Valid values are {valid_values}."
            logger.error(error_msg)
            raise ValueError(error_msg)
        logger.debug(f"Setting {full_cmd} to {value}")
        self.write(f"{full_cmd} {value}")

    return property(fget=getter, fset=setter, doc=doc_str)

# Turn this in to subsystem base class.
class Subsystem:
    # Simplified for demonstration
    mode = command_property("MODE", doc_str="The mode of the subsystem")

    def __init__(self, parent, cmd_prefix):
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
        full_command = f"{self.cmd_prefix}{command}"
        logger.info(f"Querying instrument with command: {full_command}")
        response = self._parent.query(full_command)
        self.logger.debug(f"Received response: {response}")
        return response

# Example usage
class my_inst(Instrument):
    def __init__(self, resource_string):
        super().__init__(resource_string)
        logger.info("Initializing Oscilloscope with resource string: %s", resource_string)
        self.subsyst = Subsystem(self, ":")

# Instrument discovery and selection
instrument_address = Instrument.select_resources("TCPIP?*")
inst = my_inst(instrument_address)
inst.open()

# Engaging with the instrument
print(inst.identity())

inst.subsyst.mode = "MAIN"  # This should trigger the setter
print(inst.subsyst.mode)  # This should trigger the getter

# Attempting to set an invalid mode value
try:
    inst.subsyst.mode = "INVALID"
except ValueError as e:
    print(e)
