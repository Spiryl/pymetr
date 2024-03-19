import logging
logger = logging.getLogger(__name__)

import re
import numpy as np

def switch_property(cmd_str, doc_str="", access="read-write"):
    """
    Updated definition to handle boolean values directly and string representations of boolean values.
    """
    true_values = ["on", "1", "true", "yep", "aye", "yes"]
    false_values = ["off", "0", "false", "nope", "nay", "no"]

    def normalize_value_to_bool(value):
        """Normalize various representations to Python bool."""
        if isinstance(value, bool):
            return value
        try:
            value_str = str(value).lower()
            if value_str in true_values:
                return True
            elif value_str in false_values:
                return False
        except ValueError:
            pass  # If we're here, the value conversion failed
        
        raise ValueError("Invalid boolean value: {}. Use True/False or one of 'ON', 'OFF', '1', '0', 'TRUE', 'FALSE', etc.".format(value))

    def getter(self):
        response = self.instr.query(f"{self.cmd_prefix}{cmd_str}?").strip()
        logger.debug(f"Getting {self.cmd_prefix}{cmd_str}? {response}")
        # Return True or False based on the response
        return response == "1"

    def setter(self, value):
        # Normalize the input value to boolean and then convert to '1' or '0'
        normalized_value = "1" if normalize_value_to_bool(value) else "0"
        logger.debug(f"Setting {self.cmd_prefix}{cmd_str} to {normalized_value}")
        self.instr.write(f"{self.cmd_prefix}{cmd_str} {normalized_value}")

    if "read-write" in access:
        return property(fget=getter, fset=setter, doc=doc_str)
    elif "read" in access:
        return property(fget=getter, doc=doc_str)
    elif "write" in access:
        return property(fset=setter, doc=doc_str)

def value_property(cmd_str, range=None, doc_str="", access="read-write", type=None, units=""):
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
        response = self.instr.query(f"{self.cmd_prefix}{cmd_str}?").strip()
        try:
            # Cast response to specified type if 'type' is not None
            value = float(response) if type == 'float' else int(response) if type == 'int' else response
            logger.debug(f"Getting {self.cmd_prefix}{cmd_str}? {value}")
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
        
        logger.debug(f"Setting {self.cmd_prefix}{cmd_str} to {value}{units}")
        self.instr.write(f"{self.cmd_prefix}{cmd_str} {value}{units}")

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
        response = self.instr.query(f"{self.cmd_prefix}{cmd_str}?").strip()
        # Check if the response starts with any of the valid command beginnings
        for choice in choices:
            if choice.startswith(response) or response.startswith(choice):
                logger.debug(f"Getting {self.cmd_prefix}{cmd_str}? {response}")
                return choice  # return the full command string from choices list
        # If no match is found, raise an error
        logger.error(f"Unexpected response for {self.cmd_prefix}{cmd_str}? {response}")
        raise ValueError(f"Unexpected response for {self.cmd_prefix}{cmd_str}? {response}")

    def setter(self, value):
        # Find the full command string that starts with the given value (allowing abbreviations)
        match = next((choice for choice in choices if choice.startswith(value)), None)
        
        if match is not None:
            logger.debug(f"Setting {self.cmd_prefix}{cmd_str} to {match}")
            self.instr.write(f"{self.cmd_prefix}{cmd_str} {match}")
        else:
            valid_options = ', '.join(choices)
            logger.error(f"Invalid value for {self.cmd_prefix}{cmd_str}: {value}. Valid options are: {valid_options}")
            raise ValueError(f"Invalid value for {self.cmd_prefix}{cmd_str}: {value}. Valid options are: {valid_options}")

    if 'read' in access and 'write' in access:
        return property(fget=getter, fset=setter, doc=doc_str)
    elif 'read' in access:
        return property(fget=getter, doc=doc_str)
    elif 'write' in access:
        return property(fset=setter, doc=doc_str)
    
def string_property(cmd_str, doc_str="", access="read"):
    """
    Factory function to create a property for handling string responses from SCPI commands. 
    Particularly useful for commands that return comma-separated values or other string formats.
    
    Args:
        cmd_str (str): The command string associated with the property.
        doc_str (str): A brief description of the property.
        access (str): Specifies the property access level ('read', 'write', 'read-write'), though typically 'read' for such properties.

    Returns:
        property: A configured property for handling string responses.
    """
    def getter(self):
        response = self.instr.query(f"{self.cmd_prefix}{cmd_str}?")
        logger.debug(f"Getting {cmd_str} property returned string: {response}")
        return response.strip()

    def setter(self, value):
        if 'write' in access:
            self.instr.write(f"{self.cmd_prefix}{cmd_str} {value}")
            logger.debug(f"Setting {cmd_str} property to string: {value}")
        else:
            raise AttributeError(f"{cmd_str} property is read-only.")

    if 'read' in access:
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
        data_mode = self.instr._data_mode # Global instrument configuration
        data_type = self.instr._data_type # Global instrument configuration
        full_cmd_str = f"{self.cmd_prefix}{cmd_str}?"
        logger.debug(f"Getting data with command: {full_cmd_str}, format: {data_mode}, data_type: {data_type}")
        
        try:
            if data_mode == 'ASCII' and not ieee_header:
                data = self.instr.query_ascii_values(full_cmd_str, converter=converter)
                logger.debug(f"Data fetched in ASCII format with {len(data)} elements using PyVISA's automatic handling.")
                return container(data)

            elif data_mode == 'ASCII' and ieee_header:
                raw_response = self.instr.query(full_cmd_str)
                header_match = re.match(r'#(\d)(\d+)\s', raw_response)
                if header_match:
                    num_digits = int(header_match.group(1))
                    length_of_data_block = int(header_match.group(2)[:num_digits])
                    data_start = num_digits + len(str(length_of_data_block)) - 2
                    ascii_data = raw_response[data_start:].strip().split(',')
                    data = container([converter(val) for val in ascii_data])
                    logger.debug(f"Data fetched in ASCII format with {len(data)} elements using manual IEEE header parsing.")
                    return container(data)
                else:
                    raise ValueError("Failed to parse IEEE header from ASCII response.")

            elif data_mode == 'BINARY':
                # Use query_binary_values for binary data, specifying the data type dynamically
                data = self.instr.query_binary_values(full_cmd_str, datatype=data_type, container=container, is_big_endian=False)
                logger.debug(f"Data fetched in binary format with {len(data)} elements using PyVISA's automatic handling.")
                return container(data)

        except Exception as e:
            logger.error(f"Exception while fetching data: {e}")
            raise

    def setter(self, value):
        if access not in ['write', 'read-write']:
            raise AttributeError(f"{cmd_str} property is read-only.")

        try:
            data_mode = self.instr.data_mode
            data_type = self.instr.data_type
            full_cmd_str = f"{self.cmd_prefix}{cmd_str}" 
            logger.debug(f"Sending data with command: {full_cmd_str}")

            if data_mode == 'ASCII':
                self.instr.write_ascii_values(full_cmd_str, value, converter=str)
                logger.debug(f"Data sent in ASCII format: {value}")
            elif data_mode == 'BINARY':
                self.instr.write_binary_values(full_cmd_str, value, datatype=data_type)
                logger.debug(f"Data sent in binary format: {value}")
        except Exception as e:
            logger.error(f"Failed to send data with command {full_cmd_str}: {e}")
            raise e

    return property(fget=getter if 'read' in access else None,
                    fset=setter if 'write' in access else None,
                    doc=doc_str)

# Property Factories in properties.py
def reg_value_property(minor_offset, size, format='uint', mask=None, access="read-write"):
    # Factory method logic
    pass

# Property Factories in properties.py
def reg_select_property(minor_offset, size, format='uint', mask=None, access="read-write"):
    # Factory method logic
    pass

# Property Factories in properties.py
def reg_switch_property(minor_offset, size, format='uint', mask=None, access="read-write"):
    # Factory method logic
    pass