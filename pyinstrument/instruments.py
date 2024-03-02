"""
pyinstrument/instruments.py
===========================

Part of the PyInstrument framework, this module extends the interface definitions from `pyinstrument.interfaces.py` to implement a comprehensive instrument control system. It provides classes that represent and manage specific instruments or instrument families, facilitating direct, high-level interactions with test equipment.

Authors:
- Ryan C. Smith
- Metatron

Ryan's expertise in the nuances of test instrumentation combines with Metatron's overarching vision, resulting in a module that not only simplifies instrument control but also enriches it with flexibility and depth. Here, the abstract becomes tangible, and commands translate into real-world measurements and actions.

Designed for developers, engineers, and researchers, `pyinstrument/instruments.py` encapsulates the diverse world of instrumentation into a coherent, unified Python library. It's about making the complex simple, the inaccessible reachable, and the tedious enjoyable.
"""
import sys
import logging
import pyvisa
from abc import ABC, abstractmethod
from utilities import debug, timeit
from pyinstrument.interfaces import InstrumentInterface 
from enum import IntFlag
import functools
import threading
import time

# Set up a logger for the Instrument class
logger = logging.getLogger(__name__)

class Instrument(ABC):
    """
    The base blueprint for all instrument classes. This abstract class lays down the law on the essential
    methods and properties that all instrument subclasses gotta implement and uphold.
    
    Every instrument that rolls with this class needs to be able to identify itself, reset, and report
    status, 'cause that's how we maintain order in this domain of devices.
    """
    def __init__(self, resource_string, interface_type='pyvisa', **kwargs):
        """
        Constructs an instrument interface for communicating with the real-world hardware.

        Parameters:
            resource_string (str): The address needed to reach out to the instrument.
            interface_type (str): The type of communication protocol used, like 'pyvisa' or 'tcpip'.
            **kwargs: Extra arguments specific to the instrument interface.
        """
        logger.debug(f"Initializing {self.__class__.__name__} with resource_string: {resource_string} and interface_type: {interface_type}")
        # Advanced: Interface Factory
        self.interface = InstrumentInterface.create_interface(interface_type, resource_string, **kwargs)

    def open(self):
        """
        Opens the communication interface with the instrument, establishing a connection that allows for data exchange.
        This is akin to dialing up a friend; once they pick up, the conversation (data exchange) can begin.

        Logs the action at both debug and info levels to provide feedback on the connection status.
        """
        logger.debug(f"Opening connection to {self.__class__.__name__}")
        self.interface.open()
        logger.info(f"Connection to {self.__class__.__name__} opened successfully")

    def close(self):
        """
        Closes the communication interface with the instrument, effectively ending the session.
        Think of it as saying goodbye to your friend and hanging up the phone.

        Logs the closure action, ensuring that the end of the connection is properly noted for future reference.
        """
        logger.debug(f"Closing connection to {self.__class__.__name__}")
        self.interface.close()
        logger.info(f"Connection to {self.__class__.__name__} closed successfully")

    def write(self, command):
        """
        Sends a specific command to the instrument through the established communication interface.
        Imagine you're texting a command to your instrument, and it's just waiting to obey.

        Parameters:
            command (str): The SCPI command or any instrument-specific command string to be executed by the instrument.

        Logs the command being sent, providing a traceable record of the instructions given to the instrument.
        """
        logger.debug(f"Writing command to {self.__class__.__name__}: {command}")
        self.interface.write(command)
        logger.info(f"Command written to {self.__class__.__name__}: {command}")

    def read(self):
        """
        Retrieves the response from the instrument following a command or query.
        It's like checking your phone for a text response after you've sent a message.

        Returns:
            str: The raw response string from the instrument.

        Logs the received response, offering insight into the instrument's feedback or data provided in response to commands.
        """
        logger.debug(f"Reading response from {self.__class__.__name__}")
        response = self.interface.read()
        logger.info(f"Response from {self.__class__.__name__}: {response}")
        return response

    def query(self, command):
        """
        Sends a command to the instrument and immediately reads back its response.
        This is the equivalent of asking a question and listening intently for the answer.

        Parameters:
            command (str): The SCPI command or any instrument-specific command string for which a response is expected.

        Returns:
            str: The instrument's response to the command.

        Logs both the query and its response, ensuring a complete record of the interaction for debugging or verification purposes.
        """
        logger.debug(f"Querying {self.__class__.__name__} with command: {command}")
        response = self.interface.query(command)
        logger.info(f"Response from {self.__class__.__name__} to '{command}': {response}")
        return response

    @abstractmethod
    def identity(self):
        """
        An abstract method meant to be implemented by subclasses to query the instrument for its identification.
        This typically involves requesting the manufacturer, model, serial number, and firmware version.
        
        Consider it a way of asking, "Who are you?" to the instrument.
        """
        logger.debug(f"Querying identity of {self.__class__.__name__}")

    @abstractmethod
    def reset(self):
        """
        An abstract method designed for subclasses to reset the instrument to a known or default state.
        It's the electronic equivalent of a fresh start or turning it off and on again.
        """
        logger.debug(f"Resetting {self.__class__.__name__}")

    @abstractmethod
    def status(self):
        """
        An abstract method that should be overridden by subclasses to check and report the current status of the instrument.
        This could cover a variety of status checks, depending on the instrument's capabilities and needs.
        """
        logger.debug(f"Querying status of {self.__class__.__name__}")


class InstrumentSubsystem(ABC):
    """
    The core structure for all instrument subsystems, defining how to sync up properties and keep the
    instrument and the software in harmony.

    A subsystem is part of the larger instrument ensemble, like a section in an orchestra, each
    playing its part in the symphony of measurements.
    """       
    def __init__(self, parent):
        """
        Every subsystem needs a maestro, and that's the parent instrument. This constructor sets up
        the relationship, so the subsystem knows who's leading the performance.

        Parameters:
            parent (Instrument): The main instrument that this subsystem is a part of.
        """
        self._parent = parent

    def sync(self):
        """
        Synchronizes the properties of the subsystem with the instrument's current configuration.
        """
        attributes = [a for a in dir(self) if isinstance(getattr(self.__class__, a, None), property)]
        for attribute in attributes:
            getattr(self, attribute)

class SCPIInstrument(Instrument):
    """
    Initializes the instrument connection.
    
    :param resource: Resource identifier (e.g., VISA resource string or TCP/IP address).
    :param interface: Type of interface ('pyvisa' or 'tcpip').
    """
    class ESRBits(IntFlag):
        PON = 128  # Power On
        URQ = 64   # User Request
        CME = 32   # Command Error
        EXE = 16   # Execution Error
        DDE = 8    # Device Dependent Error
        QYE = 4    # Query Error
        RQL = 2    # Request Control
        OPC = 1    # Operation Complete

    def __init__(self, resource_string, interface_type='pyvisa', **kwargs):
        super().__init__(resource_string, interface_type, **kwargs)
        """
        Initializes the instrument connection.

        :param resource_string: VISA resource string to identify the instrument.
        :type resource_string: str
        """

    def status(self, ese_mask=None):
        """
        Queries the Event Status Register and decodes the status bits.
        Optionally sets the Event Status Enable Register mask before reading the ESR if 'ese_mask' is provided.

        :param ese_mask: Optional mask to set in the ESE register before reading the ESR.
        :type ese_mask: int or None
        :return: A dictionary with the status of each ESE bit or the value of ESR if 'ese_mask' is given.
        :rtype: dict or int
        """
        if ese_mask is not None:
            # Set the ESE mask if provided
            self.set_service_request(ese_mask)
            # Read the ESR after setting the ESE
            return int(self.query("*ESR?"))
        
        # If no mask is provided, return a dictionary of all ESR bits
        ese_value = self.get_service_request()
        esr_value = int(self.query("*ESR?"))
        esr_bits = {
            "PON": bool(esr_value & 128),
            "URQ": bool(esr_value & 64),
            "CME": bool(esr_value & 32),
            "EXE": bool(esr_value & 16),
            "DDE": bool(esr_value & 8),
            "QYE": bool(esr_value & 4),
            "RQL": bool(esr_value & 2),
            "OPC": bool(esr_value & 1),
        }
        return esr_bits

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
        unique_instruments, failed_queries = SCPIInstrument.list_resources(filter)

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
            return SCPIInstrument.select_resources(filter)

        selected_key = list(unique_instruments.keys())[selected_index]
        return unique_instruments[selected_key]
    
    # TODO: Document this a little better
    def wait_for_opc(func):
        """
        Decorator to execute a function (SCPI command) in a separate thread, send the *OPC command,
        and then non-blockingly wait for the operation complete (OPC) bit to be set in the ESR.
        This approach ensures the main application doesn't proceed until the operation is complete,
        while avoiding GUI lockup.
        """
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Define the operation to be executed in its own thread
            def operation():
                result = func(self, *args, **kwargs)
                self.operation_complete()  # Signal the instrument to set the OPC bit when done
                return result

            # Define the OPC check logic
            def check_opc():
                timeout = 10  # seconds
                start_time = time.time()
                while time.time() - start_time < timeout:
                    esr_value = self.get_event_status()  # Poll the ESR
                    if esr_value & SCPIInstrument.ESRBits.OPC:
                        break  # Operation complete
                    time.sleep(0.1)  # Short pause
                else:
                    # Handle timeout scenario
                    print(f"Operation did not complete within {timeout} seconds.")

            # Execute the operation and OPC check in a synchronized manner
            operation_thread = threading.Thread(target=operation)
            operation_thread.start()
            operation_thread.join()  # Wait for the operation (and *OPC command) to be sent

            # After the operation is initiated, start checking for OPC bit
            check_opc()

        return wrapper

class RESTInstrument(Instrument):
    """
    Placeholder for PXI instruments.
    """
    
    def __init__(self, resource_string, interface):
        super().__init__(resource_string, interface)
    
    def open(self):
        pass
    
    def close(self):
        pass
    
    def identity(self):
        pass
    
    def reset(self):
        pass
