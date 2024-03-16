Practical Coding Example:
-------------------------

This example demonstrates how to use the WaveGen subsystem of an instrument to control waveform output and modulation. Below, we detail the translation of property settings into SCPI commands.

.. code-block:: python

    from pymetr.instrument import Instrument
    from pymetr.subsystem import Subsystem, switch_property, select_property, value_property

    # Creating a custom waveform generator class by subclassing Subsystem
    class WaveGen(Subsystem):
        """
        Manages the built-in waveform generator (WGEN) of an instrument, controlling waveform output and modulation.
        """
        # Property definitions using the new decorators
        function = select_property(":FUNC", ['SIN', 'SQU', 'RAMP', 'PULSE', 'NOISE', 'DC'], doc_str="Waveform function")
        frequency = value_property(":FREQ", type="float", doc_str="Waveform frequency in Hz")
        amplitude = value_property(":VOLT", type="float", doc_str="Waveform amplitude in Volts")
        output = switch_property(":OUTP", doc_str="Waveform output state")
        offset = value_property(":VOLT:OFFS", type="float", doc_str="Waveform offset in Volts")

    # We can create a custom instrument which includes the wavegen subsystem by inheriting Instrument.
    class MyInstrument(Instrument):
        def __init__(self, resource_string):
            super().__init__(resource_string)
            self.wavegen = WaveGen(self, ':WGEN') # Here we aggregate the subsystem by creating an instance during init

    # This block only executes when the script is run directly and allows for creating tests in the same file as your new classes.
    if __name__ == "__main__":

        # We can look for our instrument and select it via command line using the following static function.
        instrument_address = Instrument.select_resources("TCPIP?*INSTR")

        # We need to create an instance of our instrument, pass it the address and give it a name
        inst = MyInstrument(instrument_address)

        # Open a connection to the instrument
        inst.open() 

        # Setting properties directly with the desired values:
        inst.wavegen.function = 'SIN'  # Triggers inst.write(":WGEN:FUNC SIN")
        inst.wavegen.frequency = 1e6  # Triggers inst.write(":WGEN:FREQ 1e6")
        inst.wavegen.amplitude = 2  # Triggers inst.write(":WGEN:VOLT 2")
        inst.wavegen.offset = 0.5  # Triggers inst.write(":WGEN:VOLT:OFFS 0.5")
        inst.wavegen.output = 'ON'  # Triggers inst.write(":WGEN:OUTP ON")

        # Accessing properties to get the current settings:
        print(inst.wavegen.function)  # Triggers inst.query(":WGEN:FUNC?") and returns the function mode
        print(inst.wavegen.frequency)  # Triggers inst.query(":WGEN:FREQ?") and returns the frequency
        print(inst.wavegen.amplitude)  # Triggers inst.query(":WGEN:VOLT?") and returns the amplitude
        print(inst.wavegen.offset)  # Triggers inst.query(":WGEN:VOLT:OFFS?") and returns the offset
        print(inst.wavegen.output)  # Triggers inst.query(":WGEN:OUTP?") and returns the output state

        inst.close() # Closes the instrument connection

We can now see that we can easily create test scripts focusing on the logic flow of the script and without the distraction of dealing with SCPI commands strings directly.