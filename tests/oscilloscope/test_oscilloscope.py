import sys
import numpy as np

from Pymetr.oscilloscope.core import Oscilloscope  # Ensure Oscilloscope class is correctly imported


if __name__ == '__main__':
    osc = Oscilloscope("TCPIP0::192.168.1.111::hislip0::INSTR")
    osc.open()
    osc.handle.timeout = 15000
    osc.initialize()
    osc.setup_trigger(source="CHANnel1", level=2.0, slope='positive')
    osc.setup_timebase(scale=5e-4)
    osc.setup_channel(channel=1, scale=2)
    osc.setup_trace(channel="CHANnel1", points_mode="RAW", num_points=50000, format='byte')

