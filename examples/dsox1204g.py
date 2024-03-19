from pymetr.instruments.dsox1204g import Oscilloscope
from pymetr import Instrument
import pyqtgraph as pg
import logging
import sys
from itertools import cycle
from PySide6.QtWidgets import QApplication

logging.basicConfig(level=logging.DEBUG)

# Initialize the QApplication instance
app = QApplication(sys.argv)

# Select an instrument
resource = Instrument.select_instrument("TCPIP?*::INSTR")

# Create an oscilloscope instance with the selected resource string
oscope = Oscilloscope(resource)

# Open a connection to the instrument
oscope.open()

# Clear any previous status/settings on the oscilloscope
oscope.clear_status()

# Set global sources and data format before fetching data
oscope.set_data_sources('CHAN1', 'CHAN2', 'CHAN3', 'CHAN4')
oscope.set_data_format('WORD')
oscope.waveform.byte_order = 'LSBFirst' # If using 16-bit 'WORD'
oscope.waveform.points_mode = 'MAX'
oscope.waveform.points = 1000
oscope.timebase.range = 0.01 #s

# Initiate a single acquisition
oscope.single()
oscope.query_operation_complete()

# Fetch trace data for the active (globally set) channels
trace_data = oscope.fetch_trace()

# Create a plot window with pyqtgraph
plot_window = pg.plot(title="Oscilloscope Data")

# Define a list of colors to use for the traces
colors = ['y', 'g', 'b', 'r']
color_cycle = cycle(colors)  # Cycle through the colors list

# Plot visible traces
for trace_id, trace_info in trace_data.items():
    if trace_info['visible']:
        color = next(color_cycle)  # Get the next color from the cycle
        plot_window.plot(trace_info['range'], trace_info['data'], pen=pg.mkPen(color, width=1))

oscope.close()

# Start the QApplication event loop to keep the window open
sys.exit(app.exec())
