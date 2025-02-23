
"""
SCPI Property System - Simplified Implementation

This module provides descriptor classes for handling SCPI instrument properties.
Each property class implements specific behavior for different types of instrument
settings while relying on the base Instrument class for communication handling.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Optional, Union, Tuple, List, Type, Callable
from enum import Enum
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class PropertyResponse:
    """
    Tracks the response and status of property operations.

    Attributes:
        value: The converted/processed value from the instrument
        raw_response: The raw string response from the instrument
        success: Whether the operation completed successfully
        error: Error message if the operation failed
    """
    value: Any = None
    raw_response: str = ""
    success: bool = True
    error: Optional[str] = None

class Property(ABC):
    """
    Base class for all SCPI property descriptors.

    This class implements the descriptor protocol and provides basic functionality
    for getting and setting SCPI instrument properties. It relies on the instrument's
    write/read/query methods for communication.

    Args:
        cmd_str: The SCPI command string associated with this property
        doc_str: Documentation string describing the property
        access: Access mode ('read', 'write', or 'read-write')
        join_char: Character used to join command and value
    """

    def __init__(self, cmd_str: str, doc_str: str = "", access: str = "read-write", join_char: str = " "):
        logger.debug(f"Initializing Property with cmd_str='{cmd_str}', access='{access}'")
        self.cmd_str = cmd_str
        self.doc_str = doc_str
        self.access = access.lower()
        self.join_char = join_char
        self.last_response = PropertyResponse()

    def __get__(self, instance, owner):
        """Descriptor get implementation."""
        if instance is None:
            logger.debug(f"Property accessed on class, returning self")
            return self
            
        if self.access not in ["read", "read-write"]:
            msg = f"Property '{self.cmd_str}' is write-only"
            logger.error(msg)
            raise AttributeError(msg)
            
        return self.getter(instance)

    def __set__(self, instance, value):
        """Descriptor set implementation."""
        if self.access not in ["write", "read-write"]:
            msg = f"Property '{self.cmd_str}' is read-only"
            logger.error(msg)
            raise AttributeError(msg)
            
        self.setter(instance, value)

    @abstractmethod
    def getter(self, instance) -> Any:
        """Abstract getter method to be implemented by subclasses."""
        pass

    @abstractmethod
    def setter(self, instance, value):
        """Abstract setter method to be implemented by subclasses."""
        pass

class ValueProperty(Property):
    """
    Numeric property with range validation and unit handling.

    Args:
        cmd_str: SCPI command string
        type: Data type ('float' or 'int')
        range: Optional tuple of (min, max) values
        units: Optional unit string to append to values
        doc_str: Documentation string
        access: Access mode ('read', 'write', or 'read-write')
        join_char: Character used to join command and value
    """

    def __init__(self, cmd_str: str, type: str = None, range: Optional[Tuple] = None,
                 units: str = "", doc_str: str = "", access: str = "read-write",
                 join_char: str = " "):
        super().__init__(cmd_str, doc_str, access, join_char)
        self.type = type
        self.range = range
        self.units = units
        logger.debug(
            f"Initialized ValueProperty: type='{type}', range={range}, "
            f"units='{units}'"
        )

    def _validate_value(self, value: Any) -> Union[float, int]:
        """
        Validate and convert a value according to type and range constraints.

        Args:
            value: Value to validate and convert

        Returns:
            Converted and validated value
        """
        logger.debug(f"Validating value: {value}")
        try:
            # Convert value to proper type
            if self.type == "float":
                value = float(value)
            elif self.type == "int":
                value = int(float(value))  # Handle scientific notation
            else:
                value = value  # No conversion if type is None

            # Check range if specified
            if self.range:
                min_val, max_val = self.range
                if (min_val is not None and value < min_val) or \
                   (max_val is not None and value > max_val):
                    msg = f"Value {value} outside range [{min_val}, {max_val}]"
                    logger.error(msg)
                    raise ValueError(msg)

            logger.debug(f"Value {value} validated successfully")
            return value

        except (ValueError, TypeError) as e:
            msg = f"Validation error for '{value}': {str(e)}"
            logger.error(msg)
            raise ValueError(msg)

    def getter(self, instance) -> Union[float, int]:
        """Get the current numeric value from the instrument."""
        logger.debug(f"Getting value for '{self.cmd_str}'")
        try:
            response = instance.query(f"{self.cmd_str}?")
            value = self._validate_value(response)
            self.last_response = PropertyResponse(
                value=value,
                raw_response=response
            )
            return value
        except Exception as e:
            logger.error(f"Error in getter for '{self.cmd_str}': {e}")
            self.last_response = PropertyResponse(
                success=False,
                error=str(e)
            )
            raise

    def setter(self, instance, value):
        """Set a numeric value on the instrument."""
        logger.debug(f"Setting '{self.cmd_str}' to {value}")
        try:
            validated_value = self._validate_value(value)
            command = f"{self.cmd_str}{self.join_char}{validated_value}{self.units}"
            instance.write(command)
            self.last_response = PropertyResponse(
                value=validated_value,
                raw_response=command
            )
        except Exception as e:
            logger.error(f"Error in setter for '{self.cmd_str}': {e}")
            self.last_response = PropertyResponse(
                success=False,
                error=str(e)
            )
            raise

class SwitchProperty(Property):
    """
    Boolean property with configurable true/false representation.
    
    Args:
        cmd_str: SCPI command string
        doc_str: Documentation string
        format: Format for sending values ('ON_OFF', 'TRUE_FALSE', '1_0')
        access: Access mode ('read', 'write', or 'read-write')
        join_char: Character used to join command and value
    """

    # Define standard format mappings
    FORMAT_MAPS = {
        'ON_OFF': {'true': 'ON', 'false': 'OFF'},
        'TRUE_FALSE': {'true': 'TRUE', 'false': 'FALSE'},
        '1_0': {'true': '1', 'false': '0'}
    }

    def __init__(self, cmd_str: str, doc_str: str = "", format: str = '1_0', 
                 access: str = "read-write", join_char: str = " "):
        super().__init__(cmd_str, doc_str, access, join_char)
        
        # Validate and set format
        format = format.upper()
        if format not in self.FORMAT_MAPS:
            raise ValueError(f"Invalid format '{format}'. Must be one of: {list(self.FORMAT_MAPS.keys())}")
        self.format = format
        
        # Define accepted input values (case-insensitive)
        self.true_values = {'on', '1', 'true', 'yes'}
        self.false_values = {'off', '0', 'false', 'no'}
        logger.debug(f"Initialized SwitchProperty with format '{format}'")

    def _convert_to_bool(self, value: Union[str, bool]) -> bool:
        """Convert various inputs to boolean values."""
        if isinstance(value, bool):
            return value
            
        value_str = str(value).lower().strip()
        if value_str in self.true_values:
            return True
        if value_str in self.false_values:
            return False
            
        raise ValueError(f"Invalid boolean value: '{value}'")

    def _format_bool(self, value: bool) -> str:
        """Convert boolean to the configured string format."""
        return self.FORMAT_MAPS[self.format]['true' if value else 'false']

    def getter(self, instance) -> bool:
        """Get the current boolean state from the instrument."""
        logger.debug(f"Getting boolean value for '{self.cmd_str}'")
        try:
            response = instance.query(f"{self.cmd_str}?")
            value = self._convert_to_bool(response)
            self.last_response = PropertyResponse(
                value=value,
                raw_response=response
            )
            return value
        except Exception as e:
            logger.error(f"Error in getter for '{self.cmd_str}': {e}")
            self.last_response = PropertyResponse(
                success=False,
                error=str(e)
            )
            raise

    def setter(self, instance, value):
        """Set a boolean value on the instrument."""
        logger.debug(f"Setting '{self.cmd_str}' to {value}")
        try:
            bool_value = self._convert_to_bool(value)
            formatted_value = self._format_bool(bool_value)
            command = f"{self.cmd_str}{self.join_char}{formatted_value}"
            instance.write(command)
            self.last_response = PropertyResponse(
                value=bool_value,
                raw_response=command
            )
        except Exception as e:
            logger.error(f"Error in setter for '{self.cmd_str}': {e}")
            self.last_response = PropertyResponse(
                success=False,
                error=str(e)
            )
            raise

class SelectProperty(Property):
    """
    Property that handles selection from a predefined set of choices.

    Args:
        cmd_str: SCPI command string
        choices: List of valid choices (strings) or Enum class
        doc_str: Documentation string
        access: Access mode ('read', 'write', or 'read-write')
        join_char: Character used to join command and value
    """

    def __init__(self, cmd_str: str, choices: Union[List[str], Type[Enum]], 
                 doc_str: str = "", access: str = "read-write", join_char: str = " "):
        super().__init__(cmd_str, doc_str, access, join_char)
        
        # Handle both enum and list inputs
        self.enum_class = None
        if isinstance(choices, type) and issubclass(choices, Enum):
            self.enum_class = choices
            self.choices = [e.value for e in choices]
        else:
            self.choices = [str(c) for c in choices]
            
        logger.debug(f"Initialized SelectProperty with choices: {self.choices}")

    def _find_match(self, value: Union[str, Enum]) -> str:
        """Find the best match for a value in the choices list."""
        logger.debug(f"Finding match for value: {value}")
        
        # Handle enum input
        if isinstance(value, Enum):
            logger.debug(f"Value is an Enum: {value}")
            return value.value

        # Handle string input
        value_str = str(value).strip().upper()
        logger.debug(f"Normalized string value: {value_str}")
        
        # Create normalized versions of choices for comparison
        norm_choices = {c.strip().upper(): c for c in self.choices}
        
        # Try exact match first
        if value_str in norm_choices:
            logger.debug(f"Found exact match: {norm_choices[value_str]}")
            return norm_choices[value_str]
            
        # Try prefix match
        matches = [
            orig for norm, orig in norm_choices.items()
            if norm.startswith(value_str) or value_str.startswith(norm)
        ]
        
        if len(matches) == 1:
            logger.debug(f"Found unique prefix match: {matches[0]}")
            return matches[0]
            
        if not matches:
            msg = f"Invalid choice: '{value}'. Valid options: {', '.join(self.choices)}"
            logger.error(msg)
            raise ValueError(msg)
        else:
            msg = f"Ambiguous value '{value}' matches multiple choices: {', '.join(matches)}"
            logger.error(msg)
            raise ValueError(msg)

    def getter(self, instance) -> Union[str, Enum]:
        """Get the current selection from the instrument."""
        logger.debug(f"Getting selection for '{self.cmd_str}'")
        try:
            response = instance.query(f"{self.cmd_str}?")
            matched_value = self._find_match(response)
            
            # Convert to enum if applicable
            if self.enum_class:
                result = self.enum_class(matched_value)
                logger.debug(f"Converted to enum: {result}")
            else:
                result = matched_value
                logger.debug(f"Using string value: {result}")
                
            self.last_response = PropertyResponse(
                value=result,
                raw_response=response
            )
            return result
        except Exception as e:
            logger.error(f"Error in getter for '{self.cmd_str}': {e}")
            self.last_response = PropertyResponse(
                success=False,
                error=str(e)
            )
            raise

    def setter(self, instance, value):
        """Set a selection on the instrument."""
        logger.debug(f"Setting '{self.cmd_str}' to {value}")
        try:
            matched_value = self._find_match(value)
            command = f"{self.cmd_str}{self.join_char}{matched_value}"
            instance.write(command)
            self.last_response = PropertyResponse(
                value=matched_value,
                raw_response=command
            )
        except Exception as e:
            logger.error(f"Error in setter for '{self.cmd_str}': {e}")
            self.last_response = PropertyResponse(
                success=False,
                error=str(e)
            )
            raise

class DataProperty(Property):
    """
    Property for handling basic ASCII data arrays.
    
    This property type handles simple arrays of ASCII values like comma-separated 
    lists of numbers. It provides validation and conversion of array data.

    Args:
        cmd_str: SCPI command string
        access: Access mode ('read', 'write', or 'read-write')
        doc_str: Documentation string
        container: Container type for the data (default: numpy.array)
        converter: Function to convert individual values (default: float)
        separator: String separator between values
        join_char: Character used to join command and value
        terminator: Read termination character(s)
    """

    def __init__(self, cmd_str: str, access: str = "read-write", doc_str: str = "",
                 container=np.array, converter: Callable = float, separator: str = ",", 
                 join_char: str = " ", terminator: str = '\n'):
        super().__init__(cmd_str, doc_str, access, join_char)
        self.container = container
        self.converter = converter
        self.separator = separator
        self.terminator = terminator
        logger.debug(
            f"Initialized DataProperty with separator='{separator}', "
            f"terminator='{terminator}'"
        )

    def _convert_to_array(self, response: str) -> Any:
        """Convert a response string into an array of values."""
        logger.debug("Converting response to array")
        try:
            # Split response and filter out empty strings
            values = [v.strip() for v in response.strip().split(self.separator)]
            values = [v for v in values if v]
            
            # Convert values using specified converter
            converted = [self.converter(v) for v in values]
            logger.debug(f"Converted {len(converted)} values")
            
            # Return in specified container
            return self.container(converted)
        except Exception as e:
            msg = f"Error converting response to array: {e}"
            logger.error(msg)
            raise ValueError(msg)

    def _format_array(self, value: Any) -> str:
        """Format an array of values for sending to instrument."""
        logger.debug("Formatting array for transmission")
        try:
            # Convert each value and join with separator
            formatted = self.separator.join(str(self.converter(v)) for v in value)
            if self.terminator and not formatted.endswith(self.terminator):
                formatted += self.terminator
            return formatted
        except Exception as e:
            msg = f"Error formatting array: {e}"
            logger.error(msg)
            raise ValueError(msg)

    def getter(self, instance) -> Any:
        """Get array data from the instrument."""
        logger.debug(f"Getting array data for '{self.cmd_str}'")
        try:
            response = instance.query(f"{self.cmd_str}?")
            array_data = self._convert_to_array(response)
            self.last_response = PropertyResponse(
                value=array_data,
                raw_response=response
            )
            return array_data
        except Exception as e:
            logger.error(f"Error in getter for '{self.cmd_str}': {e}")
            self.last_response = PropertyResponse(
                success=False,
                error=str(e)
            )
            raise

    def setter(self, instance, value):
        """Set array data on the instrument."""
        logger.debug(f"Setting array data for '{self.cmd_str}'")
        if not hasattr(value, '__iter__'):
            raise ValueError(f"Value must be iterable, got {type(value)}")
            
        try:
            formatted_data = self._format_array(value)
            command = f"{self.cmd_str}{self.join_char}{formatted_data}"
            instance.write(command)
            self.last_response = PropertyResponse(
                value=value,
                raw_response=command
            )
        except Exception as e:
            logger.error(f"Error in setter for '{self.cmd_str}': {e}")
            self.last_response = PropertyResponse(
                success=False,
                error=str(e)
            )
            raise

class DataBlockProperty(Property):
    """
    Property for handling binary data blocks with IEEE headers.

    This property type handles binary data transfers with IEEE 488.2 binary block 
    format, often used for waveform data and other large datasets.

    Args:
        cmd_str: SCPI command string
        access: Access mode ('read', 'write', or 'read-write')
        doc_str: Documentation string
        container: Container type for the data (default: numpy.array)
        dtype: NumPy dtype for binary data (default: np.float32)
        ieee_header: Whether to expect/generate IEEE headers (default: True)
    """

    def __init__(self, cmd_str: str, access: str = "read-write", doc_str: str = "",
                 container=np.array, dtype=np.float32, ieee_header: bool = True):
        super().__init__(cmd_str, doc_str, access)
        self.container = container
        self.dtype = dtype
        self.ieee_header = ieee_header
        logger.debug(
            f"Initialized DataBlockProperty with dtype={dtype}, "
            f"ieee_header={ieee_header}"
        )

    def _parse_ieee_header(self, data: bytes) -> Tuple[bytes, int]:
        """
        Parse IEEE 488.2 binary block header.
        Format: '#' + number_of_digits + data_length + data
        Example: #42000 means 4 digits follow, data length is 2000 bytes
        """
        logger.debug("Parsing IEEE header")
        if not data.startswith(b'#'):
            raise ValueError("Invalid IEEE block header: missing '#' marker")

        try:
            num_digits = int(data[1:2])
            header_len = 2 + num_digits
            data_len = int(data[2:header_len])
            logger.debug(f"Found IEEE header: {num_digits} digits, {data_len} bytes")
            return data[header_len:header_len + data_len], header_len
        except Exception as e:
            msg = f"Error parsing IEEE header: {e}"
            logger.error(msg)
            raise ValueError(msg)

    def _format_ieee_block(self, data: np.ndarray) -> bytes:
        """Format data as IEEE 488.2 binary block."""
        logger.debug("Formatting IEEE block")
        try:
            # Convert data to bytes
            raw_data = data.astype(self.dtype).tobytes()
            
            # Create IEEE header
            length_str = str(len(raw_data)).encode()
            header = b'#' + str(len(length_str)).encode() + length_str
            
            return header + raw_data
        except Exception as e:
            msg = f"Error formatting IEEE block: {e}"
            logger.error(msg)
            raise ValueError(msg)

    def getter(self, instance) -> np.ndarray:
        """Get binary block data from the instrument."""
        logger.debug(f"Getting binary data for '{self.cmd_str}'")
        try:
            response = instance.query(f"{self.cmd_str}?")
            
            # Handle binary response
            if isinstance(response, bytes):
                if self.ieee_header:
                    data_bytes, _ = self._parse_ieee_header(response)
                else:
                    data_bytes = response
                    
                # Convert to numpy array
                array_data = np.frombuffer(data_bytes, dtype=self.dtype)
                
            # Handle ASCII response
            else:
                values = [float(v) for v in response.strip().split(',')]
                array_data = np.array(values, dtype=self.dtype)
            
            array_data = self.container(array_data)
            self.last_response = PropertyResponse(
                value=array_data,
                raw_response=response
            )
            return array_data
            
        except Exception as e:
            logger.error(f"Error in getter for '{self.cmd_str}': {e}")
            self.last_response = PropertyResponse(
                success=False,
                error=str(e)
            )
            raise

    def setter(self, instance, value):
        """Set binary block data on the instrument."""
        logger.debug(f"Setting binary data for '{self.cmd_str}'")
        try:
            # Convert input to numpy array if needed
            if not isinstance(value, np.ndarray):
                value = np.array(value, dtype=self.dtype)
                
            # Format data
            if self.ieee_header:
                data = self._format_ieee_block(value)
                command = f"{self.cmd_str}{self.join_char}".encode() + data
            else:
                # Fall back to ASCII if no IEEE header
                command = f"{self.cmd_str}{self.join_char}" + \
                         ",".join(str(x) for x in value)
            
            instance.write(command)
            self.last_response = PropertyResponse(
                value=value,
                raw_response=str(command)
            )
        except Exception as e:
            logger.error(f"Error in setter for '{self.cmd_str}': {e}")
            self.last_response = PropertyResponse(
                success=False,
                error=str(e)
            )
            raise