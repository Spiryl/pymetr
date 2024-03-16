# properties.py
from enum import Enum
import re
import logging
import numpy as np
logger = logging.getLogger(__name__)
    
def switch_property(cmd_str, doc_str="", access="read-write"):
    """
    Updated definition to handle boolean values directly and string representations of boolean values.
    """
    true_values = ["on", "1", "true", "yep", "aye", "yes"]
    false_values = ["off", "0", "false", "nope", "nay", "no"]

    def normalize_value(value):
        # Directly handle boolean types
        if isinstance(value, bool):
            return "ON" if value else "OFF"
        
        # If it's not a boolean, proceed with string normalization
        try:
            value_lower = value.lower()
            if value_lower in true_values:
                return "ON"
            elif value_lower in false_values:
                return "OFF"
        except AttributeError:
            pass  # If we're here, the value wasn't a string or bool; fall through to the ValueError
        
        raise ValueError(f"Invalid boolean value: {value}. Use True/False or one of 'ON', 'OFF', '1', '0', 'TRUE', 'FALSE', etc.")

    def getter(self):
        response = self._parent.query(f"{self.cmd_prefix}{cmd_str}?").strip().upper()
        logger.info(f"Getting {self.cmd_prefix}{cmd_str}? {response}")
        return response == "ON"

    def setter(self, value):
        normalized_value = normalize_value(value)
        logger.info(f"Setting {self.cmd_prefix}{cmd_str} to {normalized_value}")
        self._parent.write(f"{self.cmd_prefix}{cmd_str} {normalized_value}")

    if "read-write" in access:
        return property(fget=getter, fset=setter, doc=doc_str)
    elif "read" in access:
        return property(fget=getter, doc=doc_str)
    elif "write" in access:
        return property(fset=setter, doc=doc_str)

def value_property(cmd_str, range=None, doc_str="", access="read-write", type=None, units=None):
    """
    Creates a property for handling numerical values, ensuring they fall within specified ranges if provided,
    and optionally enforcing a specific numerical type (float or int).

    Args:
        cmd_str (str): The base command string for the property.
        range (list of float|int, optional): A list specifying the minimum and maximum acceptable values for the property.
                                             Defaults to None, which means no constraints.
        doc_str (str): Documentation string for the property.
        access (str): Specifies the access type for the property ('read', 'write', 'read-write').
        type (str, optional): The type of the value ('float', 'int', None). Specifies if the value should be 
                              explicitly cast or checked against a certain type.

    Returns:
        property: A property object with custom getter and setter for numerical communication.
    """
    def getter(self):
        response = self._parent.query(f"{self.cmd_prefix}{cmd_str}?").strip()
        try:
            # Cast response to specified type if 'type' is not None
            value = float(response) if type == 'float' else int(response) if type == 'int' else response
            logger.info(f"Getting {self.cmd_prefix}{cmd_str}? {value}")
            return value
        except ValueError:
            logger.error(f"Invalid numerical response for {self.cmd_prefix}{cmd_str}? {response}")
            raise

    def setter(self, value):
        # Type checking and conversion if 'type' is specified
        if type == 'float':
            try:
                value = float(value)
            except ValueError:
                raise ValueError(f"Value for {self.cmd_prefix}{cmd_str} must be a float: {value}")
        elif type == 'int':
            try:
                value = int(value)
            except ValueError:
                raise ValueError(f"Value for {self.cmd_prefix}{cmd_str} must be an int: {value}")

        # Value range checking if 'range' is specified
        min_value, max_value = range if range else (None, None)
        if min_value is not None and value < min_value or max_value is not None and value > max_value:
            logger.error(f"Value for {self.cmd_prefix}{cmd_str} must be between {min_value}{units} and {max_value}{units}: {value}{units}")
            raise ValueError(f"Value for {self.cmd_prefix}{cmd_str} must be between {min_value}{units} and {max_value}{units}: {value}{units}")
        
        logger.info(f"Setting {self.cmd_prefix}{cmd_str} to {value}{units}")
        self._parent.write(f"{self.cmd_prefix}{cmd_str} {value}{units}")

    if "read-write" in access:
        return property(fget=getter, fset=setter, doc=doc_str)
    elif "read" in access:
        return property(fget=getter, doc=doc_str)
    elif "write" in access:
        return property(fset=setter, doc=doc_str)

def select_property(cmd_str, choices, doc_str="", access="read-write"):
    """
    Creates a property for selecting from a list of string options.
    This simplifies interaction with instrument settings by directly specifying acceptable values.

    Args:
        cmd_str (str): The command string associated with the property.
        choices (list of str): A list defining valid options for the property.
        doc_str (str): A brief description of the property.
        access (str): Specifies the property access level ('read', 'write', 'read-write').

    Returns:
        property: A configured property for handling selection from a list of strings.
    """
    def getter(self):
        response = self._parent.query(f"{self.cmd_prefix}{cmd_str}?").strip()
        if response in choices:
            logger.info(f"Getting {self.cmd_prefix}{cmd_str}? {response}")
            return response
        else:
            logger.error(f"Unexpected response for {self.cmd_prefix}{cmd_str}? {response}")
            raise ValueError(f"Unexpected response for {self.cmd_prefix}{cmd_str}? {response}")

    def setter(self, value):
        if value in choices:
            logger.info(f"Setting {self.cmd_prefix}{cmd_str} to {value}")
            self._parent.write(f"{self.cmd_prefix}{cmd_str} {value}")
        else:
            logger.error(f"Invalid value for {self.cmd_prefix}{cmd_str}: {value}")
            raise ValueError(f"Invalid value for {self.cmd_prefix}{cmd_str}: {value}")

    if 'read' in access and 'write' in access:
        return property(fget=getter, fset=setter, doc=doc_str)
    elif 'read' in access:
        return property(fget=getter, doc=doc_str)
    elif 'write' in access:
        return property(fset=setter, doc=doc_str)
    
def data_property(cmd_str, access='read-write', doc_str="", container=np.array, converter=float, ieee_header=False):
    """
    Factory function to create a data handling property for SCPI commands that deal with data,
    with options to handle IEEE headers for ASCII data, support for writing data, and customization for binary data types.

    Args:
        cmd_str (str): The base command string for the property.
        access (str, optional): Specifies the property access mode ('read', 'write', 'read-write'). Defaults to 'read-write'.
        container (type, optional): Container type to use for the data, e.g., numpy.array. Defaults to numpy.array.
        converter (callable, optional): A function to convert data to/from the desired format. Defaults to float.
        ieee_header (bool, optional): Specifies whether the instrument's response includes an IEEE header for ASCII data. Defaults to False.
        data_type (str, optional): The data type for binary data, following Python's struct module notation. Defaults to 'B' (unsigned byte).

    Returns:
        property: A custom property object for instrument communication.
    """
    def getter(self):
        data_format = self._parent.data_format
        data_type = self._parent.data_type
        full_cmd_str = f"{self.cmd_prefix}{cmd_str}?"  # Include cmd_prefix
        
        try:
            if data_format == 'ASCII' and not ieee_header:
                # Directly use query_ascii_values for ASCII data without IEEE header
                data = self._parent.query_ascii_values(full_cmd_str, converter=converter)
                logger.info(f"Data fetched in ASCII format with {len(data)} elements using PyVISA's automatic handling.")
                return container(data)

            elif data_format == 'ASCII' and ieee_header:
                # Manually handle the IEEE header for ASCII data
                raw_response = self._parent.query(full_cmd_str)
                header_match = re.match(r'#(\d)(\d+)\s', raw_response)
                if header_match:
                    num_digits = int(header_match.group(1))
                    length_of_data_block = int(header_match.group(2)[:num_digits])
                    data_start = num_digits + len(str(length_of_data_block)) - 2
                    ascii_data = raw_response[data_start:].strip().split(',')
                    data = container([converter(val) for val in ascii_data])
                    logger.info(f"Data fetched in ASCII format with {len(data)} elements using manual IEEE header parsing.")
                    return data
                else:
                    raise ValueError("Failed to parse IEEE header from ASCII response.")

            elif data_format == 'BINARY':
                # Use query_binary_values for binary data, specifying the data type dynamically
                data = self._parent.query_binary_values(full_cmd_str, datatype=data_type, is_big_endian=False)
                logger.info(f"Data fetched in binary format with {len(data)} elements using PyVISA's automatic handling.")
                return container(data)

        except Exception as e:
            logger.error(f"Exception while fetching data: {e}")
            raise

    def setter(self, value):
        if access not in ['write', 'read-write']:
            raise AttributeError(f"{cmd_str} property is read-only.")

        try:
            data_format = self._parent.data_format
            data_type = self._parent.data_type
            full_cmd_str = f"{self.cmd_prefix}{cmd_str}"  # Include cmd_prefix
            logger.info(f"Sending data with command: {full_cmd_str}")

            if data_format == 'ASCII':
                # Use write_ascii_values for ASCII data
                self._parent.write_ascii_values(full_cmd_str, value, converter=str)
                logger.info(f"Data sent in ASCII format: {value}")
            elif data_format == 'BINARY':
                # Use write_binary_values for binary data, specifying the data type dynamically
                self._parent.write_binary_values(full_cmd_str, value, datatype=data_type)
                logger.info(f"Data sent in binary format: {value}")
        except Exception as e:
            logger.error(f"Failed to send data with command {full_cmd_str}: {e}")
            raise e

    return property(fget=getter if 'read' in access else None,
                    fset=setter if 'write' in access else None,
                    doc=doc_str)

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

def command_property(cmd_str, valid_values=None, doc_str="", access="read-write"):
    """
    Factory function to create a property in a subsystem class for interacting with instrument commands.
    Enhanced to accept enums directly for 'valid_values' and allows specifying access type.

    Args:
        cmd_str (str): The base command string for the property.
        valid_values (Enum, optional): Enum of valid values for settable properties.
        doc_str (str): Documentation string for the property.
        access (str, optional): Specifies the access type for the property ('read', 'write', 'read-write').

    Returns:
        property: A property object with custom getter and setter for instrument communication.
    """
    def getter(self):
        # Adjust to include cmd_prefix
        full_cmd_str = f"{self.cmd_prefix}{cmd_str}{'?'}"
        if "read" in access:
            response = self._parent.query(full_cmd_str).strip()
            logger.info(f"Getting {full_cmd_str}, Response = {response}")
            return response.strip()
        else:
            raise AttributeError(f"{full_cmd_str} property is write-only.")

    def setter(self, value):
        # Adjust to include cmd_prefix
        full_cmd_str = f"{self.cmd_prefix}{cmd_str}"
        if "write" in access:
            if isinstance(value, Enum):
                value = value.name  # Use the enum's name instead of its numeric value
            if valid_values is not None and value not in [v.name for v in valid_values]:
                error_msg = f"Invalid value for {full_cmd_str}. Valid values are {[v.name for v in valid_values]}."
                logger.error(error_msg)
                raise ValueError(error_msg)
            logger.info(f"Setting {full_cmd_str} to {value}")
            self._parent.write(f"{full_cmd_str} {value}")
        else:
            raise AttributeError(f"{full_cmd_str} property is read-only.")

    if access == "read":
        return property(fget=getter, doc=doc_str)
    elif access == "write":
        return property(fset=setter, doc=doc_str)
    else:
        return property(fget=getter, fset=setter, doc=doc_str)