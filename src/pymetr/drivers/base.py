# base.py

import logging
import time
from abc import ABCMeta, abstractmethod
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from typing import Optional, Any, Dict, List
import numpy as np
import concurrent.futures

from pymetr.drivers.connections import PyVisaConnection
from pymetr.drivers.connections import RawSocketConnection
from pymetr.drivers.connections import ConnectionInterface


logger = logging.getLogger(__name__)

class ABCQObjectMeta(type(QObject), ABCMeta):
    """Metaclass that combines QObject and ABC functionality."""
    pass

class Instrument(QObject, metaclass=ABCQObjectMeta):
    """
    Base Instrument class supporting both blocking and UI-responsive modes.
    """

    commandSent = Signal(str)               # Command that was sent
    responseReceived = Signal(str, str)     # (command, response)
    exceptionOccured = Signal(str)
    traceDataReady = Signal(np.ndarray, np.ndarray)  # (freq_array, amp_array)

    def __init__(self, connection: ConnectionInterface,
                 read_after_write: bool = False, read_timeout: float = 1.5,
                 parent: Optional[QObject] = None):
        super().__init__(parent)
        self.connection = connection
        self.read_after_write = read_after_write
        self.read_timeout = read_timeout

        # State flags
        self.continuous_mode = False
        self._ready_for_data = True
        self.unique_id = None

        # Check if we're in a GUI context
        self._has_gui = QApplication.instance() is not None

    def open(self):
        """Opens the connection to the instrument."""
        try:
            self.connection.open()
            logger.info("Instrument connection opened")
        except Exception as e:
            logger.exception(f"Failed to open connection: {e}")
            raise

    def close(self):
        """Closes the connection to the instrument."""
        logger.debug("Closing instrument connection")
        try:
            self.connection.close()
            logger.info("Instrument connection closed")
        except Exception as e:
            logger.exception(f"Failed to close connection: {e}")
            raise

    def _read_with_events(self) -> str:
        """
        Read from instrument while processing GUI events.
        Uses direct event processing to maintain UI responsiveness.

        Returns:
            str: Complete response string
        """
        buffer = bytearray()
        start_time = time.time()

        # Ensure terminator is in bytes
        terminator = (self.connection.read_termination.encode(self.connection.encoding) 
                    if isinstance(self.connection.read_termination, str) 
                    else self.connection.read_termination)

        while True:
            # Check timeout
            if time.time() - start_time > self.read_timeout:
                raise TimeoutError("Read operation timed out")

            # Try to read available data
            if self.connection.has_data():
                chunk = self.connection.read_available()
                if chunk:
                    buffer.extend(chunk)

                    # Check for complete message
                    if terminator in buffer:
                        # Find terminator position
                        term_pos = buffer.find(terminator)
                        # Extract message
                        message = buffer[:term_pos].decode(self.connection.encoding)
                        # Save remaining data in connection's buffer
                        remaining = buffer[term_pos + len(terminator):]
                        if remaining:
                            self.connection._read_buffer = remaining
                        return message

            # Keep UI responsive when in GUI context
            if self._has_gui:
                QApplication.processEvents()

            # Small sleep to prevent busy-waiting
            time.sleep(0.002)

    def write(self, command: str) -> None:
        """Write a command to the instrument."""
        desc = f"WRITE: {command}"
        logger.debug(desc)

        try:
            self.connection.write(command)
            self.commandSent.emit(command)

            if self.read_after_write:
                return self.read()

        except Exception as e:
            logger.exception(f"Error executing {desc}: {e}")
            self.exceptionOccured.emit(f"{desc} -> {e}")
            raise

    def read(self) -> str:
        """
        Read from the instrument using either async or sync mode.

        Returns:
            str: The response string
        """
        desc = "READ"
        logger.debug(desc)

        try:
            if self._has_gui:
                response = self._read_with_events()
            else:
                # Use synchronous read for non-GUI or sync mode
                response = self.connection.read_available().decode(self.connection.encoding).strip()

            self.responseReceived.emit("READ", response)
            return response

        except Exception as e:
            logger.exception(f"Error executing {desc}: {e}")
            self.exceptionOccured.emit(f"{desc} -> {e}")
            raise

    def query(self, command: str) -> str:
        """
        Send a query and get the response.

        Args:
            command: The query command

        Returns:
            str: The response string
        """
        desc = f"QUERY: {command}"
        logger.debug(desc)

        try:
            self.write(command)
            response = self.read()
            self.responseReceived.emit(command, response)
            return response

        except Exception as e:
            logger.exception(f"Error executing {desc}: {e}")
            self.exceptionOccured.emit(f"{desc} -> {e}")
            raise

    def set_continuous_mode(self, mode: bool):
        """Set continuous mode flag."""
        logger.debug(f"Set continuous mode to {mode}")
        self.continuous_mode = mode
        self._ready_for_data = not mode

    def set_unique_id(self, uid: str):
        """Set unique identifier for this instrument."""
        self.unique_id = uid

    @abstractmethod
    def fetch_trace(self, *args, **kwargs):
        """
        Abstract method for fetching trace data.
        Must be implemented by derived classes.
        """
        pass

    @staticmethod
    def gui_command(func):
        """Decorator for GUI-related commands."""
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    @classmethod
    def list_instruments(cls, model_filter: Optional[List[str]] = None) -> Dict[str, Dict[str, str]]:
        """
        List available instruments by combining PyVISA and Raw Socket discoveries.
        Optionally filter instruments based on a list of model substrings.

        Args:
            model_filter (List[str], optional): List of model substrings to filter instruments.

        Returns:
            Dict[str, Dict[str, str]]: A dictionary mapping unique IDs to instrument details.
        """
        logger.debug(f"Listing instruments with model_filter: '{model_filter}'")
        instruments = {}

        try:
            # Get raw resource strings from both methods
            pyvisa_resources = PyVisaConnection.list_instruments()
            raw_socket_resources = RawSocketConnection.list_instruments()

            has_gui = QApplication.instance() is not None

            # Combine resources
            all_resources = list(pyvisa_resources.values()) + list(raw_socket_resources.values())

            logger.debug(f"Total resources to query: {len(all_resources)}")

            # Define a helper function for querying IDN
            def query_idn(resource):
                if has_gui:
                    QApplication.processEvents()
                try:
                    if resource.startswith("TCPIP") and "SOCKET" in resource:
                        # Raw socket connection
                        host, port = RawSocketConnection.parse_resource_string(resource)
                        conn = RawSocketConnection(host=host, port=port)
                    else:
                        # VISA connection
                        conn = PyVisaConnection(resource)

                    conn.open()
                    # Try to get IDN - use short timeout
                    conn.timeout = 1.0
                    idn = conn.query("*IDN?").strip()
                    conn.close()

                    # If we got an IDN and it matches filter (if any), return it
                    if idn:
                        # Parse IDN: Manufacturer, Model, Serial, Firmware
                        idn_parts = [part.strip() for part in idn.split(",")]
                        if len(idn_parts) >= 4:
                            manufacturer, model, serial, firmware = idn_parts[:4]
                        else:
                            manufacturer, model, serial, firmware = idn_parts + [""]*(4-len(idn_parts))

                        # Apply model filter if provided
                        if model_filter:
                            if any(model_filter_item.lower() in model.lower() for model_filter_item in model_filter):
                                unique_id = f"{model}, {serial}"
                                instruments[unique_id] = {
                                    'manufacturer': manufacturer,
                                    'model': model,
                                    'serial': serial,
                                    'firmware': firmware,
                                    'resource': resource
                                }
                                logger.info(f"Found matching instrument - IDN: {unique_id}, Resource: {resource}")
                        else:
                            unique_id = f"{model}, {serial}"
                            instruments[unique_id] = {
                                'manufacturer': manufacturer,
                                'model': model,
                                'serial': serial,
                                'firmware': firmware,
                                'resource': resource
                            }
                            logger.info(f"Found instrument - IDN: {unique_id}, Resource: {resource}")

                except Exception as e:
                    logger.debug(f"Could not get IDN from {resource}: {e}")
                    return

            # Utilize ThreadPoolExecutor for parallel querying
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                futures = {executor.submit(query_idn, resource): resource for resource in all_resources}
                concurrent.futures.wait(futures)

        except Exception as e:
            logger.exception(f"Failed during instrument discovery: {e}")

        logger.info(f"Discovered instruments: {instruments}")
        return instruments


class SCPIInstrument(Instrument):
    """
    A specialized Instrument for SCPI-compatible devices.
    
    Args:
        connection (ConnectionInterface): The connection to use
        async_mode (bool): Whether to use UI-responsive mode (default: True)
        read_after_write (bool): Whether to read after every write (default: False)
        timeout (int): Default timeout for operations in milliseconds (default: 5000)
        parent (QObject): Parent QObject (default: None)
    """

    def __init__(self, connection, read_after_write=False, timeout=5000, parent=None):
        super().__init__(connection, read_after_write=read_after_write, parent=parent)
        self._data_mode = "ASCII"
        self._data_type = "B"  # Default data type for binary transfers
        self.timeout = timeout
        
        # Status tracking
        self._last_status = None
        self._error_queue = []

    @property
    def data_mode(self) -> str:
        """Gets or sets the data transfer mode ('ASCII' or 'BINARY')."""
        return self._data_mode
    
    @data_mode.setter
    def data_mode(self, mode: str):
        mode = mode.upper()
        if mode not in ["ASCII", "BINARY"]:
            raise ValueError("data_mode must be 'ASCII' or 'BINARY'")
        self._data_mode = mode
        logger.debug(f"Set data_mode to {self._data_mode}")

    @property
    def data_type(self) -> str:
        """Gets or sets the binary data type (e.g., 'B' for unsigned char)."""
        return self._data_type
    
    @data_type.setter
    def data_type(self, dtype: str):
        self._data_type = dtype
        logger.debug(f"Set data_type to {self._data_type}")

    # IEEE 488.2 Common Commands

    def idn(self) -> str:
        """
        Queries the instrument identity (*IDN?).
        
        Returns:
            str: The identification string
        """
        logger.debug("Querying instrument identity (*IDN?)")
        response = self._execute_command(self.connection.query, "*IDN?")
        logger.debug(f"Received IDN response: {response}")
        return response
    
    def get_identity(self) -> str:
        """
        Queries the instrument identity (*IDN?).
        
        Returns:
            str: The identification string
        """
        logger.debug("Querying instrument identity (*IDN?)")
        response = self.query("*IDN?")
        logger.debug(f"Received IDN response: {response}")
        return response
    
    def query_operation_complete(self):
        """Waits for operation complete (*OPC?)."""
        logger.info("Waiting for operation complete (*OPC?)")
        return self.query("*OPC?")

    def reset(self):
        """Resets the instrument (*RST)."""
        logger.info("Performing instrument reset (*RST)")
        self.write("*RST")

    def clear_status_registers(self):
        """Clears the status registers (*CLS)."""
        logger.info("Clearing status registers (*CLS)")
        self.write("*CLS")

    def set_operation_complete(self):
        """Sets the operation complete flag (*OPC)."""
        logger.info("Setting operation complete flag (*OPC)")
        self.write("*OPC")

    def check_error_queue(self) -> List[str]:
        """
        Queries the error queue (SYST:ERR?).
        
        Returns:
            List[str]: List of error messages
        """
        logger.debug("Checking error queue (SYST:ERR?)")
        errors = []
        
        while True:
            response = self.query("SYST:ERR?")
            if "No error" in response.lower() or response.startswith("0,"):
                logger.debug("No more errors in the error queue.")
                break
            errors.append(response)
            logger.warning(f"Instrument error: {response}")
        
        return errors

    # Helper Methods for Data Handling

    def _parse_binary_header(self, response: bytes) -> tuple:
        """
        Parses IEEE 488.2 binary block header.
        Format: '#' + num_of_length_digits + data_length + data
        
        Returns:
            tuple: (data_bytes, header_length)
        """
        if not response.startswith(b'#'):
            raise ValueError("Invalid binary block format")
            
        num_digits = int(response[1:2])
        header_len = 2 + num_digits
        data_len = int(response[2:header_len])
        
        return response[header_len:header_len + data_len], header_len

    def _format_binary_data(self, data: np.ndarray) -> bytes:
        """
        Formats data array as IEEE 488.2 binary block.
        
        Args:
            data: Numpy array to format
            
        Returns:
            bytes: Formatted binary data
        """
        raw_data = data.tobytes()
        len_str = str(len(raw_data))
        header = f"#{len(len_str)}{len_str}".encode()
        return header + raw_data

    def write_binary_data(self, command: str, data: np.ndarray):
        """
        Writes binary data to instrument with proper formatting.
        
        Args:
            command: SCPI command
            data: Numpy array to send
        """
        binary_data = self._format_binary_data(data)
        full_command = command.encode() + b' ' + binary_data
        self._execute_command(self.connection.write, full_command)

    def read_binary_data(self) -> np.ndarray:
        """
        Reads binary data from instrument and converts to numpy array.
        
        Returns:
            numpy.ndarray: Parsed data array
        """
        response = self._execute_command(self.connection.read)
        data, _ = self._parse_binary_header(response)
        return np.frombuffer(data, dtype=self._data_type)
    

class Subsystem:
    """
    Base class for creating instrument subsystems, supporting both simple and indexed instantiation, 
    and enabling nested subsystem command prefix cascading.
    """

    def __init__(self, instr, cmd_prefix="", index=None):
        """
        Initializes a Subsystem instance.

        Args:
            instr (Instrument or Subsystem): The parent instrument or subsystem this instance belongs to.
            cmd_prefix (str): The command prefix specific to this subsystem.
            index (int, optional): If provided, specifies the index for this instance.
        """
        self.instr = instr
        logger.debug(f"Initializing subsystem with instrument {instr}, prefix '{cmd_prefix}', and index {index}")
        # Handle cascading of command prefixes for nested subsystems
        self.cmd_prefix = f"{instr.cmd_prefix}{cmd_prefix}" if hasattr(instr, 'cmd_prefix') else cmd_prefix
        if index is not None:
            self.cmd_prefix += str(index)
        logger.debug(f"Subsystem command prefix set to '{self.cmd_prefix}'")

    def write(self, command: str) -> None:
        """
        Forward write command to parent instrument.

        Args:
            command (str): The SCPI command string to send.
        """
        logger.debug(f"Subsystem forwarding WRITE command: '{command}'")
        return self.instr.write(command)

    def read(self) -> str:
        """
        Forward read command to parent instrument.

        Returns:
            str: The response string from the instrument.
        """
        logger.debug("Subsystem forwarding READ command")
        return self.instr.read()

    def query(self, command: str) -> str:
        """
        Forward query command to parent instrument.

        Args:
            command (str): The SCPI query command string.

        Returns:
            str: The response string from the instrument.
        """
        logger.debug(f"Subsystem forwarding QUERY command: '{command}'")
        return self.instr.query(command)

    def _execute_command(self, func, *args, **kwargs):
        """
        Forward command execution to parent instrument.

        Args:
            func (callable): The function to execute (e.g., write, read, query).
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            Any: The result of the executed function.
        """
        logger.debug(f"Subsystem executing command with function: '{func.__name__}'")
        return self.instr._execute_command(func, *args, **kwargs)

    @classmethod
    def build(cls, parent, cmd_prefix, indices=None):
        """
        Class method to instantiate subsystems. Handles both single and indexed instances.

        Args:
            parent (Instrument or Subsystem): The parent object for the new subsystem(s).
            cmd_prefix (str): The SCPI command prefix.
            indices (int, optional): Number of indexed instances to create.

        Returns:
            Subsystem or list of Subsystem: Single instance or list of indexed instances.
        """
        if indices is None:
            # Single instance (no indexing)
            logger.debug(f"Building single instance of {cls.__name__} with prefix '{cmd_prefix}'")
            return cls(parent, cmd_prefix)
        
        subsystems = [None]  # Dummy element at index=0 for 1-based indexing
        if isinstance(indices, int) and indices > 0:
            # Create indexed instances from 1 to indices
            for i in range(1, indices + 1):
                logger.debug(f"Building indexed instance {i} of {cls.__name__} with prefix '{cmd_prefix}'")
                subsystems.append(cls(parent, cmd_prefix, i))
            return subsystems
        else:
            raise ValueError("Unsupported type or value for indices. Must be a positive integer or None.")

import logging
logger = logging.getLogger(__name__)
from enum import Enum
from collections.abc import Iterable
from PySide6.QtCore import QObject, Signal
import logging

class Sources(QObject):
    """
    Handles the management and operation of sources for SCPI instruments.

    Attributes:
        source_changed (Signal): Emitted when the list of active sources changes.
    """

    source_changed = Signal(list)

    def __init__(self, sources):
        """
        Initializes the Sources object with the available sources.

        Args:
            sources (list): List of available sources.
        """
        super().__init__()
        self._sources = [source.value if isinstance(source, Enum) else source for source in sources]
        self._source = []
        logger.info("Sources initialized with: %s", self._sources)

    @property
    def source(self):
        """
        Returns the list of active sources.

        Returns:
            list: Active sources.
        """
        return self._source

    @source.setter
    def source(self, sources):
        """
        Sets the active sources from the available sources.

        Args:
            sources (list): List of sources to set as active.
        """
        self._source = [source for source in sources if source in self._sources]
        logger.debug("Active source set to: %s", self._source)
        self.source_changed.emit(self._source)

    @property
    def sources(self):
        """
        Returns the list of available sources.

        Returns:
            list: Available sources.
        """
        return self._sources

    def add_source(self, source):
        """
        Adds a source to the list of active sources if it's available and not already active.

        Args:
            source (str or Enum): Source to add to the active sources.
        """
        source = source.value if isinstance(source, Enum) else source
        if source in self._sources and source not in self._source:
            self._source.append(source)
            logger.info("Added active source: %s", source)
            self.source_changed.emit(self._source)

    def remove_source(self, source):
        """
        Removes a source from the list of active sources if it's currently active.

        Args:
            source (str or Enum): Source to remove from the active sources.
        """
        source = source.value if isinstance(source, Enum) else source
        if source in self._source:
            self._source.remove(source)
            logger.info("Removed active source: %s", source)
            self.source_changed.emit(self._source)

    def set_sources(self, sources):
        """
        Sets the list of active sources from the available sources.

        Args:
            sources (list): List of sources to set as active.
        """
        self._source = [source.value if isinstance(source, Enum) else source for source in sources if source in self._sources]
        logger.debug("Active sources set to: %s", self._source)
        self.source_changed.emit(self._source)

    @staticmethod
    def source_command(command_template=None, formatter=None, single=False, join_str=', '):
        """
        Decorator for source-related commands.

        The `source_command` decorator is used to handle source-related commands in a flexible manner.
        It allows you to specify a command template, source formatting, and whether to handle sources
        individually or collectively.

        Usage Examples:
            @Sources.source_command(":DIGitize {}", single=True)
            def digitize(self, source):
                # Digitizes the specified source individually.
                pass

            @Sources.source_command(":calculate:measurement {}", formatter="'{}'", join_str=', ')
            def calculate_measurement(self, *sources):
                # Calculates the measurement for the specified sources.
                pass

            @Sources.source_command(single=True)
            def custom_function_single(self, source):
                # Performs a custom operation on each source individually.
                pass

            @Sources.source_command()
            def custom_function_multi(self, *sources):
                # Performs a custom operation on multiple sources.
                pass

        Args:
            command_template (str, optional): Template for the SCPI command. Defaults to None.
            formatter (str, optional): Formatter for the sources. Defaults to None.
            single (bool, optional): Whether to handle sources individually. Defaults to False.
            join_str (str, optional): String to join multiple sources. Defaults to ', '.

        Returns:
            function: Decorated function.
        """
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                sources_to_use = self.sources.source if not args else args

                if isinstance(sources_to_use, Enum):
                    sources_to_use = [sources_to_use]
                elif not isinstance(sources_to_use, Iterable) or isinstance(sources_to_use, str):
                    sources_to_use = [sources_to_use]

                cleaned_sources = [source.value if isinstance(source, Enum) else source for source in sources_to_use]

                if formatter:
                    cleaned_sources = [formatter.format(source) for source in cleaned_sources]

                if command_template:
                    if single:
                        for source in cleaned_sources:
                            command = command_template.format(source)
                            logger.debug(f"Executing command: {command}")
                            self.write(command)
                            func(self, source, **kwargs)
                    else:
                        command = command_template.format(join_str.join(cleaned_sources))
                        logger.debug(f"Executing command: {command}")
                        self.write(command)
                        return func(self, *cleaned_sources, **kwargs)
                else:
                    if single:
                        for source in cleaned_sources:
                            func(self, source, **kwargs)
                    else:
                        return func(self, *cleaned_sources, **kwargs)

            return wrapper
        return decorator
    
# properties.py

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