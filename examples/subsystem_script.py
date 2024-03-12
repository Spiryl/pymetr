from pymetr.instrument import Instrument
from pymetr.properties import Subsystem, command_property, command_options
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)

class WaveGen(Subsystem):
    """
    Manages the built-in waveform generator (WGEN) of the oscilloscope, controlling waveform output and modulation.
    """

    # Nested enums for clean namespace and easy access
    Functions = command_options('Functions', ['SIN', 'SQU', 'RAMP', 'PULSE', 'NOISE', 'DC'])
    OutputState = command_options('OutputState', ['ON', 'OFF'])

    # Updated property definitions without redundant ":WGEN" prefix
    function = command_property(":FUNC", Functions, "Waveform function")
    frequency = command_property(":FREQ", doc_str="Waveform frequency")
    amplitude = command_property(":VOLT", doc_str="Waveform amplitude")
    output = command_property(":OUTP", OutputState, "Waveform output state")
    offset = command_property(":VOLT:OFFS", doc_str="Waveform offset")

    def __init__(self, parent):
        super().__init__(parent, ":WGEN")

# Example usage class that represents a custom instrument with a WaveGen subsystem
class MyInstrument(Instrument):
    def __init__(self, resource_string):
        super().__init__(resource_string)
        self.wavegen = WaveGen(self)  # Specific Subsystem for waveform generation

# Main routine to demonstrate usage
if __name__ == "__main__":
    # Instrument discovery and selection
    instrument_address = Instrument.select_resources("TCPIP?*INSTR")
    inst = MyInstrument(instrument_address)
    inst.open()

    # Engaging with the instrument
    print(inst.identity())

    # Specific subsystem tests showcasing all properties
    inst.wavegen.function = WaveGen.Functions.SQU  # Set waveform function
    print(f"Waveform function set to: {inst.wavegen.function}")

    inst.wavegen.frequency = '1MHz'  # Set frequency
    print(f"Wavegen frequency set to: {inst.wavegen.frequency}")

    inst.wavegen.amplitude = 2  # Set amplitude
    print(f"Wavegen amplitude set to: {inst.wavegen.amplitude}")

    inst.wavegen.offset = 0.5  # Set offset
    print(f"Wavegen offset set to: {inst.wavegen.offset}")

    inst.wavegen.output = WaveGen.OutputState.ON  # Enable output
    print(f"Wavegen output state set to: {inst.wavegen.output}")

    # Demonstrate toggling output state for completeness
    print("Toggling WaveGen output state...")
    inst.wavegen.output = WaveGen.OutputState.OFF
    print(f"Wavegen output state set to: {inst.wavegen.output}")

    # Clean up
    inst.close()
    print("Instrument connection closed.")
