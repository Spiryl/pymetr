"""
pymetr/instruments.py
===========================

Part of the pymetr framework, this module extends the interface definitions from `pymetr.interfaces.py` to implement a comprehensive instrument control system. It provides classes that represent and manage specific instruments or instrument families, facilitating direct, high-level interactions with test equipment.

Authors:
- Ryan C. Smith

Designed for developers, engineers, and researchers, `pymetr/instruments.py` encapsulates the diverse world of instrumentation into a coherent, unified Python library. It's about making the complex simple, the inaccessible reachable, and the tedious enjoyable.
"""
import sys
import logging
import pyvisa
from enum import IntFlag

# Set up a logger for the Instrument class
logger = logging.getLogger(__name__)

class Instrument:
    """
    A comprehensive class for interacting with scientific and industrial instruments through VISA, 
    specifically tailored for devices that support the Standard Commands for Programmable Instruments (SCPI) protocol. 
    It simplifies the process of establishing connections, sending commands, reading responses, and managing instrument 
    status, whether communicating in ASCII or binary format.

    This class is designed to serve as the foundation for specialized instrument control by providing common SCPI 
    command support and direct VISA communication capabilities.
    """

    def __init__(self, resource_string, **kwargs):
        """
        Initializes the instrument connection using the provided VISA resource string.
        
        Parameters:
            resource_string (str): VISA resource string to identify the instrument.
            **kwargs: Additional keyword arguments for PyVISA's open_resource method.
        """
        self.resource_string = resource_string
        self.rm = pyvisa.ResourceManager()
        self.instrument = None
        logger.debug(f"Initializing Instrument with resource_string: {resource_string}")

    def open(self):
        """Opens a connection to the instrument."""
        self.instrument = self.rm.open_resource(self.resource_string)
        logger.info(f"Connection to instrument {self.resource_string} opened successfully.")

    def close(self):
        """Closes the connection to the instrument."""
        if self.instrument:
            self.instrument.close()
            logger.info("Instrument connection closed.")
            self.instrument = None

    def write(self, command):
        """
        Sends a command to the instrument.
        
        Parameters:
            command (str): The SCPI command to be executed by the instrument.
        """
        self.instrument.write(command)
        logger.debug(f"Command sent: {command}")

    def read(self):
        """
        Reads the response from the instrument.
        
        Returns:
            str: The raw response from the instrument.
        """
        response = self.instrument.read()
        logger.debug(f"Response received: {response}")
        return response

    def query(self, command):
        """
        Sends a command to the instrument and reads its response.
        
        Parameters:
            command (str): The SCPI command for which a response is expected.
        
        Returns:
            str: The instrument's response to the command.
        """
        self.write(command)
        response = self.read()
        logger.debug(f"Query sent: {command}, received: {response}")
        return response

    def query_binary(self, command, datatype='f', is_big_endian=False, container=list):
        """
        Sends a command to the instrument and reads a binary response.
        
        Parameters:
            command (str): The SCPI command for which a binary response is expected.
            datatype (str): The type of data to expect ('b', 'h', 'i', 'f', etc.).
            is_big_endian (bool): True for big endian data, False for little endian.
            container (type): The type of container to store the binary data.
        
        Returns:
            container: The binary data read from the instrument.
        """
        endian = '>' if is_big_endian else '<'
        response = self.instrument.query_binary_values(command, datatype=endian + datatype, container=container)
        logger.debug(f"Binary query sent: {command}, received: {response}")
        return response

    def status(self):
        """
        Queries the Event Status Register (ESR) to decode and return the current instrument status.
        
        Returns:
            dict: A dictionary representing the status of various ESR bits.
        """
        esr_value = int(self.query("*ESR?"))
        status = {bit.name: bool(esr_value & bit.value) for bit in Instrument.Status}
        logger.debug(f"Instrument status: {status}")
        return status
    
    def identity(self):
        """
        Sends a request to the instrument to identify itself. This usually includes the manufacturer, 
        model number, serial number, and firmware version. It's like asking, "Who are you?"

        Returns:
            str: The identification string returned by the instrument.
        """
        return self.query("*IDN?")
        
    def clear_status(self):
        """
        Resets the instrument's status and error queue to clear out any errors and get it back to its 
        startup condition. Think of it as the instrument taking a deep breath and starting fresh.
        """
        self.write("*CLS")

    def reset(self):
        """
        Resets the instrument to its factory default settings. It's the control-alt-delete for when you 
        want to wipe the slate clean and start over.
        """
        self.write("*RST")

    def set_service_request(self, mask):
        """
        Configures the instrument to enable certain status events to generate service requests (SRQ). 
        It's like setting up push notifications for the events you actually care about.

        Parameters:
            mask (int): A bit mask that defines which status events will trigger an SRQ.
        """
        self.write(f"*ESE {mask}")

    def get_service_request(self):
        """
        Retrieves the current settings of the Service Request Enable (SRE) register, which determines 
        what events will trigger a service request.

        Returns:
            int: The bit mask of the SRE register's current settings.
        """
        return int(self.query("*ESE?"))

    def get_event_status(self):
        """
        Polls the Event Status Register (ESR) of the instrument to check for any status events that 
        have occurred. It's like checking your notifications to see what's happened.

        Returns:
            int: The bit mask of the ESR, indicating which events have occurred.
        """
        return int(self.query("*ESR?"))

    def operation_complete(self):
        """
        Instructs the instrument to set the Operation Complete (OPC) bit in the Event Status Register 
        once all pending operations have finished. It's a way to tell the instrument, "Hit me up when 
        you're done with what you're doing."
        """
        self.write("*OPC")

    def query_operation_complete(self):
        """
        Asks the instrument if it has finished processing all pending operations. This method queries the 
        Operation Complete (OPC) bit and is useful for synchronization in automated test sequences.

        Returns:
            str: '1' when the instrument has completed all pending operations.
        """
        return self.query("*OPC?")

    def save_setup(self, value):
        """
        Saves the current configuration of the instrument to a specified memory location. It's like 
        taking a snapshot of your current setup so you can return to it later.

        Parameters:
            value (int): The memory location where the instrument's state will be saved.
        """
        self.write(f"*SAV {value}")
    
    @staticmethod
    def list_resources(query='?*::INSTR'):
        """
        Lists all the connected instruments matching the query filter.

        Parameters:
            query (str): Filter pattern using VISA Resource Regular Expression syntax.

        Returns:
            tuple: A tuple containing a dict of unique instruments keyed by their IDN response,
                and a list of resources that failed to query.
        """
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources(query)
        unique_instruments = {}
        failed_queries = []

        for resource in resources:
            try:
                with rm.open_resource(resource) as inst:
                    idn = inst.query("*IDN?").strip()
                    unique_key = f"{resource}: {idn}"
                    unique_instruments[unique_key] = resource
            except pyvisa.VisaIOError as e:
                failed_queries.append((resource, str(e)))

        return unique_instruments, failed_queries
    
    @staticmethod
    def select_resources(filter='?*::INSTR'):
        """
        Presents a list of connected instruments filtered by the query and prompts the user to select one.

        Parameters:
            filter (str): Filter pattern to identify the instruments.

        Returns:
            str: The selected resource string of the instrument.
        """
        unique_instruments, failed_queries = Instrument.list_resources(filter)

        if not unique_instruments:
            print("No instruments found. Check your connections and try again.")
            sys.exit(1)

        print("\nConnected Instruments:")
        for idx, (unique_key, resource) in enumerate(unique_instruments.items(), start=1):
            print(f"{idx}. {unique_key}")

        if failed_queries:
            print("\nFailed to query some instruments:")
            for resource, error in failed_queries:
                print(f"{resource}: {error}")

        selection = input("\nSelect an instrument by number (or 'exit' to quit): ")
        if selection.lower() == 'exit':
            sys.exit(0)

        try:
            selected_index = int(selection) - 1
            if selected_index < 0 or selected_index >= len(unique_instruments):
                raise ValueError
        except ValueError:
            print("Invalid selection. Please enter a number from the list.")
            return Instrument.select_resources(filter)

        selected_key = list(unique_instruments.keys())[selected_index]
        return unique_instruments[selected_key]

    class Status(IntFlag):
        """
        Event Status Register Bits for SCPI Instruments.

        Each bit in the status register represents a specific status or error condition.
        These are defined according to the IEEE 488.2 standard for SCPI instruments.
        """

        OPC = 1 << 0  # Operation Complete
        """Operation complete bit, set when an operation is finished."""

        RQL = 1 << 1  # Request Control
        """Request control bit, indicates a device is requesting control."""

        QYE = 1 << 2  # Query Error
        """Query error bit, set when there is a syntax error in a query command."""

        DDE = 1 << 3  # Device Dependent Error
        """Device dependent error bit, indicates an error specific to the device's operation."""

        EXE = 1 << 4  # Execution Error
        """Execution error bit, set when there is an error in executing a command."""

        CME = 1 << 5  # Command Error
        """Command error bit, set when there is a syntax error in a command."""

        URQ = 1 << 6  # User Request
        """User request bit, set when there is a user request for service."""

        PON = 1 << 7  # Power On
        """Power on bit, set when the device is first powered on or reset."""