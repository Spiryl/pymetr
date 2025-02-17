# connections.py

"""
Defines the abstract base class (interface) for all instrument connections.
Adds support for non-blocking reads and data availability checking.
"""

from abc import ABC, abstractmethod
import logging
import socket
import select
import time
from typing import Optional, Dict, List
import ipaddress
from zeroconf import ServiceBrowser, Zeroconf
import concurrent.futures
import pyvisa
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

class ConnectionInterface(ABC):
    """
    An abstract base class representing the low-level connection or transport layer.
    Every specific transport (PyVISA, raw socket, serial, etc.) must implement these methods.
    """

    def __init__(self, read_termination: str = '\n', write_termination: str = '\n', encoding: str = 'ascii'):
        """
        Initialize common connection parameters.

        Args:
            read_termination: Character(s) marking end of received messages
            write_termination: Character(s) to append to sent messages
            encoding: Character encoding for string conversion
        """
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
        """
        Writes a command string to the instrument.

        Args:
            command: The command string to send
        """
        pass

    @abstractmethod
    def has_data(self) -> bool:
        """
        Check if there is data available to read without blocking.

        Returns:
            bool: True if data is available to read without blocking
        """
        pass

    @abstractmethod
    def read_available(self) -> bytes:
        """
        Read whatever data is currently available without blocking.

        Returns:
            bytes: The currently available data (may be empty)
        """
        pass

    def read(self) -> str:
        """
        Default implementation of blocking read that uses has_data() and read_available().
        Can be overridden by subclasses if a more efficient implementation exists.

        Returns:
            str: The complete response string
        """
        while True:
            # Check for complete message in buffer
            if self.read_termination in self._read_buffer:
                # Find the terminator
                term_pos = self._read_buffer.find(self.read_termination)
                # Extract the message
                message = self._read_buffer[:term_pos].decode(self.encoding)
                # Remove processed data from buffer
                self._read_buffer = self._read_buffer[term_pos + len(self.read_termination):]
                return message

            # Read any available data
            if self.has_data():
                chunk = self.read_available()
                if chunk:
                    self._read_buffer.extend(chunk)
                continue

            # No data available and no complete message - block until data arrives
            chunk = self.read_available()  # This should block
            if chunk:
                self._read_buffer.extend(chunk)

    def query(self, command: str) -> str:
        """
        Default implementation of write followed by read.
        Can be overridden by subclasses if a more efficient implementation exists.

        Args:
            command: The command string to send

        Returns:
            str: The response string
        """
        self.write(command)
        return self.read()

    def clear_buffer(self):
        """Clear any partially read data from the buffer."""
        self._read_buffer.clear()


class PyVisaConnection(ConnectionInterface):
    """
    Implements the ConnectionInterface using PyVISA to communicate with instruments.
    Supports non-blocking reads through PyVISA's asynchronous I/O capabilities.
    """

    def __init__(self, resource_string: str, timeout: int = 5000,
                 read_termination: str = '\n', write_termination: str = '\n',
                 encoding: str = 'ascii'):
        """
        Initialize PyVISA connection parameters.

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
        self._last_status = 0

    @staticmethod
    def list_instruments(query: str = "TCPIP?*::INSTR") -> Dict[str, str]:
        """List VISA resources without querying IDN."""
        logger.debug(f"PyVISA list_instruments called with query: '{query}'")
        discovered_devices = {}
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources(query)
            logger.debug(f"PyVISA discovered resources: {list(resources)}")
            
            # Just map resource strings to themselves
            for resource in resources:
                discovered_devices[resource] = resource
                
        except Exception as e:
            logger.exception(f"PyVISA failed to list instruments: {e}")
                
        return discovered_devices
    
    @staticmethod
    def select_instrument(filter_query="TCPIP?*::INSTR"):
        """Utility method to interactively list and select VISA resources."""
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources(filter_query)
            if not resources:
                print("No VISA instruments found matching your filter. Check connections.")
                raise SystemExit(0)

            print("\nAvailable Instruments:")
            for i, r in enumerate(resources, start=1):
                print(f"{i}. {r}")

            selection = input("\nSelect an instrument by number (or 'exit' to quit): ")
            if selection.lower() == 'exit':
                raise SystemExit(0)

            index = int(selection) - 1
            if index < 0 or index >= len(resources):
                raise ValueError("Invalid selection.")

            return resources[index]
        except Exception as e:
            logger.exception(f"select_instrument failed: {e}")
            raise

    def read_sync(self) -> str:
        """
        Synchronous (blocking) read operation for non-GUI contexts.
        This provides a simpler, more efficient read when async operation isn't needed.

        Returns:
            str: The complete response string
        """
        if not self.inst:
            raise ConnectionError("PyVISA instrument not open. Call open() first.")
            
        try:
            response = self.inst.read()
            logger.debug(f"PyVISA sync read response: {response}")
            return response
        except Exception as e:
            logger.exception(f"Error in sync read: {e}")
            raise

    def open(self):
        """Open the VISA session and configure it for asynchronous operation."""
        logger.debug(f"Opening PyVISA connection for resource: {self.resource_string}")
        self.inst = self.rm.open_resource(self.resource_string)
        self.inst.timeout = self.timeout
        self.inst.read_termination = self.write_termination
        self.inst.write_termination = self.write_termination

        # Enable Service Request generation if supported
        try:
            # Enable SRQ on data available
            self.inst.write("*SRE 16")  # Enable MAV bit in SRE
            self._srq_supported = True
        except pyvisa.Error:
            logger.debug("SRQ not supported by instrument")
            self._srq_supported = False

        logger.info(f"PyVISA connection opened for {self.resource_string}")

    def close(self):
        """Close the VISA session."""
        if self.inst is not None:
            logger.debug(f"Closing PyVISA connection for resource: {self.resource_string}")
            try:
                self.inst.close()
            finally:
                self.inst = None
                logger.info(f"PyVISA connection closed for {self.resource_string}")

    def write(self, command: str):
        """
        Write a command string to the instrument.

        Args:
            command: The command string to send
        """
        if not self.inst:
            raise ConnectionError("PyVISA instrument not open. Call open() first.")
        logger.debug(f"PyVISA write: {command}")
        self.inst.write(command)

    def has_data(self) -> bool:
        """
        Check if data is available to read without blocking.

        Returns:
            bool: True if data is available
        """
        if not self.inst:
            raise ConnectionError("PyVISA instrument not open. Call open() first.")

        try:
            if self._srq_supported:
                # Use STB polling for data availability
                stb = self.inst.read_stb()
                return bool(stb & 0x10)  # Check MAV bit
            else:
                # Fall back to VI_ATTR_TMO_VALUE=0 read attempt
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
        """
        Read whatever data is currently available.
        If no data is available, blocks for up to timeout period.

        Returns:
            bytes: The currently available data (may be empty)
        """
        if not self.inst:
            raise ConnectionError("PyVISA instrument not open. Call open() first.")

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


class RawSocketConnection(ConnectionInterface):
    """
    Implements a raw socket-based connection for instruments that communicate over TCP/IP
    without requiring a VISA driver. Supports non-blocking reads.
    """

    # Default discovery port for Microchip TCP/IP Stack (PIC32MX/MZ)
    DISCOVERY_PORT = 30303

    @staticmethod
    def parse_resource_string(resource: str) -> tuple[str, int]:
        """Parse various resource string formats into host and port."""
        # Handle TCPIP resource string format
        if resource.startswith("TCPIP::"):
            parts = resource.split("::")
            if len(parts) >= 3:
                return parts[1], int(parts[2])
        
        # Handle direct IP:port format
        if ":" in resource:
            host, port = resource.split(":")
            return host.strip(), int(port)
            
        # If just an IP/hostname is provided
        return resource, 5025  # Default SCPI port
    
    def __init__(self, host: str, port: int = 5025, timeout: float = 2.5,
                 encoding: str = 'ascii', read_termination: str = '\n',
                 write_termination: str = '\n'):
        """
        Initialize socket connection parameters.
        
        Args:
            host: IP address, hostname, or resource string
            port: TCP port number (default: 5025 for SCPI)
            timeout: Socket timeout in seconds
            encoding: Character encoding for string conversion
            read_termination: Character(s) marking end of received messages
            write_termination: Character(s) to append to sent messages
        """
        super().__init__(read_termination=read_termination,
                        write_termination=write_termination,
                        encoding=encoding)
                        
        # Handle if host is actually a resource string
        if isinstance(host, str) and ("::" in host or ":" in host):
            self.host, parsed_port = self.parse_resource_string(host)
            self.port = port if port != 5025 else parsed_port  # Use explicitly provided port if given
        else:
            self.host = host
            self.port = port
            
        self.timeout = timeout
        self.sock = None

    def open(self):
        """Open the socket connection to the instrument."""
        logger.debug(f"Opening raw socket connection to {self.host}:{self.port}")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))
            # Set non-blocking mode after connection
            self.sock.setblocking(False)
            logger.info(f"Raw socket connection established to {self.host}:{self.port}")
        except socket.error as e:
            logger.exception(f"Failed to connect to {self.host}:{self.port} - {e}")
            raise

    def close(self):
        """Close the socket connection."""
        if self.sock is not None:
            logger.debug(f"Closing raw socket connection to {self.host}:{self.port}")
            try:
                self.sock.close()
            finally:
                self.sock = None
                logger.info(f"Raw socket connection closed for {self.host}:{self.port}")

    def write(self, command: str):
        """
        Send a command string to the instrument.

        Args:
            command: The command string to send
        """
        if not self.sock:
            raise ConnectionError("Raw socket not open. Call open() first.")

        # Append termination if not already present
        if not command.endswith(self.write_termination):
            command += self.write_termination

        data = command.encode(self.encoding)
        logger.debug(f"Raw socket write: {command.strip()}")

        try:
            self.sock.sendall(data)
        except socket.error as e:
            logger.exception(f"Failed to send data to {self.host}:{self.port} - {e}")
            raise

    def has_data(self) -> bool:
        """
        Check if data is available to read without blocking.

        Returns:
            bool: True if data is available
        """
        if not self.sock:
            raise ConnectionError("Raw socket not open. Call open() first.")

        try:
            readable, _, _ = select.select([self.sock], [], [], 0)
            return bool(readable)
        except select.error as e:
            logger.exception(f"Select error checking for data: {e}")
            raise

    def read_available(self) -> bytes:
        """
        Read whatever data is currently available without blocking.
        If no data is available, blocks for up to timeout seconds.

        Returns:
            bytes: The currently available data (may be empty)
        """
        if not self.sock:
            raise ConnectionError("Raw socket not open. Call open() first.")

        try:
            # If data is immediately available, read it
            if self.has_data():
                return self.sock.recv(4096)

            # No data available - wait for timeout period
            readable, _, _ = select.select([self.sock], [], [], self.timeout)
            if readable:
                return self.sock.recv(4096)
            return b''
        except socket.error as e:
            logger.exception(f"Failed to read data from {self.host}:{self.port} - {e}")
            raise

    @staticmethod
    def list_instruments(methods: List[str] = ['udp', 'mdns', 'scan'], timeout: float = 5.0) -> Dict[str, str]:
        """
        Discover raw socket instruments using various methods.

        Args:
            methods (list): Methods to use for discovery ('udp', 'mdns', 'scan').
            timeout (float): Timeout for discovery methods in seconds.

        Returns:
            dict[str, str]: A dictionary mapping unique IDs to resource strings.
        """
        discovered_devices = {}

        # Discover all local IP ranges
        local_ip_ranges = RawSocketConnection.get_all_local_ip_ranges()
        logger.debug(f"Detected local IP ranges: {local_ip_ranges}")

        for ip_range in local_ip_ranges:
            if 'udp' in methods:
                devices = RawSocketConnection._discover_udp(timeout, ip_range)
                discovered_devices.update(devices)

            # Implement these in a full scan.
            # if 'mdns' in methods and not discovered_devices:
            #     devices = RawSocketConnection._discover_mdns(timeout)
            #     discovered_devices.update(devices)

            # if 'scan' in methods and not discovered_devices:
            #     devices = RawSocketConnection._discover_scan(ip_range=ip_range, timeout=timeout)
            #     discovered_devices.update(devices)

        logger.debug(f"RawSocket discovered devices before filtering: {discovered_devices}")

        # Filtering will be handled externally in Instrument.list_instruments

        return discovered_devices

    @staticmethod
    def _discover_udp(timeout: float, ip_range: str) -> Dict[str, str]:
        """Discover instruments via UDP broadcast within a specific IP range."""
        discovered_devices = {}
        discovered_ips = set()  
        port = 30303  # PIC32 discovery port

        # Check for GUI context once
        has_gui = QApplication.instance() is not None

        # Derive broadcast address from IP range
        network = ipaddress.ip_network(ip_range, strict=False)
        broadcast_address = str(network.broadcast_address)

        logger.debug(f"Starting UDP discovery on {broadcast_address}:{port}")

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.bind(('', port))
                sock.settimeout(timeout)

                # Send discovery message
                discovery_message = b"Discovery: Who is out there!"
                sock.sendto(discovery_message, (broadcast_address, port))
                logger.debug(f"Sent UDP discovery message to {broadcast_address}:{port}")

                # Collect responses
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        data, addr = sock.recvfrom(4096)
                        logger.debug(f"Received UDP response from {addr}")
                        discovered_ips.add(addr[0])
                    except socket.timeout:
                        pass
                    
                    if has_gui:
                        QApplication.processEvents()

        except Exception as e:
            logger.exception(f"Failed to perform UDP discovery: {e}")

        # Now try to identify devices on standard ports using parallel scanning
        instrument_ports = [9760]
        discovered_resources = {}

        def scan_port(ip, port):
            if has_gui:
                QApplication.processEvents()
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.5)  # Reduced timeout for faster scanning
                    sock.connect((ip, port))
                    resource = f"TCPIP::{ip}::{port}::SOCKET"
                    logger.info(f"Found device at {ip}:{port}")
                    return resource, resource  # Don't query IDN
            except (socket.timeout, ConnectionRefusedError):
                return None
            except Exception as e:
                logger.debug(f"Error checking {ip}:{port} - {e}")
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = [
                executor.submit(scan_port, ip, port) 
                for ip in discovered_ips 
                for port in instrument_ports
            ]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    unique_id, resource = result
                    discovered_resources[unique_id] = resource

        logger.debug(f"RawSocket discovered devices before filtering: {discovered_resources}")

        # Filtering will be handled externally in Instrument.list_instruments

        return discovered_resources

    @staticmethod
    def get_all_local_ip_ranges(default: str = "192.168.1.0/24") -> List[str]:
        """
        Retrieve all local IPv4 addresses and derive their subnets.

        Args:
            default (str): Default subnet to use if no valid IPs are found

        Returns:
            List[str]: A list of IP ranges in CIDR notation
        """
        ip_ranges = []
        try:
            hostname = socket.gethostname()
            logger.debug(f"Host name: {hostname}")
            host_info = socket.gethostbyname_ex(hostname)
            # host_info[2] contains a list of IP addresses
            for ip in host_info[2]:
                try:
                    # Exclude loopback and non-private IPs
                    if ip.startswith("127.") or not RawSocketConnection.is_private_ip(ip):
                        continue
                    network = ipaddress.IPv4Network(f"{ip}/24", strict=False)
                    ip_ranges.append(str(network))
                    logger.debug(f"Derived network from IP {ip}: {network}")
                except ValueError as ve:
                    logger.warning(f"Invalid IP address '{ip}': {ve}")
        except Exception as e:
            logger.error(f"Failed to retrieve local IP addresses: {e}")
            ip_ranges.append(default)
            logger.debug(f"Using default IP range: {default}")

        return ip_ranges if ip_ranges else [default]

    @staticmethod
    def is_private_ip(ip: str) -> bool:
        """
        Check if the given IP address is within a private network range.

        Args:
            ip (str): IP address to check

        Returns:
            bool: True if private, False otherwise
        """
        private_networks = [
            ipaddress.IPv4Network('10.0.0.0/8'),
            ipaddress.IPv4Network('172.16.0.0/12'),
            ipaddress.IPv4Network('192.168.0.0/16'),
        ]
        ip_addr = ipaddress.IPv4Address(ip)
        return any(ip_addr in network for network in private_networks)
    
    @staticmethod
    def parse_datagram(datagram: bytes) -> str:
        """
        Parse PIC32 UDP response datagram.
        PIC32 devices using Microchip's TCP/IP stack typically respond with ASCII text
        containing device information and network configuration.

        Args:
            datagram (bytes): The received UDP datagram.

        Returns:
            str: The parsed device identifier or empty string if parsing fails.
        """
        try:
            # PIC32 responses are typically ASCII
            data_str = datagram.decode('ascii').strip()
            logger.debug(f"Parsing PIC32 response: {data_str}")
            
            # Extract device identifier (usually first part of response)
            device_id = data_str.split(',')[0].strip()
            return device_id

        except Exception as e:
            logger.error(f"Failed to parse PIC32 response '{datagram.hex()}': {e}")
            return ""
    
    @staticmethod
    def _discover_mdns(timeout: float) -> Dict[str, str]:
        """
        Discover instruments via mDNS.

        Args:
            timeout (float): Timeout for discovery in seconds.

        Returns:
            dict[str, str]: A dictionary mapping unique IDs to resource strings.
        """
        discovered_devices = {}
        service_type = "_instrument._tcp.local."  # Replace with your instrument's service type

        logger.debug(f"Starting mDNS discovery for service type: {service_type}")

        class InstrumentListener:
            def __init__(self):
                self.devices = {}

            def remove_service(self, zeroconf, type, name):
                logger.debug(f"Service {name} removed")

            def add_service(self, zeroconf, type, name):
                info = zeroconf.get_service_info(type, name)
                if info:
                    addr = socket.inet_ntoa(info.addresses[0])
                    port = info.port
                    properties = info.properties
                    unique_id = properties.get(b'unique_id', b'').decode('utf-8')
                    if unique_id:
                        resource = f"TCPIP::{addr}::{port}::SOCKET"
                        self.devices[unique_id] = resource
                        logger.info(f"Discovered mDNS Instrument - ID: {unique_id}, Resource: {resource}")

            def update_service(self, zeroconf, type, name):
                logger.debug(f"Service {name} updated")
                self.add_service(zeroconf, type, name)

        zeroconf = Zeroconf()
        listener = InstrumentListener()
        browser = ServiceBrowser(zeroconf, service_type, listener)

        try:
            logger.debug(f"Waiting for mDNS responses for {timeout} seconds...")
            time.sleep(timeout)
        finally:
            zeroconf.close()

        discovered_devices = listener.devices
        logger.debug(f"mDNS discovery completed. Devices found: {discovered_devices}")

        return discovered_devices

    @staticmethod
    def _discover_scan(ip_range: Optional[str] = None, ports: list = [5025, 9760, 1234], 
                      timeout: float = 3.0) -> Dict[str, str]:
        """
        Discover instruments by scanning a range of IP addresses and specific ports.

        Args:
            ip_range (str, optional): IP range in CIDR notation. If None, detect automatically.
            ports (list): List of port numbers to scan.
            timeout (float): Timeout for each connection attempt in seconds.

        Returns:
            dict[str, str]: A dictionary mapping unique IDs to resource strings.
        """
        if ip_range is None:
            ip_ranges = RawSocketConnection.get_all_local_ip_ranges()
        else:
            ip_ranges = [ip_range]

        discovered_devices = {}
        logger.debug(f"Starting network scan on IP range(s): {ip_ranges}, Ports: {ports}")

        for current_ip_range in ip_ranges:
            try:
                network = ipaddress.ip_network(current_ip_range, strict=False)
            except ValueError as e:
                logger.error(f"Invalid IP range '{current_ip_range}': {e}")
                continue

            def scan_ip(ip, port):
                if QApplication.instance() is not None:
                    QApplication.processEvents()
                    
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(timeout)
                    try:
                        sock.connect((str(ip), port))
                        resource = f"TCPIP::{ip}::{port}::SOCKET"
                        logger.info(f"Found device at {ip}:{port}")
                        return resource, resource  # Don't query IDN
                    except (socket.timeout, ConnectionRefusedError):
                        pass
                    except Exception as e:
                        logger.debug(f"Error scanning {ip}:{port} - {e}")
                return None

            # Utilize ThreadPoolExecutor for efficient scanning
            with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
                futures = [executor.submit(scan_ip, ip, port) 
                          for ip in network.hosts() 
                          for port in ports]
                
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        unique_id, resource = result
                        discovered_devices[unique_id] = resource

        logger.debug(f"Network scan completed. Devices found: {discovered_devices}")

        return discovered_devices
