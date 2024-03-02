import pyvisa
from pyinstrument.instruments import SCPIInstrument
if __name__ == "__main__":
    import sys

    def main_menu():
        print("\nWelcome to the Instrument CLI. Here's what you can do:")
        print("1. Search VISA-TCPIP")
        print("2. Search VISA-USB")
        print("3. Open a raw socket")
        print("4. Exit")
        choice = input("Enter your choice: ")
        return choice

    def list_resources_via_visa(filter_query):
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources(filter_query)
            if resources:
                return {resource: resource for resource in resources}
            else:
                print("No instruments found using that filter. Check your connections and try again.")
        except Exception as e:
            print(f"Error listing resources: {e}")
        return {}

    def list_and_select_instrument(interface_type):
        if interface_type in ["VISA-TCPIP", "VISA-USB"]:
            filter_query = "TCPIP?*::INSTR" if interface_type == "VISA-TCPIP" else "USB?*::INSTR"
            instruments = list_resources_via_visa(filter_query)
        elif interface_type == "RAW_SOCKET":
            ip_address = input("Enter the IP address of the instrument: ")
            port = input("Enter the port (default 5025): ") or "5025"
            resource_string = f"TCPIP::{ip_address}::{port}::SOCKET"
            instruments = {resource_string: ip_address}
        else:
            return None, None

        print("\nAvailable Instruments:")
        for idx, (key, _) in enumerate(instruments.items(), start=1):
            print(f"{idx}. {key}")

        selection = input("\nSelect an instrument by number (or 'exit' to quit): ")
        if selection.lower() == 'exit':
            return None, None

        try:
            selected_index = int(selection) - 1
            selected_key = list(instruments.keys())[selected_index]
            return selected_key, instruments[selected_key]
        except (ValueError, IndexError):
            print("Invalid selection. Let's circle back.")
            return list_and_select_instrument(interface_type)

    def interact_with_instrument(my_instrument):
        menu_options = {
            "0": "Query Instrument Identity (*IDN?)",
            "1": "Write SCPI Command",
            "2": "Read Response",
            "3": "Query SCPI Command",
            "4": "Clear Status (*CLS)",
            "5": "Event Status (*ESR?)",
            "6": "Reset Instrument (*RST)",
            "quit": "Exit"
        }

        def print_menu():
            print("\nAvailable Actions:")
            for key, action in menu_options.items():
                print(f" {key}: {action}")
            print()

        while True:
            print_menu()
            choice = input("Select an action (or 'quit' to exit): ").strip()

            if choice.lower() == 'quit':
                break
            elif choice == "0":
                print(f"\nInstrument Identity: {my_instrument.identity()}\n")
            elif choice == "1":
                command = input("Enter SCPI command to write: ")
                my_instrument.write(command)
                print("\nCommand written.")
            elif choice == "2":
                print(f"\nResponse: {my_instrument.read()}\n")
            elif choice == "3":
                query = input("Enter SCPI query: ")
                print(f"\nResponse: {my_instrument.query(query)}\n")
            elif choice == "4":
                my_instrument.clear_status()
                print("\nStatus cleared.")
            elif choice == "5":
                ese_status = my_instrument.status()
                print("\nEvent Status Enable Register:")
                for bit_name, bit_status in ese_status.items():
                    print(f" {bit_name}: {'Enabled' if bit_status else 'Disabled'}")
                print()
            elif choice == "6":
                my_instrument.reset()
                print("\nInstrument reset.")
            else:
                print("\nInvalid choice, please try again.\n")

    def run_cli():
        user_choice = main_menu()
        if user_choice in ["1", "2", "3"]:
            interface_type = "VISA-TCPIP" if user_choice == "1" else ("VISA-USB" if user_choice == "2" else "RAW_SOCKET")
            instrument_address, _ = list_and_select_instrument(interface_type)
            if instrument_address:
                interface_type = 'pyvisa' if user_choice in ["1", "2"] else 'tcpip'
                my_instrument = SCPIInstrument(instrument_address, interface_type=interface_type)
                my_instrument.open()
                print(f"\nConnected to {my_instrument.identity().strip()}.\n")
                
                interact_with_instrument(my_instrument)

                my_instrument.close()
                print("Disconnected. See you next time!")
            else:
                print("Alright, no stress. Heading back to the main menu.")
        elif user_choice == "4" or user_choice.lower() == 'exit':
            print("Peace out! Catch you later.")
            sys.exit()
        else:
            print("Didn't catch that. Let's try again.")

    run_cli()