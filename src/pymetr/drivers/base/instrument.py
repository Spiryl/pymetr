# drivers/base/instrument.py
import logging
import time
from abc import ABCMeta, abstractmethod
from typing import Optional, Any, Dict, List
import concurrent.futures
import queue

# Third-party imports
import numpy as np
from PySide6.QtCore import QObject, Signal, QThread, Slot
from PySide6.QtWidgets import QApplication

# Local imports
from pymetr.core.logging import logger
from pymetr.drivers.base.connections import (
    ConnectionInterface,
    PyVisaConnection,
    RawSocketConnection
)

class ConnectionWorker(QObject):
    """Worker object that handles instrument communication in a separate thread."""
    command_finished = Signal(str)    # Response string
    error_occurred = Signal(str)      # Error message
    
    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.command_queue = queue.Queue()
        self.running = True
        
    @Slot()
    def process_commands(self):
        """Process raw SCPI commands."""
        while self.running:
            try:
                # Get command with timeout
                try:
                    cmd_type, command = self.command_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                    
                # Execute command
                try:
                    if cmd_type == "write":
                        self.connection.write(command)
                        self.command_finished.emit("")
                    elif cmd_type == "read":
                        response = self.connection.read()
                        self.command_finished.emit(response)
                    elif cmd_type == "query":
                        response = self.connection.query(command)
                        self.command_finished.emit(response)
                except Exception as e:
                    self.error_occurred.emit(str(e))
                    
            except Exception as e:
                self.error_occurred.emit(f"Worker error: {str(e)}")

    def stop(self):
        """Stop the worker thread."""
        self.running = False
        
    def write(self, command: str):
        """Queue a write command."""
        self.command_queue.put(("write", command))
        
    def read(self):
        """Queue a read command."""
        self.command_queue.put(("read", ""))
        
    def query(self, command: str):
        """Queue a query command."""
        self.command_queue.put(("query", command))

class ABCQObjectMeta(type(QObject), ABCMeta):
    """Metaclass that combines QObject and ABC functionality."""
    pass

class Instrument(QObject, metaclass=ABCQObjectMeta):
    """
    Base Instrument class supporting both threaded and direct communication modes.
    """
    commandSent = Signal(str)               
    responseReceived = Signal(str, str)     
    exceptionOccured = Signal(str)
    traceDataReady = Signal(np.ndarray, np.ndarray)

    def __init__(self, connection: ConnectionInterface,
                 read_after_write: bool = False, 
                 read_timeout: float = 1.5,
                 threaded_mode: bool = None,  # None = auto-detect based on GUI context
                 parent: Optional[QObject] = None):
        super().__init__(parent)
        self.connection = connection
        self.read_after_write = read_after_write
        self.read_timeout = read_timeout
        
        # State flags
        self.continuous_mode = False
        self._ready_for_data = True
        self.unique_id = None

        # Determine communication mode
        self._has_gui = QApplication.instance() is not None
        self._threaded_mode = threaded_mode if threaded_mode is not None else self._has_gui
        self._worker = None
        self._worker_thread = None

        if self._threaded_mode:
            self._setup_worker()

    def _setup_worker(self):
        """Initialize connection worker and thread if needed."""
        self._worker = ConnectionWorker(self.connection)
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)
        
        # Connect signals
        self._worker_thread.started.connect(self._worker.process_commands)
        self._worker.command_finished.connect(self._handle_worker_response)
        self._worker.error_occurred.connect(self._handle_worker_error)
        
        self._worker_thread.start()

    def _cleanup_worker(self):
        """Clean up worker thread."""
        if self._worker:
            self._worker.stop()
            self._worker_thread.quit()
            self._worker_thread.wait()
            self._worker = None
            self._worker_thread = None

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
        self._cleanup_worker()
        try:
            self.connection.close()
            logger.info("Instrument connection closed")
        except Exception as e:
            logger.exception(f"Failed to close connection: {e}")
            raise

    def write(self, command: str) -> None:
        """Write a command to the instrument."""
        desc = f"WRITE: {command}"
        logger.debug(desc)

        try:
            if self._threaded_mode:
                self._worker.write(command)
            else:
                self.connection.write(command)
                
            self.commandSent.emit(command)

            if self.read_after_write:
                return self.read()

        except Exception as e:
            logger.exception(f"Error executing {desc}: {e}")
            self.exceptionOccured.emit(f"{desc} -> {e}")
            raise

    def read(self) -> str:
        """Read from the instrument."""
        desc = "READ"
        logger.debug(desc)

        try:
            if self._threaded_mode:
                self._worker.read()
                # Response will come through _handle_worker_response
                return None  # Or use a Future/Promise pattern if needed
            else:
                response = self.connection.read()
                self.responseReceived.emit("READ", response)
                return response

        except Exception as e:
            logger.exception(f"Error executing {desc}: {e}")
            self.exceptionOccured.emit(f"{desc} -> {e}")
            raise

    def query(self, command: str) -> str:
        """Send a query and get the response."""
        desc = f"QUERY: {command}"
        logger.debug(desc)

        try:
            if self._threaded_mode:
                self._worker.query(command)
                # Response will come through _handle_worker_response
                return None  # Or use a Future/Promise pattern if needed
            else:
                self.write(command)
                response = self.read()
                self.responseReceived.emit(command, response)
                return response

        except Exception as e:
            logger.exception(f"Error executing {desc}: {e}")
            self.exceptionOccured.emit(f"{desc} -> {e}")
            raise

    def _handle_worker_response(self, response: str):
        """Handle responses from worker thread."""
        self.responseReceived.emit("READ", response)

    def _handle_worker_error(self, error: str):
        """Handle errors from worker thread."""
        self.exceptionOccured.emit(error)

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
        List available instruments, starting with fast UDP discovery.
        Emits instrument_found signals as devices are discovered.
        
        Args:
            model_filter (List[str], optional): List of model substrings to filter instruments.
            
        Returns:
            Dict[str, Dict[str, str]]: Dictionary mapping unique IDs to instrument details.
        """
        logger.debug(f"Starting instrument discovery with model_filter: '{model_filter}'")
        instruments = {}
        has_gui = QApplication.instance() is not None

        # Start with UDP discovery (faster)
        try:
            logger.debug("Starting UDP discovery")
            for ip_range in RawSocketConnection.get_all_local_ip_ranges():
                udp_devices = RawSocketConnection._discover_udp(timeout=1.0, ip_range=ip_range)
                
                # Process each UDP-discovered device
                for resource in udp_devices.values():
                    try:
                        # Create socket connection
                        host, port = RawSocketConnection.parse_resource_string(resource)
                        conn = RawSocketConnection(host=host, port=port, timeout=1.0)
                        conn.open()
                        
                        # Quick IDN query
                        idn = conn.query("*IDN?").strip()
                        conn.close()

                        if idn:
                            # Parse IDN parts
                            idn_parts = [part.strip() for part in idn.split(",")]
                            if len(idn_parts) >= 4:
                                manufacturer, model, serial, firmware = idn_parts[:4]
                            else:
                                manufacturer, model, serial, firmware = idn_parts + [""]*(4-len(idn_parts))

                            # Apply model filter if provided
                            if not model_filter or any(f.lower() in model.lower() for f in model_filter):
                                instrument_info = {
                                    'manufacturer': manufacturer,
                                    'model': model,
                                    'serial': serial,
                                    'firmware': firmware,
                                    'resource': resource
                                }
                                unique_id = f"{model}, {serial}"
                                instruments[unique_id] = instrument_info
                                
                                # Emit signal if we found a device
                                if hasattr(cls, 'instrument_found'):
                                    cls.instrument_found.emit(instrument_info)
                                logger.info(f"Found instrument via UDP: {unique_id}")

                    except Exception as e:
                        logger.debug(f"Could not query device at {resource}: {e}")

                    if has_gui:
                        QApplication.processEvents()

        except Exception as e:
            logger.warning(f"UDP discovery error: {e}")

        # Then do VISA discovery (slower but might find additional devices)
        try:
            logger.debug("Starting VISA discovery")
            visa_resources = PyVisaConnection.list_instruments()
            
            def query_visa_device(resource):
                if has_gui:
                    QApplication.processEvents()
                try:
                    conn = PyVisaConnection(resource, timeout=1000)  # Short timeout
                    conn.open()
                    idn = conn.query("*IDN?").strip()
                    conn.close()

                    if idn:
                        idn_parts = [part.strip() for part in idn.split(",")]
                        if len(idn_parts) >= 4:
                            manufacturer, model, serial, firmware = idn_parts[:4]
                        else:
                            manufacturer, model, serial, firmware = idn_parts + [""]*(4-len(idn_parts))

                        if not model_filter or any(f.lower() in model.lower() for f in model_filter):
                            instrument_info = {
                                'manufacturer': manufacturer,
                                'model': model,
                                'serial': serial,
                                'firmware': firmware,
                                'resource': resource
                            }
                            unique_id = f"{model}, {serial}"
                            
                            # Only add/emit if we haven't already found this device
                            if unique_id not in instruments:
                                instruments[unique_id] = instrument_info
                                if hasattr(cls, 'instrument_found'):
                                    cls.instrument_found.emit(instrument_info)
                                logger.info(f"Found instrument via VISA: {unique_id}")

                except Exception as e:
                    logger.debug(f"Could not query VISA device at {resource}: {e}")

            # Use thread pool for VISA discovery
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                list(executor.map(query_visa_device, visa_resources.values()))

        except Exception as e:
            logger.warning(f"VISA discovery error: {e}")

        logger.info(f"Discovery complete. Found {len(instruments)} instruments")
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
        self.cmd_prefix = f"{getattr(instr, 'cmd_prefix', '')}{cmd_prefix}"
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

