"""
Connection interfaces for instrument communication.
Defines base interface and VISA implementation.
"""

from abc import ABC, ABCMeta, abstractmethod
import logging
import socket
import select
import time
from typing import Optional, Dict
import ipaddress
import pyvisa
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

try:
    from pymetr.drivers.registry import DRIVER_REGISTRY, get_driver_info
    from pymetr.logging import logger
except ImportError:
    from registry import DRIVER_REGISTRY, get_driver_info

class ABCQObjectMeta(type(QObject), ABCMeta):
    """Metaclass that combines QObject and ABC functionality."""
    pass

class DiscoverySignals(QObject):
    """Class to hold discovery signals"""
    instrument_found = Signal(dict)

class ConnectionInterface(QObject, ABC, metaclass=ABCQObjectMeta):
    """
    Abstract base class for all instrument connections.
    Provides common interface and non-blocking I/O support.
    """
    # Static signals instance
    _signals = DiscoverySignals()
    
    def __init__(self, read_termination: str = '\n', 
                 write_termination: str = '\n', 
                 encoding: str = 'ascii'):
        """Initialize connection parameters."""
        super().__init__()
        self.read_termination = read_termination.encode(encoding) if isinstance(read_termination, str) else read_termination
        self.write_termination = write_termination
        self.encoding = encoding
        self._read_buffer = bytearray()
        self._has_gui = QApplication.instance() is not None

    def _process_events(self):
        """Process GUI events if in GUI context."""
        if self._has_gui:
            QApplication.processEvents()

    @abstractmethod
    def open(self):
        """Opens the connection to the instrument."""
        pass

    @abstractmethod
    def close(self):
        """Closes the connection to the instrument."""
        pass

    @abstractmethod
    def write(self, command: str):
        """Writes a command string to the instrument."""
        pass

    @abstractmethod
    def has_data(self) -> bool:
        """Check if there is data available to read without blocking."""
        pass

    @abstractmethod
    def read_available(self) -> bytes:
        """Read whatever data is currently available without blocking."""
        pass

    def read(self) -> str:
        """
        Default implementation of blocking read using has_data() and read_available().
        Can be overridden if a more efficient implementation exists.
        """
        while True:
            # Check for complete message in buffer
            if self.read_termination in self._read_buffer:
                term_pos = self._read_buffer.find(self.read_termination)
                message = self._read_buffer[:term_pos].decode(self.encoding)
                self._read_buffer = self._read_buffer[term_pos + len(self.read_termination):]
                return message

            # Read any available data
            if self.has_data():
                chunk = self.read_available()
                if chunk:
                    self._read_buffer.extend(chunk)
                continue

            # No data available - block until data arrives
            chunk = self.read_available()  # This should block
            if chunk:
                self._read_buffer.extend(chunk)

            # Keep UI responsive
            self._process_events()
            time.sleep(0.001)  # Small sleep to prevent busy-waiting

    def query(self, command: str) -> str:
        """Write followed by read."""
        self.write(command)
        return self.read()

    def clear_buffer(self):
        """Clear any partially read data."""
        self._read_buffer.clear()


class PyVisaConnection(ConnectionInterface):
    """VISA-based connection implementation supporting GPIB, USB, and VXI-11."""

    def __init__(self, resource_string: str, timeout: int = 5000,
                 read_termination: str = '\n', write_termination: str = '\n',
                 encoding: str = 'ascii'):
        """
        Initialize VISA connection.
        
        Args:
            resource_string: VISA resource identifier
            timeout: I/O timeout in milliseconds
            read_termination: Character(s) marking end of received messages
            write_termination: Character(s) to append to sent messages
            encoding: Character encoding for string conversion
        """
        super().__init__(read_termination=read_termination,
                        write_termination=write_termination,
                        encoding=encoding)
        self.resource_string = resource_string
        self.timeout = timeout
        self.rm = pyvisa.ResourceManager()
        self.inst = None
        self._srq_supported = False

    def open(self):
        """Open the VISA session and configure it."""
        logger.debug(f"Opening VISA connection for resource: {self.resource_string}")
        try:
            self.inst = self.rm.open_resource(self.resource_string)
            self.inst.timeout = self.timeout
            self.inst.read_termination = self.write_termination
            self.inst.write_termination = self.write_termination

            # Try to enable SRQ if supported
            try:
                self.inst.write("*SRE 16")  # Enable MAV bit in SRE
                self._srq_supported = True
            except pyvisa.Error:
                logger.debug("SRQ not supported by instrument")
                self._srq_supported = False

            logger.info(f"VISA connection opened for {self.resource_string}")
        except Exception as e:
            logger.exception(f"Failed to open VISA connection: {e}")
            raise

    def close(self):
        """Close the VISA session."""
        if self.inst is not None:
            logger.debug(f"Closing VISA connection for resource: {self.resource_string}")
            try:
                self.inst.close()
            finally:
                self.inst = None
                logger.info(f"VISA connection closed")

    def write(self, command: str):
        """Write a command string to the instrument."""
        if not self.inst:
            raise ConnectionError("VISA instrument not open. Call open() first.")
            
        logger.debug(f"VISA write: {command}")
        try:
            self.inst.write(command)
        except Exception as e:
            logger.exception(f"VISA write failed: {e}")
            raise

    def has_data(self) -> bool:
        """Check if data is available to read."""
        if not self.inst:
            raise ConnectionError("VISA instrument not open")

        try:
            if self._srq_supported:
                # Use STB polling for data availability
                stb = self.inst.read_stb()
                return bool(stb & 0x10)  # Check MAV bit
            else:
                # Try a non-blocking read
                orig_timeout = self.inst.timeout
                self.inst.timeout = 0
                try:
                    self.inst.read_bytes(1)
                    return True
                except pyvisa.VisaIOError as e:
                    if e.error_code == pyvisa.constants.StatusCode.error_timeout:
                        return False
                    raise
                finally:
                    self.inst.timeout = orig_timeout
        except Exception as e:
            logger.exception(f"Error checking for data: {e}")
            raise

    def read_available(self) -> bytes:
        """Read available data from the instrument."""
        if not self.inst:
            raise ConnectionError("VISA instrument not open")

        try:
            # If data is available, read it
            if self.has_data():
                return self.inst.read_raw()

            # No immediate data - wait for timeout period
            if self._srq_supported:
                # Wait for SRQ
                if self.inst.wait_for_srq(self.timeout / 1000):
                    return self.inst.read_raw()
            else:
                # Regular timeout-based read
                try:
                    return self.inst.read_raw()
                except pyvisa.VisaIOError as e:
                    if e.error_code == pyvisa.constants.StatusCode.error_timeout:
                        return b''
                    raise

            return b''

        except Exception as e:
            logger.exception(f"Error reading available data: {e}")
            raise

    @classmethod
    def list_instruments(cls, query: str = "?*::INSTR") -> Dict[str, str]:
        """
        List available VISA resources.
        Emits instrument_found signal for each discovered device.
        """
        discovered = {}
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources(query)
            logger.debug(f"Found VISA resources: {list(resources)}")
            
            # Filter out serial ports during testing
            resources = [r for r in resources if not r.startswith("ASRL")]
            
            # Try to identify each resource
            for resource in resources:
                try:
                    with rm.open_resource(resource) as inst:
                        # Set short timeout for ID query
                        inst.timeout = 1000
                        
                        # Query identity
                        idn = inst.query("*IDN?").strip()
                        parts = [p.strip() for p in idn.split(',')]
                        
                        if len(parts) >= 2:
                            manufacturer = parts[0]
                            model = parts[1]
                            serial = parts[2] if len(parts) > 2 else None
                            firmware = parts[3] if len(parts) > 3 else None
                            
                            # Try to get driver info
                            try:
                                driver_info = get_driver_info(model)
                                
                                # Create device info
                                device_info = {
                                    'manufacturer': manufacturer,
                                    'model': model,
                                    'serial': serial,
                                    'firmware': firmware,
                                    'resource': resource,
                                    'driver_info': driver_info,
                                    'idn': idn
                                }
                                
                                # Emit signal
                                cls._signals.instrument_found.emit(device_info)
                                
                                # Add to discovered devices
                                discovered[model] = device_info
                                
                            except ValueError:
                                logger.debug(f"No driver found for model: {model}")
                            
                except Exception as e:
                    logger.debug(f"Could not identify {resource}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"VISA resource discovery failed: {e}")
            
        logger.info(f"VISA discovery complete. Found {len(discovered)} devices")
        return discovered

class RawSocketConnection(ConnectionInterface):
    """TCP Socket-based connection with UDP discovery support."""
    
    DISCOVERY_PORT = 30303  # Default discovery port for Microchip stack
    
    def __init__(self, host: str, port: int = 5025, timeout: float = 2.5,
                 encoding: str = 'ascii', read_termination: str = '\n',
                 write_termination: str = '\n'):
        """
        Initialize socket connection parameters.
        
        Args:
            host: IP address or hostname
            port: TCP port number (default: 5025 for SCPI)
            timeout: Socket timeout in seconds
            encoding: Character encoding for string conversion
            read_termination: Character(s) marking end of received messages
            write_termination: Character(s) to append to sent messages
        """
        super().__init__(read_termination=read_termination,
                        write_termination=write_termination,
                        encoding=encoding)
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None

    def open(self):
        """Open the socket connection."""
        logger.debug(f"Opening socket connection to {self.host}:{self.port}")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))
            self.sock.setblocking(False)  # Enable non-blocking mode
            logger.info(f"Socket connected to {self.host}:{self.port}")
        except socket.error as e:
            logger.exception(f"Failed to connect to {self.host}:{self.port}")
            raise

    def close(self):
        """Close the socket connection."""
        if self.sock:
            logger.debug(f"Closing socket connection to {self.host}:{self.port}")
            try:
                self.sock.close()
            finally:
                self.sock = None
                logger.info(f"Socket connection closed")

    def write(self, command: str):
        """Send a command string to the instrument."""
        if not self.sock:
            raise ConnectionError("Socket not open")

        # Ensure command ends with termination
        if not command.endswith(self.write_termination):
            command += self.write_termination

        data = command.encode(self.encoding)
        logger.debug(f"Socket write: {command.strip()}")

        try:
            self.sock.sendall(data)
        except socket.error as e:
            logger.exception(f"Socket write failed")
            raise

    def has_data(self) -> bool:
        """Check if data is available using select."""
        if not self.sock:
            raise ConnectionError("Socket not open")

        try:
            readable, _, _ = select.select([self.sock], [], [], 0)
            return bool(readable)
        except select.error as e:
            logger.exception(f"Select failed")
            raise

    def read_available(self) -> bytes:
        """Read available data from socket."""
        if not self.sock:
            raise ConnectionError("Socket not open")

        try:
            # If data is immediately available, read it
            if self.has_data():
                return self.sock.recv(4096)

            # No data - wait for timeout period
            readable, _, _ = select.select([self.sock], [], [], self.timeout)
            if readable:
                return self.sock.recv(4096)
            return b''
            
        except socket.error as e:
            logger.exception(f"Socket read failed")
            raise

    @staticmethod
    def get_broadcast_addresses() -> list:
        """Get list of broadcast addresses for all network interfaces."""
        broadcasts = []
        try:
            for iface in socket.getaddrinfo(socket.gethostname(), None):
                addr = iface[4][0]
                try:
                    # Only interested in IPv4 addresses
                    if ':' not in addr and not addr.startswith('127.'):
                        network = ipaddress.IPv4Network(f"{addr}/24", strict=False)
                        broadcasts.append(str(network.broadcast_address))
                except ValueError:
                    continue
        except Exception as e:
            logger.warning(f"Error getting broadcast addresses: {e}")
            broadcasts.append('255.255.255.255')
            
        return broadcasts if broadcasts else ['255.255.255.255']

    @classmethod
    def list_instruments(cls, timeout: float = 1.0) -> Dict[str, dict]:
        """
        List available instruments using UDP broadcast and SCPI query.
        Emits instrument_found signal for each discovered device.
        """
        discovered = {}
        logger.debug("Starting UDP instrument discovery")
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.settimeout(timeout)
                sock.bind(('', cls.DISCOVERY_PORT))
                
                # Get broadcasts, excluding loopback
                broadcasts = cls.get_broadcast_addresses()
                broadcasts = [addr for addr in broadcasts 
                            if not addr.startswith('127.')]
                logger.debug(f"Broadcasting to: {broadcasts}")
                
                # Send discovery message to each broadcast address
                for broadcast in broadcasts:
                    try:
                        message = b"Discovery: Who is out there!"
                        sock.sendto(message, (broadcast, cls.DISCOVERY_PORT))
                        logger.debug(f"Sent discovery message to {broadcast}")
                    except Exception as e:
                        logger.warning(f"Failed to send to {broadcast}: {e}")
                        continue
                
                # Collect responding IPs
                responding_ips = set()
                start_time = time.time()
                
                # Listen for responses
                while time.time() - start_time < timeout:
                    try:
                        data, addr = sock.recvfrom(4096)
                        host = addr[0]
                        
                        # Try to decode as ASCII to check if it's our discovery message
                        try:
                            message = data.decode('ascii').strip()
                            if message == "Discovery: Who is out there!":
                                logger.debug(f"Skipping discovery echo from {host}")
                                continue
                            logger.debug(f"Received ASCII response from {host}: {message}")
                        except UnicodeDecodeError:
                            logger.debug(f"Received binary response from {host}")
                            
                        logger.debug(f"Adding {host} to responding IPs list")
                        responding_ips.add(host)
                            
                    except socket.timeout:
                        break
                
                logger.debug(f"Found {len(responding_ips)} responding IPs: {responding_ips}")
                
                # Query each responding IP
                for host in responding_ips:
                    try:
                        # Try default Holzworth port
                        port = 9760
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(1.0)  # Short timeout for IDN query
                            logger.debug(f"Attempting connection to {host}:{port}")
                            s.connect((host, port))
                            
                            logger.debug(f"Connected to {host}:{port}, sending *IDN?")
                            s.send(b"*IDN?\n")
                            idn = s.recv(1024).decode('ascii').strip()
                            logger.debug(f"Received IDN response: {idn}")
                            
                            if idn:
                                parts = [p.strip() for p in idn.split(',')]
                                if len(parts) >= 2:
                                    manufacturer = parts[0]
                                    model = parts[1]
                                    serial = parts[2] if len(parts) > 2 else None
                                    firmware = parts[3] if len(parts) > 3 else None
                                    
                                    logger.debug(f"Parsed IDN parts: manufacturer='{manufacturer}', "
                                            f"model='{model}', serial='{serial}', "
                                            f"firmware='{firmware}'")
                                    
                                    try:
                                        driver_info = get_driver_info(model)
                                        logger.debug(f"Found driver info for {model}")
                                        
                                        device_info = {
                                            'manufacturer': manufacturer,
                                            'model': model,
                                            'serial': serial,
                                            'firmware': firmware,
                                            'resource': f"TCPIP::{host}::{port}::SOCKET",
                                            'address': host,
                                            'port': port,
                                            'idn': idn,
                                            'driver_info': driver_info
                                        }
                                        
                                        logger.debug(f"Created device info: {device_info}")
                                        
                                        # Add to discovered devices
                                        discovered[model] = device_info
                                        logger.debug(f"Added {model} to discovered dict")
                                        
                                        # Emit signal
                                        cls._signals.instrument_found.emit(device_info)
                                        logger.debug(f"Emitted instrument_found signal for {model}")
                                        
                                    except ValueError as e:
                                        logger.debug(f"No driver found for model: {model}")
                                else:
                                    logger.debug(f"Invalid IDN response format: {idn}")
                            else:
                                logger.debug(f"Empty IDN response from {host}")
                                
                    except Exception as e:
                        logger.debug(f"Failed to query {host}: {e}")
                        
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
        
        logger.debug(f"Final discovered dict contents: {discovered}")
        logger.info(f"Discovery complete. Found {len(discovered)} devices")
        return discovered

    @staticmethod
    def parse_resource_string(resource: str) -> tuple[str, int]:
        """Parse VISA resource string into host and port."""
        if resource.startswith("TCPIP::"):
            parts = resource.split("::")
            if len(parts) >= 3:
                return parts[1], int(parts[2])
        elif ":" in resource:
            host, port = resource.split(":")
            return host.strip(), int(port)
            
        return resource, 5025  # Default SCPI port
    
if __name__ == "__main__":
    import sys
    
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Need QApp for signal handling
    app = QApplication(sys.argv)
    
    def on_instrument_found(info: dict):
        """Print discovered instruments"""
        model = info.get('model', 'Unknown')
        resource = info.get('resource', 'Unknown')
        print(f"\nFound: {model} at {resource}")
        if 'idn' in info:
            print(f"IDN: {info['idn']}")
    
    # Connect discovery signals
    PyVisaConnection._signals.instrument_found.connect(on_instrument_found)
    
    # Test VISA discovery
    print("\nTesting VISA discovery...")
    start = time.time()
    visa_devices = PyVisaConnection.list_instruments()
    print(f"VISA discovery took {time.time() - start:.2f}s")
    
    print(f"\nTotal devices found: {len(visa_devices)}")
    
    # Process any pending events
    app.processEvents()

    # Test both discovery methods
    print("\nTesting VISA discovery...")
    start = time.time()
    visa_devices = PyVisaConnection.list_instruments()
    print(f"VISA discovery took {time.time() - start:.2f}s")
    
    print("\nTesting UDP discovery...")
    start = time.time()
    socket_devices = RawSocketConnection.list_instruments(timeout=2.0)
    print(f"UDP discovery took {time.time() - start:.2f}s")
    
    print(f"\nTotal devices found: {len(visa_devices) + len(socket_devices)}")
    
    try:
        while True:
            app.processEvents()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nTest complete!")

