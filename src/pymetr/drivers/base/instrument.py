# drivers/base/instrument.py
"""
Base Instrument Classes

This module provides the foundation for instrument communication with support for:
1. Thread-safe asynchronous operation for GUI applications
2. Synchronous operation for scripting contexts
3. Command-response pairing to ensure proper sequencing
4. Common SCPI command implementations
5. Abstraction for different connection types
6. Extensibility through subsystems
"""

import time
import uuid
import threading
import queue
from abc import ABCMeta, abstractmethod
from typing import Optional, Any, Dict, List, Union, Tuple

# Third-party imports
import numpy as np
from PySide6.QtCore import QObject, Signal, QThread, Slot, QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

# Local imports
from pymetr.core.logging import logger
from pymetr.drivers.base.connections import (
    ConnectionInterface,
    PyVisaConnection,
    RawSocketConnection
)

class ConnectionWorker(QObject):
    """
    Worker object that handles instrument communication in a separate thread.
    
    This class manages the command queue, executes commands in sequence,
    and ensures proper command-response pairing to prevent race conditions.
    
    Signals:
        command_finished(str, str): Emitted when a command completes (command, response)
        error_occurred(str): Emitted when an error occurs during processing
    """
    command_finished = Signal(str, str)    # Command, Response string
    error_occurred = Signal(str)           # Error message
    
    def __init__(self, connection: ConnectionInterface):
        """
        Initialize the worker with a connection interface.
        
        Args:
            connection: The ConnectionInterface instance to use for communication
        """
        super().__init__()
        self.connection = connection
        self.command_queue = queue.Queue()
        self.running = True
        self._last_command = None
        
    @Slot()
    def process_commands(self):
        """
        Main worker loop that processes commands from the queue.
        
        This method runs in a separate thread and handles commands
        sequentially, ensuring proper command-response pairing.
        """
        logger.debug("ConnectionWorker: Starting command processing loop")
        while self.running:
            try:
                # Check for incoming commands
                try:
                    cmd_type, command = self.command_queue.get(block=False)
                    logger.debug(f"ConnectionWorker: Processing {cmd_type} command: {command}")
                    self._handle_command(cmd_type, command)
                except queue.Empty:
                    # No commands to process, check for any incoming data
                    self._check_for_data()
                    time.sleep(0.001)  # Short sleep to prevent CPU hogging
                    
            except Exception as e:
                error_msg = f"Worker error: {str(e)}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
    
    def _handle_command(self, cmd_type: str, command: str):
        """
        Process a single command with appropriate handling based on type.
        
        Args:
            cmd_type: Type of command ('write', 'read', or 'query')
            command: The SCPI command string to execute
        """
        try:
            if cmd_type == "write":
                # Execute write command
                self.connection.write(command)
                self._last_command = command
                
                # If the instrument always sends responses, wait for it
                if getattr(self.connection, 'read_after_write', False):
                    logger.debug(f"ConnectionWorker: Read-after-write enabled, reading response")
                    response = self.connection.read()
                    self.command_finished.emit(command, response)
                else:
                    # No response expected for write
                    self.command_finished.emit(command, "")
                    
            elif cmd_type == "read":
                # Execute read command (no write needed)
                response = self.connection.read()
                self.command_finished.emit("", response)
                
            elif cmd_type == "query":
                # Execute query (write followed by read)
                self.connection.write(command)
                self._last_command = command
                
                # For queries, we must wait for the response
                response = self.connection.read()
                self.command_finished.emit(command, response)
                
        except Exception as e:
            error_msg = f"Error executing {cmd_type} command '{command}': {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def _check_for_data(self):
        """
        Check for any unsolicited data from the instrument.
        
        Some instruments send data without being specifically queried,
        so we check for available data and process it.
        """
        if hasattr(self.connection, 'has_data') and self.connection.has_data():
            try:
                data = self.connection.read_available()
                if data:
                    # Decode the data and emit the signal
                    response = data.decode(self.connection.encoding)
                    logger.debug(f"ConnectionWorker: Received unsolicited data: {response}")
                    self.command_finished.emit("", response)
            except Exception as e:
                error_msg = f"Error reading unsolicited data: {str(e)}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
    
    def write(self, command: str):
        """
        Queue a write command.
        
        Args:
            command: The SCPI command string to send
        """
        logger.debug(f"ConnectionWorker: Queueing write command: {command}")
        self.command_queue.put(("write", command))
        
    def read(self):
        """Queue a read command."""
        logger.debug("ConnectionWorker: Queueing read command")
        self.command_queue.put(("read", ""))
        
    def query(self, command: str):
        """
        Queue a query command.
        
        Args:
            command: The SCPI query command string to send
        """
        logger.debug(f"ConnectionWorker: Queueing query command: {command}")
        self.command_queue.put(("query", command))
    
    def stop(self):
        """Stop the worker thread."""
        logger.debug("ConnectionWorker: Stopping worker")
        self.running = False


class ABCQObjectMeta(type(QObject), ABCMeta):
    """Metaclass that combines QObject and ABC functionality."""
    pass


class Instrument(QObject, metaclass=ABCQObjectMeta):
    """
    Base Instrument class supporting both threaded and direct communication modes.
    
    This class provides the foundation for instrument communication with:
    - Thread-safe operation in GUI applications
    - Synchronous operation in scripting contexts
    - Signal-based communication for UI updates
    - Common SCPI command implementations
    
    Signals:
        commandSent(str): Emitted when a command is sent
        responseReceived(str, str): Emitted when a response is received (command, response)
        exceptionOccured(str): Emitted when an exception occurs
        traceDataReady(np.ndarray, np.ndarray): Emitted when trace data is available (x_data, y_data)
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
        """
        Initialize the instrument with connection and communication parameters.
        
        Args:
            connection: The connection interface to use
            read_after_write: Whether the instrument sends data after every write
            read_timeout: Timeout in seconds for read operations
            threaded_mode: Whether to use threaded communication (None = auto-detect)
            parent: Parent QObject for the Qt object hierarchy
        """
        super().__init__(parent)
        self.connection = connection
        self.read_after_write = read_after_write
        self.read_timeout = read_timeout
        
        # State flags
        self.continuous_mode = False
        self._ready_for_data = True
        self.unique_id = None

        # Response tracking
        self._response_buffer = {}
        self._response_lock = threading.RLock()

        # Determine communication mode
        self._has_gui = QApplication.instance() is not None
        self._threaded_mode = threaded_mode if threaded_mode is not None else self._has_gui
        self._worker = None
        self._worker_thread = None

        logger.debug(f"Instrument initialized with threaded_mode={self._threaded_mode}")
        
        if self._threaded_mode:
            self._setup_worker()

    def _setup_worker(self):
        """
        Initialize connection worker and thread.
        
        Creates a worker instance and moves it to a separate thread for
        asynchronous command processing.
        """
        logger.debug("Instrument: Setting up worker thread")
        
        # Create worker and thread instances
        self._worker = ConnectionWorker(self.connection)
        self._worker_thread = QThread()
        
        # Move worker to thread
        self._worker.moveToThread(self._worker_thread)
        
        # Connect signals
        self._worker_thread.started.connect(self._worker.process_commands)
        self._worker.command_finished.connect(self._handle_worker_response)
        self._worker.error_occurred.connect(self._handle_worker_error)
        
        # Start the thread
        self._worker_thread.start()
        logger.debug("Instrument: Worker thread started")

    def _cleanup_worker(self):
        """
        Clean up worker thread.
        
        Stops the worker, quits the thread, and cleans up resources.
        """
        logger.debug("Instrument: Cleaning up worker thread")
        if self._worker:
            self._worker.stop()
            if self._worker_thread:
                self._worker_thread.quit()
                self._worker_thread.wait(1000)  # Wait up to 1 second for thread to quit
                
            self._worker = None
            self._worker_thread = None
            logger.debug("Instrument: Worker thread cleaned up")

    def open(self):
        """
        Open the connection to the instrument.
        
        Initializes the physical connection and prepares for communication.
        """
        try:
            self.connection.open()
            logger.info("Instrument connection opened")
        except Exception as e:
            logger.exception(f"Failed to open connection: {e}")
            raise

    def close(self):
        """
        Close the connection to the instrument.
        
        Cleans up resources and closes the physical connection.
        """
        self._cleanup_worker()
        try:
            self.connection.close()
            logger.info("Instrument connection closed")
        except Exception as e:
            logger.exception(f"Failed to close connection: {e}")
            raise

    def write(self, command: str) -> None:
        """
        Write a command to the instrument.
        
        Sends a command to the instrument without expecting a response.
        If read_after_write is True, reads and returns the response.
        
        Args:
            command: The SCPI command string to send
            
        Returns:
            Optional response string if read_after_write is True
        """
        desc = f"WRITE: {command}"
        logger.debug(desc)

        try:
            if self._threaded_mode:
                # Send via worker thread
                self._worker.write(command)
            else:
                # Direct communication
                self.connection.write(command)
                
            # Emit signal for UI components
            self.commandSent.emit(command)

            # Read response if needed
            if self.read_after_write:
                return self.read()

        except Exception as e:
            logger.exception(f"Error executing {desc}: {e}")
            self.exceptionOccured.emit(f"{desc} -> {e}")
            raise

    def read(self) -> str:
        """
        Read from the instrument.
        
        Reads data from the instrument without sending a command.
        
        Returns:
            The response string from the instrument
        """
        desc = "READ"
        logger.debug(desc)

        try:
            if self._threaded_mode:
                # Send read request to worker thread
                self._worker.read()
                
                # For GUI context, we need to wait for the response
                if QThread.currentThread() == QApplication.instance().thread():
                    # Use event loop to wait without blocking UI
                    return self._wait_for_response(None)
                else:
                    # For script context, use simpler blocking wait
                    return self._blocking_wait_for_response(None)
            else:
                # Direct communication
                response = self.connection.read()
                self.responseReceived.emit("READ", response)
                return response

        except Exception as e:
            logger.exception(f"Error executing {desc}: {e}")
            self.exceptionOccured.emit(f"{desc} -> {e}")
            raise

    def query(self, command: str) -> str:
        """
        Send a query and get the response.
        
        Handles both threaded GUI and blocking script contexts appropriately.
        
        Args:
            command: The SCPI query command string
            
        Returns:
            The response string from the instrument
            
        Raises:
            TimeoutError: If no response is received within the timeout period
            Exception: For any other communication errors
        """
        desc = f"QUERY: {command}"
        logger.debug(desc)

        try:
            # Check if we're in the main GUI thread
            in_main_thread = self._has_gui and QThread.currentThread() == QApplication.instance().thread()
            
            # In threaded mode and in the main thread, handle differently
            if self._threaded_mode:
                # Send command to worker thread
                self._worker.query(command)
                self.commandSent.emit(command)
                
                if in_main_thread:
                    # Use event loop for GUI context
                    return self._wait_for_response(command)
                else:
                    # Use blocking wait for script context
                    return self._blocking_wait_for_response(command)
            else:
                # Direct communication (no worker)
                self.write(command)
                response = self.connection.read()
                self.responseReceived.emit(command, response)
                return response

        except Exception as e:
            logger.exception(f"Error executing {desc}: {e}")
            self.exceptionOccured.emit(f"{desc} -> {e}")
            raise

    def _wait_for_response(self, command: Optional[str]) -> str:
        """
        Wait for a response using event loop (for GUI context).
        
        Uses Qt's event loop mechanism to wait for the response without
        blocking the UI thread.
        
        Args:
            command: The command that was sent, or None for read operations
            
        Returns:
            The response string
            
        Raises:
            TimeoutError: If no response is received within the timeout period
        """
        from concurrent.futures import Future
        
        result_future = Future()
        
        # One-time handler for this specific command
        def handle_response(cmd, resp):
            # Match if it's the exact command or if this is a read operation
            if (command is None and not cmd) or cmd == command:
                if not result_future.done():
                    result_future.set_result(resp)
        
        # Connect signal temporarily
        conn = self.responseReceived.connect(handle_response)
        
        # Create event loop and timer
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        result_future.add_done_callback(lambda f: loop.quit())
        
        # Start timeout timer
        timeout_ms = int(self.read_timeout * 1000)  # Convert to ms
        timer.start(timeout_ms)
        
        # Wait for response or timeout
        loop.exec_()
        
        # Clean up
        try:
            self.responseReceived.disconnect(conn)
        except Exception:
            pass
        
        if result_future.done():
            return result_future.result()
        else:
            raise TimeoutError(f"Timeout waiting for response to: {command}")

    def _blocking_wait_for_response(self, command: Optional[str]) -> str:
        """
        Wait for a response using a blocking approach (for script context).
        
        This method is used when running in a script thread where it's
        appropriate to block while waiting for the response.
        
        Args:
            command: The command that was sent, or None for read operations
            
        Returns:
            The response string
            
        Raises:
            TimeoutError: If no response is received within the timeout period
        """
        from concurrent.futures import Future
        
        result_future = Future()
        
        # One-time handler for this specific command
        def handle_response(cmd, resp):
            # Match if it's the exact command or if this is a read operation
            if (command is None and not cmd) or cmd == command:
                if not result_future.done():
                    result_future.set_result(resp)
        
        # Connect signal temporarily
        conn = self.responseReceived.connect(handle_response)
        
        # Wait for response with timeout
        timeout_s = self.read_timeout
        start_time = time.time()
        
        while not result_future.done() and (time.time() - start_time < timeout_s):
            # Give a chance for signals to be processed
            if self._has_gui:
                QApplication.processEvents()
            time.sleep(0.001)  # Short sleep to prevent CPU hogging
        
        # Clean up
        try:
            self.responseReceived.disconnect(conn)
        except Exception:
            pass
        
        if result_future.done():
            return result_future.result()
        else:
            raise TimeoutError(f"Timeout waiting for response to: {command}")

    def _handle_worker_response(self, command: str, response: str):
        """
        Handle responses from worker thread.
        
        This method is called when the worker thread completes a command
        and emits a command_finished signal.
        
        Args:
            command: The command that was sent
            response: The response from the instrument
        """
        # Store response in buffer for synchronization
        with self._response_lock:
            self._response_buffer[command if command else "READ"] = response
        
        # Emit the signal for any UI listeners
        self.responseReceived.emit(command, response)
        logger.debug(f"Response received for {command if command else 'READ'}: {response}")

    def _handle_worker_error(self, error: str):
        """
        Handle errors from worker thread.
        
        Args:
            error: The error message
        """
        logger.error(f"Worker error: {error}")
        self.exceptionOccured.emit(error)

    def set_continuous_mode(self, mode: bool):
        """
        Set continuous mode flag.
        
        Args:
            mode: Whether to enable continuous mode
        """
        logger.debug(f"Set continuous mode to {mode}")
        self.continuous_mode = mode
        self._ready_for_data = not mode

    def set_unique_id(self, uid: str):
        """
        Set unique identifier for this instrument.
        
        Args:
            uid: Unique identifier string
        """
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
        """
        Decorator for GUI-related commands.
        
        This can be used to mark commands that should only be executed
        in GUI context or that require special handling.
        
        Example:
            @Instrument.gui_command
            def update_display(self, data):
                # This method will be marked as GUI-related
                pass
        """
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
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                list(executor.map(query_visa_device, visa_resources.values()))

        except Exception as e:
            logger.warning(f"VISA discovery error: {e}")

        logger.info(f"Discovery complete. Found {len(instruments)} instruments")
        return instruments


class SCPIInstrument(Instrument):
    """
    A specialized Instrument for SCPI-compatible devices.
    
    Provides common IEEE 488.2 commands and utilities for SCPI instruments.
    
    Args:
        connection (ConnectionInterface): The connection to use
        read_after_write (bool): Whether to read after every write (default: False)
        timeout (int): Default timeout for operations in milliseconds (default: 5000)
        parent (QObject): Parent QObject (default: None)
    """

    def __init__(self, connection, read_after_write=False, timeout=5000, parent=None, **kwargs):
        super().__init__(connection, read_after_write=read_after_write, parent=parent, **kwargs)
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
        response = self.query("*IDN?")
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
        """
        Waits for operation complete (*OPC?).
        
        Returns:
            str: The operation complete response (typically "1")
        """
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
        
        Args:
            response: The binary response data
            
        Returns:
            tuple: (data_bytes, header_length)
            
        Raises:
            ValueError: If the binary header is invalid
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
        self.write(full_command)

    def read_binary_data(self) -> np.ndarray:
        """
        Reads binary data from instrument and converts to numpy array.
        
        Returns:
            numpy.ndarray: Parsed data array
        """
        response = self.read()
        data, _ = self._parse_binary_header(response)
        return np.frombuffer(data, dtype=self._data_type)


class Subsystem:
    """
    Base class for creating instrument subsystems.
    
    Subsystems encapsulate related instrument functionality and handle
    command prefix cascading for nested subsystem hierarchies.
    
    Examples:
        # Single subsystem instance
        scope = SCPIInstrument(connection)
        scope.timebase = Timebase(scope, "TIM")  # Creates a Timebase subsystem
        
        # Creating multiple indexed instances (e.g., channels)
        scope.channels = Channel.build(scope, "CHAN", 4)  # Creates channels 1-4
        # Now scope.channels[1] refers to channel 1
    """

    def __init__(self, instr, cmd_prefix="", index=None):
        """
        Initializes a Subsystem instance.

        Args:
            instr (Instrument or Subsystem): The parent instrument or subsystem
            cmd_prefix (str): The command prefix specific to this subsystem
            index (int, optional): If provided, specifies the index for this instance
        """
        self.instr = instr
        logger.debug(f"Initializing subsystem with prefix '{cmd_prefix}', and index {index}")
        
        # Handle cascading of command prefixes for nested subsystems
        parent_prefix = getattr(instr, 'cmd_prefix', '')
        
        # Build the command prefix without adding any colons
        self.cmd_prefix = parent_prefix + cmd_prefix
        
        # Add index to prefix if provided
        if index is not None:
            self.cmd_prefix += str(index)
            
        logger.debug(f"Subsystem command prefix set to '{self.cmd_prefix}'")

    def write(self, command: str) -> None:
        """
        Forward write command to parent instrument with proper prefix.

        Args:
            command (str): The SCPI command string to send
        """
        full_command = f"{self.cmd_prefix}{command}"
        logger.debug(f"Subsystem forwarding WRITE command: '{full_command}'")
        return self.instr.write(full_command)

    def read(self) -> str:
        """
        Forward read command to parent instrument.

        Returns:
            str: The response string from the instrument
        """
        logger.debug("Subsystem forwarding READ command")
        return self.instr.read()

    def query(self, command: str) -> str:
        """
        Forward query command to parent instrument with proper prefix.

        Args:
            command (str): The SCPI query command string

        Returns:
            str: The response string from the instrument
        """
        full_command = f"{self.cmd_prefix}{command}"
        logger.debug(f"Subsystem forwarding QUERY command: '{command}'")
        return self.instr.query(full_command)

    @classmethod
    def build(cls, parent, cmd_prefix, indices=None):
        """
        Class method to instantiate subsystems. Handles both single and indexed instances.

        Args:
            parent (Instrument or Subsystem): The parent object for the new subsystem(s)
            cmd_prefix (str): The SCPI command prefix
            indices (int, optional): Number of indexed instances to create

        Returns:
            Subsystem or list of Subsystem: Single instance or list of indexed instances
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

    def fetch_trace(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fetch a trace from this subsystem.
        
        Default implementation that can be overridden by subclasses.
        
        Returns:
            tuple: (x_data, y_data) as numpy arrays
        """
        # Default implementation - subclasses should override this
        logger.warning(f"Default fetch_trace implementation called for {self.__class__.__name__}")
        return np.array([]), np.array([])