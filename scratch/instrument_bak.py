# pyinstrument/instrument.py
import pyvisa
from abc import ABC, abstractmethod
from utilities import debug, timeit


class InstrumentSubsystem(ABC):
    """
    Abstract base class for creating instrument subsystems.

    This class provides the basic structure for defining properties and synchronization
    behavior for instrument subsystems.

    :param parent: The parent instrument to which the subsystem belongs.
    :type parent: Instrument
    """
    
    def __init__(self, parent):
        self._parent = parent

    def sync(self):
        """
        Synchronizes the properties of the subsystem with the instrument's current configuration.
        """
        attributes = [a for a in dir(self) if isinstance(getattr(self.__class__, a, None), property)]
        for attribute in attributes:
            getattr(self, attribute)

class Instrument:
    """
    Initializes the instrument connection.
    
    :param resource: Resource identifier (e.g., VISA resource string or TCP/IP address).
    :param interface: Type of interface ('pyvisa' or 'tcpip').
    """
    def __init__(self, resource_string, interface='pyvisa'):
        """
        Initializes the instrument connection.

        :param resource_string: VISA resource string to identify the instrument.
        :type resource_string: str
        """
        self.resource_string = resource_string
        self.rm = pyvisa.ResourceManager()
        self.handle = None

    def open(self):
        """
        Kicks off the connection to the instrument.
        """
        self.handle = self.rm.open_resource(self.resource_string)

    def close(self):
        """
        Cuts off the connection to the instrument, no strings attached.
        """
        if self.handle:
            self.handle.close()

    @debug
    def write(self, command):
        """
        Sends a command down the line to the instrument.

        :param command: SCPI command string to control the instrument.
        :type command: str
        """
        self.handle.write(command)

    def read(self):
        """
        Catches the response from the instrument, no miss.

        :return: The response from the instrument.
        :rtype: str
        """
        return self.handle.read()

    @debug
    def query(self, query):
        """
        Throws a query and catches the response in one smooth move.

        :param query: SCPI query string for the instrument.
        :type query: str
        :return: The instrument's response to the query.
        :rtype: str
        """
        return self.handle.query(query)

    def clear_status(self):
        """
        Clears the status of the instrument to its power-on state.
        """
        self.write("*CLS")

    def set_service_request(self, mask):
        """
        Sets the service request enable register (mask).

        :param mask: Bit mask of the service request enable register.
        :type mask: int
        """
        self.write(f"*ESE {mask}")

    def get_service_request(self):
        """
        Queries the service request enable register status.

        :return: The current value of the service request enable register.
        :rtype: int
        """
        return int(self.query("*ESE?"))
    
    def status(self):
        """
        Queries the Event Status Enable register and decodes the status bits.

        :return: A dictionary with the status of each ESE bit.
        :rtype: dict
        """
        ese_value = self.get_service_request()
        ese_bits = {
            "PON": bool(ese_value & 128),
            "URQ": bool(ese_value & 64),
            "CME": bool(ese_value & 32),
            "EXE": bool(ese_value & 16),
            "DDE": bool(ese_value & 8),
            "QYE": bool(ese_value & 4),
            "RQL": bool(ese_value & 2),
            "OPC": bool(ese_value & 1),
        }
        return ese_bits

    def get_event_status(self):
        """
        Queries the event status register.

        :return: The current value of the event status register.
        :rtype: int
        """
        return int(self.query("*ESR?"))

    def identity(self):
        """
        Queries the instrument for its identification.

        :return: The identification string returned by the instrument.
        :rtype: str
        """
        return self.query("*IDN?")

    def operation_complete(self):
        """
        Queries the Operation Complete bit.

        :return: '1' when all pending operations are complete.
        :rtype: str
        """
        self.write("*OPC")

    def query_operation_complete(self):
        """
        Queries the Operation Complete bit.
        
        Returns:
            str: '1' when all pending operations are complete.
        """
        return self.query("*OPC?")

    def reset(self):
        """
        Resets the instrument to a known state.
        """
        self.write("*RST")

    def save_setup(self, value):
        """
        Saves the current state of the instrument to the specified memory location.

        :param value: Memory location to save the instrument state.
        :type value: int
        """
        self.write(f"*SAV {value}")

    # More methods could be added here for *RCL, etc.

    @staticmethod
    def list_resources(query='?*::INSTR'):
        """
        Lists all the connected instruments that match the vibe, filtered by the query.

        :param query: Filter pattern using VISA Resource Regular Expression syntax.
        :type query: str
        :return: A tuple of unique instruments based on their IDN? response, and a list of failed queries.
        :rtype: tuple
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

# Some fancy jazz here so this script is useful by run alone
if __name__ == "__main__":
    import sys
    
    def main_menu():
        print("\nWelcome to the Instrument CLI. Here's what you can do:")
        print("1. List available instruments")
        print("2. Exit")
        choice = input("Enter your choice: ")
        return choice

    def list_and_select_instrument():
        print("\nWhich type of interface are we looking for today?")
        print("1. Ethernet (TCPIP)")
        print("2. USB")
        interface_choice = input("Pick an interface (number): ")

        # Mapping user choice to VISA resource filter
        interface_filters = {
            "1": "TCPIP?*::INSTR",
            "2": "USB?*::INSTR",
        }

        if interface_choice not in interface_filters:
            print("That's not a valid choice, kemosabe. Let's try again.")
            return list_and_select_instrument()

        filter_query = interface_filters[interface_choice]
        instruments, failed = Instrument.list_resources(query=filter_query)

        if not instruments:
            print("No instruments found on that interface. Check your connections and try again.")
            return None

        print("\nAvailable Instruments:")
        for idx, key in enumerate(instruments, start=1):
            print(f"{idx}. {key}")

        if failed:
            print("\nHad some issues talking to these hot kittens:")
            for fail in failed:
                print(f"{fail[0]}: {fail[1]}")

        selection = input("\nSelect an instrument by number (or 'exit' to quit): ")
        if selection.lower() == 'exit':
            return None

        try:
            selected_index = int(selection) - 1
            selected_key = list(instruments.keys())[selected_index]
            return instruments[selected_key]
        except (ValueError, IndexError):
            print("Invalid selection. Let's circle back.")
            return list_and_select_instrument()

    def run_cli(instrument_address):
        my_instrument = Instrument(instrument_address)
        my_instrument.open()
        print(f"\nConnected to {my_instrument.identity().strip()}.\n")

        menu_options = {
            "0": "Query Instrument Identity (*IDN?)",
            "1": "Write SCPI Command",
            "2": "Read Response",
            "3": "Query SCPI Command",
            "4": "Get Event Status (*ESR?)",
            "5": "Clear Status (*CLS)",
            "6": "Event Status (*ESE?)"
        }

        def print_menu():
            print("Select an action for: -> ", instrument_address, "\n")
            for key in menu_options:
                print(f" {key} = {menu_options[key]}")
            print(" 'quit' to exit.\n")

        while True:
            print_menu()
            choice = input("\nYour choice: ").strip()

            if choice.lower() == 'quit':
                break
            elif choice == "0":
                print(f"\n\n\nInstrument Identity: {my_instrument.identity()}")
            elif choice == "1":
                command = input("Enter SCPI command to write: ")
                my_instrument.write(command)
                print("\n\n\nCommand written.\n  >>", command, "\n")
            elif choice == "2":
                print("\n\n\nResponse:", my_instrument.read())
            elif choice == "3":
                query = input("Enter SCPI query: ")
                print("\n\n\nResponse:", my_instrument.query(query))
            elif choice == "4":
                print("\n\n\nEvent Status Register:", my_instrument.get_event_status())
            elif choice == "5":
                my_instrument.clear_status()
                print("\n\n\nStatus cleared.")
            elif choice == "6":
                print("\n\n\n")
                ese_status = my_instrument.status()
                for bit_name, bit_status in ese_status.items():
                    print(f"{bit_name}: {'Enabled' if bit_status else 'Disabled'}")
                print("\n")
            else:
                print("Invalid choice. Please try again.")

        my_instrument.close()
        print("Disconnected. See you next time!")

    # Keep it lit
    while True:
        user_choice = main_menu()
        if user_choice == "1":
            instrument_address = list_and_select_instrument()
            if instrument_address:
                run_cli(instrument_address)
            else:
                print("Alright, no stress. Heading back to the main menu.")
        elif user_choice == "2" or user_choice.lower() == 'exit':
            print("Peace out! Catch you later.")
            sys.exit()
        else:
            print("Didn't catch that. Let's try again.")