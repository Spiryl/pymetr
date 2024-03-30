import logging
import re
import numpy as np

logger = logging.getLogger(__name__)

class Property:
    """
    Base class for all property types.

    This class defines the basic structure and behavior of properties, including getter and setter methods.
    Subclasses should inherit from this class and implement their own specific getter and setter methods.

    Args:
        cmd_str (str): The SCPI command string associated with the property.
        doc_str (str, optional): The documentation string for the property. Defaults to an empty string.
        access (str, optional): The access mode of the property. Can be 'read', 'write', or 'read-write'. Defaults to 'read-write'.
    """
    def __init__(self, cmd_str, doc_str="", access="read-write"):
        self.cmd_str = cmd_str
        self.doc_str = doc_str
        self.access = access

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return self.getter(instance)

    def __set__(self, instance, value):
        if self.access in ["write", "read-write"]:
            self.setter(instance, value)
        else:
            raise AttributeError(f"{self.cmd_str} property is read-only.")

    def getter(self, instance):
        raise NotImplementedError("Subclasses must implement the getter method.")

    def setter(self, instance, value):
        raise NotImplementedError("Subclasses must implement the setter method.")

class SwitchProperty(Property):
    """
    Represents a switch property that can be turned on or off.

    This property handles boolean values and provides a convenient way to control switch-like settings of an instrument.
    It normalizes various boolean-like values to Python's True or False.

    Args:
        cmd_str (str): The SCPI command string associated with the switch property.
        doc_str (str, optional): The documentation string for the switch property. Defaults to an empty string.
        access (str, optional): The access mode of the switch property. Can be 'read', 'write', or 'read-write'. Defaults to 'read-write'.
    """
    def __init__(self, cmd_str, doc_str="", access="read-write"):
        super().__init__(cmd_str, doc_str, access)
        self.true_values = ["on", "1", "true", "yep", "aye", "yes"]
        self.false_values = ["off", "0", "false", "nope", "nay", "no"]

    def normalize_value_to_bool(self, value):
        if isinstance(value, bool):
            return value
        try:
            value_str = str(value).lower()
            if value_str in self.true_values:
                return True
            elif value_str in self.false_values:
                return False
        except ValueError:
            pass
        raise ValueError(f"Invalid boolean value: {value}. Use True/False or one of {', '.join(self.true_values + self.false_values)}")

    def getter(self, instance):
        response = instance.instr.query(f"{instance.cmd_prefix}{self.cmd_str}?").strip()
        logger.debug(f"Getting {instance.cmd_prefix}{self.cmd_str}? {response}")
        return response == "1"

    def setter(self, instance, value):
        normalized_value = "1" if self.normalize_value_to_bool(value) else "0"
        logger.debug(f"Setting {instance.cmd_prefix}{self.cmd_str} to {normalized_value}")
        instance.instr.write(f"{instance.cmd_prefix}{self.cmd_str} {normalized_value}")

class ValueProperty(Property):
    """
    Represents a numeric value property with optional range and unit validation.

    This property handles numeric values (float or int) and ensures they fall within a specified range if provided.
    It also supports specifying the units of the value for better readability and validation.

    Args:
        cmd_str (str): The SCPI command string associated with the value property.
        range (tuple, optional): A tuple specifying the minimum and maximum allowed values for the property. Defaults to None.
        doc_str (str, optional): The documentation string for the value property. Defaults to an empty string.
        access (str, optional): The access mode of the value property. Can be 'read', 'write', or 'read-write'. Defaults to 'read-write'.
        type (str, optional): The type of the value. Can be 'float', 'int', or None. Defaults to None.
        units (str, optional): The units of the value. Defaults to an empty string.
    """
    def __init__(self, cmd_str, range=None, doc_str="", access="read-write", type=None, units=""):
        super().__init__(cmd_str, doc_str, access)
        self.range = range
        self.type = type
        self.units = units

    def getter(self, instance):
        response = instance.instr.query(f"{instance.cmd_prefix}{self.cmd_str}?").strip()
        try:
            value = float(response) if self.type == 'float' else int(response) if self.type == 'int' else response
            logger.debug(f"Getting {instance.cmd_prefix}{self.cmd_str}? {value}")
            return value
        except ValueError:
            logger.error(f"Invalid numerical response for {instance.cmd_prefix}{self.cmd_str}? {response}")
            raise

    def setter(self, instance, value):
        if self.type == 'float':
            try:
                value = float(value)
            except ValueError:
                raise ValueError(f"Value for {instance.cmd_prefix}{self.cmd_str} must be a float: {value}")
        elif self.type == 'int':
            try:
                value = int(value)
            except ValueError:
                raise ValueError(f"Value for {instance.cmd_prefix}{self.cmd_str} must be an int: {value}")

        min_value, max_value = self.range if self.range else (None, None)
        if min_value is not None and value < min_value or max_value is not None and value > max_value:
            raise ValueError(f"Value for {instance.cmd_prefix}{self.cmd_str} must be between {min_value}{self.units} and {max_value}{self.units}: {value}{self.units}")

        logger.debug(f"Setting {instance.cmd_prefix}{self.cmd_str} to {value}{self.units}")
        instance.instr.write(f"{instance.cmd_prefix}{self.cmd_str} {value}{self.units}")

class SelectProperty(Property):
    """
    Represents a property that allows selecting from a predefined set of choices.

    This property provides a convenient way to handle instrument settings that have a limited set of valid options.
    It ensures that only valid choices are accepted and allows for easy selection by providing partial matches.

    Args:
        cmd_str (str): The SCPI command string associated with the select property.
        choices (list): A list of valid choices for the property.
        doc_str (str, optional): The documentation string for the select property. Defaults to an empty string.
        access (str, optional): The access mode of the select property. Can be 'read', 'write', or 'read-write'. Defaults to 'read-write'.
    """
    def __init__(self, cmd_str, choices, doc_str="", access="read-write"):
        super().__init__(cmd_str, doc_str, access)
        self.choices = choices

    def getter(self, instance):
        response = instance.instr.query(f"{instance.cmd_prefix}{self.cmd_str}?").strip()
        for choice in self.choices:
            if choice.startswith(response) or response.startswith(choice):
                logger.debug(f"Getting {instance.cmd_prefix}{self.cmd_str}? {response}")
                return choice
        logger.error(f"Unexpected response for {instance.cmd_prefix}{self.cmd_str}? {response}")
        raise ValueError(f"Unexpected response for {instance.cmd_prefix}{self.cmd_str}? {response}")

    def setter(self, instance, value):
        match = next((choice for choice in self.choices if choice.startswith(value)), None)
        if match is not None:
            logger.debug(f"Setting {instance.cmd_prefix}{self.cmd_str} to {match}")
            instance.instr.write(f"{instance.cmd_prefix}{self.cmd_str} {match}")
        else:
            valid_options = ', '.join(self.choices)
            logger.error(f"Invalid value for {instance.cmd_prefix}{self.cmd_str}: {value}. Valid options are: {valid_options}")
            raise ValueError(f"Invalid value for {instance.cmd_prefix}{self.cmd_str}: {value}. Valid options are: {valid_options}")

class StringProperty(Property):
    """
    Represents a string property for handling string-based instrument settings.

    This property is useful for settings that return or accept string values, such as instrument identifiers or custom commands.

    Args:
        cmd_str (str): The SCPI command string associated with the string property.
        doc_str (str, optional): The documentation string for the string property. Defaults to an empty string.
        access (str, optional): The access mode of the string property. Can be 'read', 'write', or 'read-write'. Defaults to 'read'.
    """
    def getter(self, instance):
        response = instance.instr.query(f"{instance.cmd_prefix}{self.cmd_str}?")
        logger.debug(f"Getting {self.cmd_str} property returned string: {response}")
        return response.strip()

    def setter(self, instance, value):
        if 'write' in self.access:
            instance.instr.write(f"{instance.cmd_prefix}{self.cmd_str} {value}")
            logger.debug(f"Setting {self.cmd_str} property to string: {value}")
        else:
            raise AttributeError(f"{self.cmd_str} property is read-only.")

class DataProperty(Property):
    """
    Represents a property for handling instrument data, such as waveforms or measurement results.

    This property supports fetching data in various formats (ASCII, binary) and provides options for handling IEEE headers and data conversion.

    Args:
        cmd_str (str): The SCPI command string associated with the data property.
        access (str, optional): The access mode of the data property. Can be 'read', 'write', or 'read-write'. Defaults to 'read-write'.
        doc_str (str, optional): The documentation string for the data property. Defaults to an empty string.
        container (type, optional): The container type to use for the data, e.g., numpy.array. Defaults to numpy.array.
        converter (callable, optional): A function to convert the data elements to the desired type. Defaults to float.
        ieee_header (bool, optional): Specifies whether the instrument's response includes an IEEE header. Defaults to False.
    """
    def __init__(self, cmd_str, access='read-write', doc_str="", container=np.array, converter=float, ieee_header=False):
        super().__init__(cmd_str, doc_str, access)
        self.container = container
        self.converter = converter
        self.ieee_header = ieee_header

    def getter(self, instance):
        data_mode = instance.instr._data_mode
        data_type = instance.instr._data_type
        full_cmd_str = f"{instance.cmd_prefix}{self.cmd_str}?"
        logger.debug(f"Getting data with command: {full_cmd_str}, format: {data_mode}, data_type: {data_type}")

        try:
            if data_mode == 'ASCII' and not self.ieee_header:
                data = instance.instr.query_ascii_values(full_cmd_str, converter=self.converter)
                logger.debug(f"Data fetched in ASCII format with {len(data)} elements using PyVISA's automatic handling.")
                return self.container(data)

            elif data_mode == 'ASCII' and self.ieee_header:
                raw_response = instance.instr.query(full_cmd_str)
                header_match = re.match(r'#(\d)(\d+)\s', raw_response)
                if header_match:
                    num_digits = int(header_match.group(1))
                    length_of_data_block = int(header_match.group(2)[:num_digits])
                    data_start = num_digits + len(str(length_of_data_block)) - 2
                    ascii_data = raw_response[data_start:].strip().split(',')
                    data = self.container([self.converter(val) for val in ascii_data])
                    logger.debug(f"Data fetched in ASCII format with {len(data)} elements using manual IEEE header parsing.")
                    return self.container(data)
                else:
                    raise ValueError("Failed to parse IEEE header from ASCII response.")

            elif data_mode == 'BINARY':
                data = instance.instr.query_binary_values(full_cmd_str, datatype=data_type, container=self.container, is_big_endian=False)
                logger.debug(f"Data fetched in binary format with {len(data)} elements using PyVISA's automatic handling.")
                return self.container(data)

        except Exception as e:
            logger.error(f"Exception while fetching data: {e}")
            raise

    def setter(self, instance, value):
        if self.access not in ['write', 'read-write']:
            raise AttributeError(f"{self.cmd_str} property is read-only.")

        try:
            data_mode = instance.instr.data_mode
            data_type = instance.instr.data_type
            full_cmd_str = f"{instance.cmd_prefix}{self.cmd_str}"
            logger.debug(f"Sending data with command: {full_cmd_str}")

            if data_mode == 'ASCII':
                instance.instr.write_ascii_values(full_cmd_str, value, converter=str)
                logger.debug(f"Data sent in ASCII format: {value}")
            elif data_mode == 'BINARY':
                instance.instr.write_binary_values(full_cmd_str, value, datatype=data_type)
                logger.debug(f"Data sent in binary format: {value}")
        except Exception as e:
            logger.error(f"Failed to send data with command {full_cmd_str}: {e}")
            raise e