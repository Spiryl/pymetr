from pymetr.instruments import Oscilloscope
from pymetr.instrument import Instrument

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
    resource_string = Oscilloscope.select_instrument("TCPIP?*::INSTR")
    test_oscilloscope_commands(resource_string)
