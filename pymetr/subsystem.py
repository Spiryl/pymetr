
from enum import Enum
import logging
logger = logging.getLogger(__name__)

def command_property(cmd_str, valid_values=None, doc_str="", read_only=False):
    """
    Factory function to create a property in a subsystem class for interacting with instrument commands.
    This version has been enhanced to accept enums directly for the 'valid_values' parameter, enabling
    setting properties with enum members without needing to access their .value attribute.

    Args:
        cmd_str (str): The base command string associated with the property.
        valid_values (Enum, optional): An Enum class of valid values that the property can accept.
                                        Only relevant for settable properties. Can handle Enum directly now.
        read_only (bool, optional): Indicates if the property is query-only. Defaults to False.
        doc_str (str): Documentation string for the property.

    Returns:
        property: A property object with custom getter and setter for instrument communication.
    """
    def getter(self):
        logger.debug(f"Getting {cmd_str}")
        return self.query(cmd_str)

    if read_only:
        setter = None
    else:
        def setter(self, value):
            # If value is an instance of Enum, extract the value using .value
            if isinstance(value, Enum):
                value = value.value
            # Now, check if the value is in the valid_values Enum by converting Enum to list of values
            if valid_values is not None and value not in [v.value for v in valid_values]:
                error_msg = f"Invalid value for {cmd_str}. Valid values are {[v.value for v in valid_values]}."
                logger.error(error_msg)
                raise ValueError(error_msg)
            logger.debug(f"Setting {cmd_str} to {value}")
            self.write(f"{cmd_str} {value}")

    return property(fget=getter, fset=setter, doc=doc_str)

def command_options(name, options):
    """
    Dynamically creates an Enum class with given options. This method simplifies the process of defining command parameters,
    making it intuitive and efficient for instrument coders. By using enums, we ensure that the options are not only clearly defined
    but also offer auto-completion support in IDEs, enhancing the coding experience.

    Args:
        name (str): The name of the Enum class to be created. This should be a meaningful and descriptive name related to the command options it represents.
        options (list of str): A list of strings, where each string is a valid option that the command can accept. These options will be the members of the Enum class.

    Returns:
        Enum: A dynamically created Enum class with members corresponding to the provided options.
    """
    return Enum(name, {option: option for option in options})

class Subsystem:
    """
    Base class for creating instrument subsystems. This class is designed to be inherited by specific subsystem classes,
    providing them with the ability to send queries and commands to the instrument.

    This class should not be instantiated directly but extended by specific instrument subsystems.
    """

    def __init__(self, parent, cmd_prefix=""):
        """
        Initializes the subsystem with a reference to its parent instrument and an optional command prefix.

        Args:
            parent (Instrument): The parent instrument object this subsystem belongs to.
            cmd_prefix (str, optional): The command prefix for this subsystem. Defaults to an empty string.
        """
        self._parent = parent
        self.cmd_prefix = cmd_prefix

    def write(self, command):
        """
        Sends a command to the instrument.

        Args:
            command (str): The command to send to the instrument.
        """
        full_command = f"{self.cmd_prefix}{command}"
        self._parent.write(full_command)
        logger.info(f"Command sent: {full_command}")

    def query(self, command):
        """
        Sends a query to the instrument and returns the response.

        Args:
            command (str): The query command to send to the instrument.

        Returns:
            str: The response from the instrument.
        """
        full_command = f"{self.cmd_prefix}{command}?"
        response = self._parent.query(full_command)
        logger.info(f"Query sent: {full_command}")
        logger.debug(f"Response received: {response}")
        return response

    def read(self):
        """
        Reads the response from the instrument's output buffer.

        Returns:
            str: The response from the instrument.
        """
        response = self._parent.read()
        logger.debug("Response read from the instrument.")
        return response