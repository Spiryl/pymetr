# oscilloscope_app.py
import logging
import numpy as np
import sys

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QDockWidget, QTabWidget, QWidget, QPushButton, QHBoxLayout)
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QGroupBox, QSizePolicy)
from PySide6.QtGui import QPalette, QColor
from vispy import scene

from oscilloscope_controls import AcquireControl, WaveformControl, WaveGenControl, TriggerControl, TimebaseControl,  ChannelControl
from pymetr.oscilloscope import Oscilloscope
from pymetr.instrument import Instrument
from utilities import debug, timeit

class FetchThread(QThread):
    data_fetched = Signal(dict)  # Emit a dictionary for multiple channels

    def __init__(self, oscope, continuous_fetch_getter, parent=None):
        super(FetchThread, self).__init__(parent)
        self.oscope = oscope
        self.continuous_fetch_getter = continuous_fetch_getter
        self.single_fetch_mode = False  # New attribute to control fetch mode

    def run(self):
        if self.single_fetch_mode:
            self.fetch_data()
        else:
            while self.continuous_fetch_getter():
                self.fetch_data()

    def fetch_data(self):
        trace_data_dict = {}
        for channel_num in range(1, 5):  # Assuming 4 channels for simplicity
            # Assuming you have a method to check if a channel is active...
            if self.oscope.channels[channel_num].is_active():
                volts, times = self.oscope.waveform.fetch_data(channel_num)
                trace_data_dict[channel_num] = {'volts': volts, 'times': times}
            
        self.data_fetched.emit(trace_data_dict)

class VisPyCanvas(scene.SceneCanvas):
    def __init__(self):
        super(VisPyCanvas, self).__init__(keys='interactive', show=True, bgcolor='#1A1A1A')
        self.unfreeze()
        self.setup_view()
        self.lines = {}  # key: channel name, value: Line object
        self.colors = {}  # Store original colors
        self.initialize_lines()

    def setup_view(self):
        self.grid = self.central_widget.add_grid(spacing=0)
        self.view = self.grid.add_view(row=0, col=1, camera='panzoom')
        self.setup_axes()

    def setup_axes(self):
        self.x_axis = scene.AxisWidget(orientation='bottom')
        self.x_axis.stretch = (1, 0.06)
        self.grid.add_widget(self.x_axis, row=1, col=1)
        self.x_axis.link_view(self.view)

        self.y_axis = scene.AxisWidget(orientation='left')
        self.y_axis.stretch = (0.08, 1)
        self.grid.add_widget(self.y_axis, row=0, col=0)
        self.y_axis.link_view(self.view)

    def initialize_lines(self):
        N = 500
        y_lim = [-0.01, 0.01]
        channel_colors = {
            'CHAN1': (1, 1, 0, 1),
            'CHAN2': (0, 1, 0, 1),
            'CHAN3': (0, 0, 1, 1),
            'CHAN4': (1, 0, 0, 1)
        }

        for channel_name, color in channel_colors.items():
            pos = np.empty((N, 2), dtype=np.float32)
            pos[:, 0] = np.linspace(y_lim[0], y_lim[1], N)
            pos[:, 1] = np.random.uniform(y_lim[0], y_lim[1], N)
            self.colors[channel_name] = color  # Save original color
            self.lines[channel_name] = scene.Line(pos, color=color, parent=self.view.scene)

    def update_trace(self, channel_name, trace_data, trace_time, visible):
        # Ensure this channel is recognized and initialized in your visualization setup
        if channel_name not in self.lines:
            return

        # Prepare the position data
        N = len(trace_time)
        pos = np.zeros((N, 2), dtype=np.float32)
        pos[:, 0] = trace_time
        pos[:, 1] = trace_data

        # Determine the visibility; if not visible, we might opt to hide the line
        # by setting its color to fully transparent or by other means like setting
        # the data off-screen.
        if visible:
            # Update the line with actual data and original color
            color = self.colors[channel_name]
            self.lines[channel_name].set_data(pos=pos, color=color)
        else:
            # Option 1: Make the line transparent
            self.lines[channel_name].set_data(pos=pos, color=(0, 0, 0, 0))

    def update_multiple_traces(self, trace_data_dict):
        for channel_name, data in trace_data_dict.items():
            self.update_trace(channel_name, data['volts'], data['times'], data['visible'])
        self.view.camera.set_range()

class MainWindow(QMainWindow):
    def __init__(self, oscope):
        super(MainWindow, self).__init__()
        self.setWindowTitle('Oscilloscope Visualization')
        self.oscope = oscope
        self.setupUI()
        self.resizeEvent(None)
        
    def setupUI(self):
        self.setupCanvas()
        self.setupOverlayControls()
        self.setupControls()

    def setupCanvas(self):
        self.canvas = VisPyCanvas()
        self.setCentralWidget(self.canvas.native)
        
    def setupOverlayControls(self):
        self.overlayControls = QWidget(self.canvas.native)
        self.overlayControlsLayout = QVBoxLayout(self.overlayControls)
        self.overlayControls.setLayout(self.overlayControlsLayout)
        
        self.autoScaleButton = QPushButton("Auto Scale")
        self.autoScaleButton.clicked.connect(self.auto_scale)
        self.overlayControlsLayout.addWidget(self.autoScaleButton)

        self.singleButton = QPushButton("Single Acquisition")
        self.singleButton.clicked.connect(self.single_fetch)
        self.overlayControlsLayout.addWidget(self.singleButton)
        
        self.overlayControls.move(self.canvas.native.width() - self.overlayControls.width() - 20, 20)
        self.overlayControls.setStyleSheet("background-color: rgba(31, 31, 31, 150); padding: 5px;")

    def auto_scale(self):
        self.oscope.autoscale()
        
    def resizeEvent(self, event):
        super(MainWindow, self).resizeEvent(event)
        # Reposition overlay controls when the main window is resized
        if self.canvas and self.overlayControls:
            self.overlayControls.move(self.canvas.native.width() - self.overlayControls.width() - 20, 20)

    def setupControls(self):
        # Creating a widget for the combined controls panel
        combined_controls_widget = QWidget()
        combined_controls_layout = QHBoxLayout(combined_controls_widget)  # Switched to QHBoxLayout for horizontal layout

        # Creating group boxes for each set of controls
        acquire_group = QGroupBox("Acquire Controls")
        acquire_layout = QVBoxLayout(acquire_group)
        acquire_layout.addWidget(AcquireControl(self.oscope, acquire_group))

        trigger_group = QGroupBox("Trigger Controls")
        trigger_layout = QVBoxLayout(trigger_group)
        trigger_layout.addWidget(TriggerControl(self.oscope, trigger_group))

        timebase_group = QGroupBox("Timebase Controls")
        timebase_layout = QVBoxLayout(timebase_group)
        timebase_layout.addWidget(TimebaseControl(self.oscope, timebase_group))

        waveform_group = QGroupBox("Waveform Controls")
        waveform_layout = QVBoxLayout(waveform_group)
        waveform_layout.addWidget(WaveformControl(self.oscope, waveform_group))

        # Adding group boxes to the combined controls layout
        combined_controls_layout.addWidget(acquire_group)
        combined_controls_layout.addWidget(trigger_group)
        combined_controls_layout.addWidget(timebase_group)
        combined_controls_layout.addWidget(waveform_group)

        combined_controls_dock = QDockWidget("Advanced Controls", self)
        combined_controls_dock.setWidget(combined_controls_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, combined_controls_dock)

        # Channel Controls Setup
        self.channel_dock = QDockWidget("Channel Controls", self)
        channel_widget = QWidget()
        channel_layout = QVBoxLayout(channel_widget)
        channel_layout.addWidget(ChannelControl(self.oscope, self.channel_dock))
        self.channel_dock.setWidget(channel_widget)

        # WaveGen Controls Setup (Docked separately on the bottom left)
        self.wavegen_dock = QDockWidget("WaveGen Controls", self)
        wavegen_widget = QWidget()
        wavegen_layout = QVBoxLayout(wavegen_widget)
        wavegen_layout.addWidget(WaveGenControl(self.oscope, self.wavegen_dock))
        self.wavegen_dock.setWidget(wavegen_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.wavegen_dock)

        # Docking Channel and Advanced Controls together, to the right of WaveGen controls
        self.splitDockWidget(self.wavegen_dock, self.channel_dock, Qt.Horizontal)
        self.tabifyDockWidget(self.channel_dock, combined_controls_dock)  # Tabify Channel with Advanced Controls
    
    def single_fetch(self):
        self.oscope.clear_status()
        self.oscope.single()
        self.oscope.digitize()
        self.oscope.query_operation_complete()

        # Fetch the time base for all traces first, ensuring uniform x-axis across channels
        times = self.oscope.waveform.fetch_time()
        print(f"the length of times is : {len(times)}")

        trace_data_dict = {}
        # Assuming source_mapping and channel display info is correctly configured in your oscilloscope object
        source_mapping = {1: 'CHAN1', 2: 'CHAN2', 3: 'CHAN3', 4: 'CHAN4'}

        # Loop over all channels to fetch or simulate data based on visibility
        for channel_num in range(1, 5):
            source = source_mapping[channel_num]
            visible = self.oscope.channels[channel_num].display in ['On', '1']
            
            if visible:
                volts = self.oscope.waveform.fetch_data(source)
            else:
                # For non-visible channels, simulate zero data with the correct size
                volts = np.zeros(times.shape)
            
            # Regardless of visibility, store data with uniform size and the visibility flag
            trace_data_dict[source] = {'volts': volts, 'times': times, 'visible': visible}

        # Update visualization with the prepared trace data, all of uniform size
        self.canvas.update_multiple_traces(trace_data_dict)

    def on_data_fetched(self, trace_data_dict):
        self.canvas.update_multiple_traces(trace_data_dict)

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # The filter can be removed or changed for different connection types. 
    resource_string = Instrument.select_instrument("TCPIP?*::INSTR")
    oscope = Oscilloscope(resource_string)
    oscope.data_format = 'ASCII'  # This would be the overall format (ASCII or BINARY)
    oscope.data_type = 'b'
    
    try:
        oscope.open()
        print(f"Successfully connected to {oscope.identity().strip()}")
    except:
        pass

    oscope.reset()
    
    # Configuration for waveform fetching
    oscope.waveform.source = oscope.Sources.CHAN1
    oscope.waveform.format = "ASCII"  # or 'WORD'
    oscope.waveform.points_mode = oscope.waveform.PointsModes.NORMAL
    oscope.waveform.points = 500
    oscope.waveform.unsigned = True
    oscope.read_termination = '\n'
    oscope.write_termination = '\n'


    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(36, 36, 36))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(36, 36, 36))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(36, 36, 36))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)

    win = MainWindow(oscope)
    win.show()
    # win.start_continuous_fetch()  # Make sure this method aligns with your MainWindow class methods
    sys.exit(app.exec())
