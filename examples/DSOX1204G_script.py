from pymetr.instruments.dsox1204g import Oscilloscope
import pyqtgraph as pg
import logging
import sys
from itertools import cycle
from PySide6.QtWidgets import QApplication

logging.basicConfig(level=logging.CRITICAL)

# Initialize the QApplication instance
app = QApplication(sys.argv)

resource = Oscilloscope.select_instrument("TCPIP?*::INSTR")
oscope = Oscilloscope(resource)
oscope.open()
oscope.reset()
oscope.autoscale()
oscope.clear_status()
<<<<<<< HEAD
oscope.set_data_sources('CHAN1')
oscope.set_data_format('WORD')
oscope.waveform.byte_order = 'LSBFirst' # If using 16-bit 'WORD'
=======
oscope.source = ['CHAN1', 'CHAN2']
oscope.set_format('BYTE')
# oscope.waveform.byte_order = 'LSBFirst' # If using 16-bit 'WORD'
>>>>>>> in_progress
oscope.waveform.points_mode = 'MAX'
oscope.waveform.points = 10000
oscope.timebase.range = 0.1 #s

# confirm indexing
print(f"Channel 1 probe value: {oscope.channel[1].probe}")
print(f"Channel 2 display value: {oscope.channel[2].display}")
print(f"Channel 3 coupling value: {oscope.channel[3].coupling}")

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
