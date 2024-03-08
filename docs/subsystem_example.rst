Practical Coding Example:
-------------------------

This example demonstrates how to use the WaveGen subsystem of an instrument to control waveform output and modulation. Below, we detail the translation of property settings into SCPI commands.

.. code-block:: python

    from pymetr.instrument import Instrument
    from pymetr.subsystem import Subsystem, command_property, command_options

    class WaveGen(Subsystem):
        """
        Manages the built-in waveform generator (WGEN) of an instrument, controlling waveform output and modulation.
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

    class MyInstrument(Instrument):
        def __init__(self, resource_string):
            super().__init__(resource_string)
            self.wavegen = WaveGen(self)

    if __name__ == "__main__":

        # We can look for our instrument and select it via command line using the following static function.
        instrument_address = Instrument.select_resources("TCPIP?*INSTR")

        # We need to create an instance of our instrument and give it a name
        inst = MyInstrument(instrument_address)
        
        inst.open() # Open a connection to the instrument through PyVisa

        # Setting properties triggers SCPI write commands:
        inst.wavegen.function = WaveGen.Functions.SIN  # Triggers inst.write(":WGEN:FUNC SIN")
        inst.wavegen.frequency = '1MHz'  # Triggers inst.write(":WGEN:FREQ 1MHz")
        inst.wavegen.amplitude = 2  # Triggers inst.write(":WGEN:VOLT 2")
        inst.wavegen.offset = 0.5  # Triggers inst.write(":WGEN:VOLT:OFFS 0.5")
        inst.wavegen.output = WaveGen.OutputState.ON  # Triggers inst.write(":WGEN:OUTP ON")

        # Accessing properties triggers SCPI query commands:
        print(inst.wavegen.function)  # Triggers inst.query(":WGEN:FUNC?") and returns the function mode
        print(inst.wavegen.frequency)  # Triggers inst.query(":WGEN:FREQ?") and returns the frequency
        print(inst.wavegen.amplitude)  # Triggers inst.query(":WGEN:VOLT?") and returns the amplitude
        print(inst.wavegen.offset)  # Triggers inst.query(":WGEN:VOLT:OFFS?") and returns the offset
        print(inst.wavegen.output)  # Triggers inst.query(":WGEN:OUTP?") and returns the output state

        inst.close() # CLoses the instrument connection