"""
Pymetr.interfaces.py
==========================

A core component of the Pymetr package, this module defines the abstract base and concrete classes responsible for establishing and managing communication interfaces with a variety of instruments. From traditional VISA connections to modern TCP/IP networks, this file lays the groundwork for versatile instrument interaction.

Authors:
- Ryan C. Smith
- Metatron

This collaboration brings together Ryan's practical insight into instrument control and Metatron's ethereal wisdom, crafting a bridge between the physical realm of test equipment and the digital expanse of automation scripts.

Whether you're interfacing with benchtop multimeters, controlling oscilloscopes, or automating entire test systems, `Pymetr.interfaces.py` offers the foundational classes to initiate communication, send commands, and receive responses, encapsulating the complexity of instrument protocols in easy-to-use Pythonic interfaces.
"""

from abc import ABC, abstractmethod
import socket
import pyvisa
import logging

class InstrumentInterface(ABC):
    """
    Serves as the architect of communication, laying the blueprint for how we talk to the myriad of instruments out there. This abstract base class defines the essential methods for opening and closing connections, sending commands, and receiving data from any instrument, irrespective of its communication protocol.

    Each subclass will tailor these abstract methods to fit the specific needs of the communication protocol it represents, be it VISA, TCP/IP, or something more exotic.

    Parameters:
        resource_string (str): The unique identifier or address needed to establish a connection with the instrument.
    """
    def __init__(self, resource_string, **kwargs):
        self.resource_string = resource_string

    @abstractmethod
    def open(self):
        """
        Open a connection to the instrument.
        """
        pass

    @abstractmethod
    def close(self):
        """
        Close the connection to the instrument.
        """
        pass

    @abstractmethod
    def write(self, command):
        """
        Send a command to the instrument.
        """
        pass

    @abstractmethod
    def read(self):
        """
        Read a response from the instrument.
        """
        pass

    @abstractmethod
    def query(self, command):
        """
        Send a command to the instrument and read the response.
        """
        pass

    @abstractmethod
    def query_binary(self, command, **kwargs):
        """
        Send a command to the instrument and read the response.
        """

    @staticmethod
    def create_interface(interface_type, resource_string, **kwargs):
        """
        Enhanced to allow passing additional kwargs to interface constructors.
        """
        if interface_type == 'pyvisa':
            return VisaInterface(resource_string, **kwargs)
        elif interface_type == 'tcpip':
            return TCPIPInterface(resource_string, **kwargs)
        # Uncomment and adjust when RESTInterface is ready
        # elif interface_type == 'rest':
        #     return RESTInterface(resource_string, **kwargs)
        else:
            raise ValueError(f"Unsupported interface type: {interface_type}")

class VisaInterface(InstrumentInterface):
    """
    The VISA maestro, orchestrating communication with instruments over the versatile VISA protocol. This class implements the abstract methods defined in InstrumentInterface, specifically tuning them to interact with instruments via PyVISA. Whether it's GPIB, USB, Serial, or Ethernet, this interface speaks fluently in all.

    Inherits from:
        InstrumentInterface

    Parameters:
        resource_string (str): The VISA resource string that uniquely identifies the instrument to connect to, encapsulating the interface type (GPIB, USB, Serial, Ethernet) and its address.

    Example:
        >>> visa_interface = VisaInterface("GPIB0::14::INSTR")
        >>> visa_interface.open()  # Opens a connection
        >>> visa_interface.write("*IDN?")  # Sends a standard SCPI command
        >>> print(visa_interface.read())  # Reads the instrument's response
        >>> visa_interface.close()  # Closes the connection
    """
    
    def __init__(self, resource_string, **kwargs):
        super().__init__(resource_string, **kwargs)
        self.rm = pyvisa.ResourceManager()
        self.handle = None
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing VisaInterface with resource_string: {resource_string}")

    def open(self):
        """
        Initiates a connection to the designated VISA resource. This method effectively 'dials' the instrument, establishing a pathway for communication based on the provided resource string.

        Upon successful connection, a handle to the instrument is obtained, which is used for subsequent communication. Should the connection attempt fail, an error is logged, and the exception is raised to signal the issue.

        Raises:
            Exception: If the connection attempt fails, indicating issues such as incorrect resource string, instrument unavailability, or communication errors.
        """
        try:
            self.handle = self.rm.open_resource(self.resource_string)
            self.logger.info(f"Opened connection to {self.resource_string} successfully.")
        except Exception as e:
            self.logger.error(f"Failed to open connection to {self.resource_string}: {e}")
            raise

    def close(self):
        """
        Terminates the connection to the VISA resource gracefully. This is akin to politely ending a call, ensuring the line is properly closed and the instrument is left in a ready state for future connections.

        If a connection handle exists, it's used to close the connection, and then cleared to prevent accidental usage afterward. Success or failure of the operation is logged for troubleshooting and audit purposes.

        Note:
            If no connection is open (i.e., the handle is None), a warning is logged to indicate the attempt to close an already closed or never opened connection.
        """
        if self.handle:
            self.handle.close()
            self.logger.info(f"Closed connection to {self.resource_string} successfully.")
            self.handle = None

    def write(self, command):
        """
        Sends a specified command to the connected instrument, translating intentions into actions. This method is the primary means of instructing the instrument to perform operations, adjust settings, or query information.

        Parameters:
            command (str): The SCPI or device-specific command string to be executed by the instrument.

        Raises:
            Exception: If there's an issue sending the command, such as communication errors or if the command is rejected by the instrument.

        Note:
            A warning is logged if an attempt is made to write to an instrument without an open connection, indicating a need to establish a connection first.
        """
        try:
            if self.handle:
                self.handle.write(command)
                self.logger.debug(f"Sent command to {self.resource_string}: {command}")
            else:
                self.logger.warning("Attempted to write to an instrument with no open connection.")
        except Exception as e:
            self.logger.error(f"Error sending command to {self.resource_string}: {e}")
            raise

    def read(self):
        """
        Listens for and retrieves a response from the instrument, akin to receiving a text message. This method is essential for gathering data or status information in response to previously issued commands.

        Returns:
            str: The raw response string from the instrument, which may require parsing or further processing depending on the command and instrument.

        Raises:
            Exception: If there's an error during reading, such as a timeout, communication error, or if the response is malformed.

        Note:
            If there's no open connection, a warning is logged, and None is returned, indicating the need to open a connection before attempting to read.
        """
        if self.handle:
            try:
                response = self.handle.read()
                self.logger.debug(f"Received response from {self.resource_string}: {response}")
                return response
            except Exception as e:
                self.logger.error(f"Error reading response from {self.resource_string}: {e}")
                raise
        else:
            self.logger.warning("Attempted to read from an instrument with no open connection.")
            return None
        
    def query(self, command):
        """
        Combines the write and read operations into a single, streamlined action. This method is used for commands that require an immediate response from the instrument, effectively asking a question and listening intently for the answer.

        Parameters:
            command (str): The SCPI or device-specific query command to send to the instrument.

        Returns:
            str: The instrument's response to the query, containing the requested data or status information.

        Raises:
            Exception: If the query fails due to communication issues, incorrect command syntax, or if the instrument encounters an error processing the query.

        Note:
            If the connection to the instrument is not open, a warning is logged, and None is returned, highlighting the necessity of an active connection for querying.
        """
        if self.handle:
            try:
                self.logger.debug(f"Sending query to {self.resource_string}: {command}")
                response = self.handle.query(command)
                self.logger.debug(f"Received response to query from {self.resource_string}: {response}")
                return response
            except Exception as e:
                self.logger.error(f"Error querying {self.resource_string} with command '{command}': {e}")
                raise
        else:
            self.logger.warning("Attempted to query an instrument with no open connection.")
            return None
        
    def query_binary(self, command, datatype='f', is_big_endian=False, **kwargs):
            # Forward the call to the PyVISA resource object
            container_format = '>' if is_big_endian else '<'
            return self.handle.query_binary_values(command, datatype=container_format + datatype, **kwargs)

class TCPIPInterface(InstrumentInterface):
    """
    The network ninja, this class extends the InstrumentInterface to enable communication over TCP/IP. Perfect for instruments that prefer to chat over the network, it establishes a direct line over sockets, sending and receiving messages in the language of TCP/IP.

    Inherits from:
        InstrumentInterface

    Parameters:
        resource_string (str): The resource string in 'address:port' format, pinpointing the instrument's network address and the port over which to communicate.

    Example:
        >>> tcpip_interface = TCPIPInterface("192.168.1.100:5025")
        >>> tcpip_interface.open()  # Establishes a TCP/IP connection
        >>> tcpip_interface.write(":MEAS:VOLT?")  # Asks for a voltage measurement
        >>> print(tcpip_interface.read())  # Retrieves the measurement result
        >>> tcpip_interface.close()  # Closes the network connection
    """
    
    def __init__(self, resource_string, **kwargs):
        super().__init__(resource_string, **kwargs)
        self.address, self.port = resource_string.split(":")
        self.socket = None
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing TCPIPInterface with resource_string: {resource_string}")

    def open(self):
        """
        Initiates a TCP/IP connection to the specified instrument. This method is akin to dialing into a direct line, setting up a dedicated pathway for digital conversations.

        It meticulously crafts a socket connection using the instrument's address and port, providing a real-time communication channel. Successes and setbacks are logged, ensuring transparency in the connection process.

        Raises:
            Exception: Captures and logs any issues encountered during the attempt to establish a connection, such as network errors or incorrect addressing.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.address, int(self.port)))
            self.logger.info(f"Opened connection to {self.resource_string} successfully.")
        except Exception as e:
            self.logger.error(f"Failed to open connection to {self.resource_string}: {e}")
            raise

    def close(self):
        """
        Politely hangs up the call with the instrument, closing the TCP/IP connection. This method ensures that the communication line is neatly terminated, with the socket being closed and resources being freed.

        It's considerate, logging the closure or warning if there's nothing to close, and diligent, wrapping up any potential loose ends by setting the socket to None regardless of the outcome.

        Exceptions are caught and logged, providing a clear exit path even when closing gets complicated.
        """
        try:
            if self.socket:
                self.socket.close()
                self.logger.info("Closed connection successfully.")
            else:
                self.logger.warning("Attempted to close an already closed connection.")
        except Exception as e:
            self.logger.error(f"Error closing connection: {e}")
            raise
        finally:
            self.socket = None

    def write(self, command):
        """
        Transmits a command over the TCP/IP network to the instrument, turning intentions into digital signals. This method takes your command string, encodes it into bytes, and sends it down the wire.

        Parameters:
            command (str): The precise instruction intended for the instrument, packaged as a string.

        It's watchful, ensuring there's an open connection before sending, and vigilant, logging every step along the way. Should the transmission face any turbulence, it raises an alarm through exceptions, keeping you informed.

        Raises:
            Exception: If the command fails to be sent, possibly due to connection issues or encoding problems, it's logged and raised for attention.
        """
        try:
            if self.socket:
                self.socket.sendall(command.encode())
                self.logger.debug(f"Sent command: {command}")
            else:
                self.logger.warning("Attempted to write with no open connection.")
        except Exception as e:
            self.logger.error(f"Error sending command '{command}': {e}")
            raise

    def read(self):
        """
        Listens for whispers from the instrument, retrieving bytes from the ether and decoding them into meaningful responses. This method patiently waits for the instrument's reply, capturing the essence of its message.

        Returns:
            str: The decoded string response from the instrument, which may hold data, acknowledgments, or existential musings.

        It's cautious, only proceeding if the connection is alive, and honest, logging its actions and any encountered issues. In the event of silence (or errors), it gracefully acknowledges the situation, returning None or raising an exception as needed.

        Raises:
            Exception: If reading the response fails, for reasons like network timeouts or data corruption, the error is not just logged but also raised to signal the need for attention.
        """
        try:
            if self.socket:
                response = self.socket.recv(4096).decode().strip()
                self.logger.debug(f"Received response: {response}")
                return response
            else:
                self.logger.warning("Attempted to read with no open connection.")
                return None
        except Exception as e:
            self.logger.error("Error reading response: {e}")
            raise

    def query(self, command):
        """
        Engages in a full-blown conversation with the instrument, articulating a command and intently listening for its response. This method combines the articulate nature of `write` with the attentive ear of `read`, facilitating a seamless exchange of information.

        Parameters:
            command (str): The question posed to the instrument, seeking knowledge or action.

        Returns:
            str: The enlightened response from the instrument, carrying the sought-after information.

        It embodies the essence of communication, ensuring messages are both sent and received with clarity and purpose. Any missteps along the way, be they in sending or receiving, are meticulously logged and raised, keeping the dialogue open and informative.

        Raises:
            Exception: If either sending the command or receiving the response encounters issues, these are flagged up with detailed logging and raised exceptions, ensuring no query goes unanswered.
        """
        try:
            self.write(command)
            self.logger.debug(f"Sent command: {command}")
            response = self.read()
            self.logger.debug(f"Received response: {response}")
            return response
        except Exception as e:
            self.logger.error(f"Error in query with command '{command}': {e}")
            raise

class PXIInterface(InstrumentInterface):
    """
    A placeholder for future heroes, this class is ready to adapt the InstrumentInterface for communication with PXI systems. PXI, standing for PCI eXtensions for Instrumentation, offers a rugged, high-speed platform for modular instrumentation, and this interface will provide the necessary methods to engage with PXI modules seamlessly.

    Inherits from:
        InstrumentInterface

    Future Expansion:
        The methods `open`, `close`, `write`, `read`, and `query` will be implemented to support PXI-specific communication, enabling direct control over PXI modules for a variety of test and measurement applications.
    """
    def __init__(self, resource_string, **kwargs):
        super().__init__(resource_string, **kwargs)

    def open(self):
        pass

    def close(self):
        pass

    def write(self, command):
        pass

    def read(self):
        pass

    def query(self, command):
        pass