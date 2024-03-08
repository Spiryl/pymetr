import numpy as np
import sys
from pymetr.oscilloscope.core import Oscilloscope
from pymetr.instrument import Instrument

def select_instrument(filter):
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
        return select_instrument(filter)
    
    selected_key = list(unique_instruments.keys())[selected_index]
    return unique_instruments[selected_key]

def test_oscilloscope_commands(resource_string):
    oscope = Oscilloscope(resource_string)
    try:
        oscope.open()
        print(f"Successfully connected to {oscope.identity().strip()}")
        oscope.reset()

        # Set up the trigger subsystem
        oscope.trigger.source = oscope.Source.CH1
        oscope.trigger.mode = oscope.trigger.Mode.EDGE
        oscope.trigger.slope = oscope.trigger.Slope.POSITIVE
        oscope.trigger.level = 2.0 #V

        # Autoscale and run single acquisition to test basic functionality
        oscope.autoscale()
        oscope.single()
        print("Single acquisition triggered.")

        # Fetch a trace from channel 1
        trace = oscope.waveform.fetch_trace(channel=1)
        print(f"Fetched trace from channel 1: {trace[:10]}...")  # Show a snippet of the trace

        # Query the Event Status Enable register to test base instrument class functionality
        ese_status = oscope.get_service_request()
        print(f"Event Status Enable Register Status: {ese_status}")

        # Experiment with more subsystem commands as needed
        oscope.timebase.scale = 0.0001  # Set timebase scale
        oscope.wavegen.output = oscope.wavegen.Output.ON
        oscope.wavegen.function = oscope.wavegen.Function.SINusoid
        oscope.wavegen.frequency = 1e3  # 1 kHz
        oscope.wavegen.amplitude = 1.0  # 1 V

        print("Configured waveform generator to output a 1 kHz sine wave.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        oscope.close()
        print("Connection to oscilloscope closed.")

if __name__ == '__main__':
    # The filter can be removed or changed for different connection types. 
    resource_string = select_instrument("TCPIP?*::INSTR")
    test_oscilloscope_commands(resource_string)
