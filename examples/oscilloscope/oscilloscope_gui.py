# oscilloscope_app.py
import logging
import numpy as np
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QDockWidget, QTabWidget, QWidget, QCheckBox, QComboBox, QLineEdit, QLabel,QPushButton, QHBoxLayout, QColorDialog)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QDockWidget, QWidget, QPushButton, QDial, QLabel, QHBoxLayout, QColorDialog, QSlider, QGroupBox, QSizePolicy)
from PySide6.QtGui import QPalette, QColor
from vispy import scene

from oscilloscope_controls import AcquireControl, WaveformControl, WaveGenControl, TriggerControl, TimebaseControl,  ChannelControl, ControlDock
from pyinstrument.oscilloscope.core import Oscilloscope
from pyinstrument.instruments import SCPIInstrument
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
        for channel_num, channel in self.oscope.channels.items():
            if channel.display == 'ON':
                trace_data = self.oscope.waveform.fetch_trace(channel_num)
                trace_data_dict[channel_num] = trace_data
        self.data_fetched.emit(trace_data_dict)

class VisPyCanvas(scene.SceneCanvas):
    def __init__(self):
        super(VisPyCanvas, self).__init__(keys='interactive', show=True, bgcolor='#1A1A1A')
        self.unfreeze()
        self.setup_view()
        self.lines = {}  # key: channel name, value: Line object
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
        # Random initial data for visualization
        N = 200
        y_lim = [-2., 2.]

        # Set up initial colors for each channel
        channel_colors = {
            'CHAN1': (1, 0, 0, 1),  # Red
            'CHAN2': (0, 1, 0, 1),  # Green
            'CHAN3': (0, 0, 1, 1),  # Blue
            'CHAN4': (1, 1, 0, 1)   # Yellow
        }

        # Initialize line visuals for each channel with random data
        for channel_name, color in channel_colors.items():
            pos = np.empty((N, 2), dtype=np.float32)
            pos[:, 0] = np.linspace(0, N, N)
            pos[:, 1] = np.random.uniform(y_lim[0], y_lim[1], N)
            color_array = np.repeat(np.array(color)[np.newaxis, :], N, axis=0)
            self.lines[channel_name] = scene.Line(pos, color=color_array, parent=self.view.scene)

        self.view.camera.set_range()

    @debug
    def update_trace(self, channel_name, trace_data):
        # This method updates a specific channel's line visual with new data
        if channel_name not in self.lines:
            return  # Skip if the channel is not recognized

        N = len(trace_data)
        pos = np.zeros((N, 2), dtype=np.float32)
        pos[:, 0] = np.linspace(0, N, N)  # Adjust these ranges based on your actual data scale
        pos[:, 1] = trace_data

        self.lines[channel_name].set_data(pos=pos)
        self.view.camera.set_range()

    def update_multiple_traces(self, trace_data_dict):
        # This method updates multiple channels based on the incoming dictionary
        for channel_name, trace_data in trace_data_dict.items():
            self.update_trace(channel_name, trace_data)
        self.view.camera.set_range()

class MainWindow(QMainWindow):
    def __init__(self, oscope):
        super(MainWindow, self).__init__()
        self.setWindowTitle('Oscilloscope Visualization')
        self.oscope = oscope
        self.setupUI()
        
    def setupUI(self):
        self.setupCanvas()
        self.setupOverlayControls()

    def setupCanvas(self):
        self.canvas = VisPyCanvas()
        self.setCentralWidget(self.canvas.native)
        
    def setupOverlayControls(self):
        self.overlayControls = QWidget(self.canvas.native)
        self.overlayControlsLayout = QVBoxLayout(self.overlayControls)
        self.overlayControls.setLayout(self.overlayControlsLayout)
        
        self.singleButton = QPushButton("Single Acquisition")
        self.singleButton.clicked.connect(self.single_fetch)
        self.overlayControlsLayout.addWidget(self.singleButton)
        
        self.overlayControls.move(self.canvas.native.width() - self.overlayControls.width() - 20, 20)
        self.overlayControls.setStyleSheet("background-color: rgba(31, 31, 31, 150); padding: 5px;")

    def single_fetch(self):
        self.oscope.single()  # Trigger a single acquisition
        trace_data_dict = {}
        for channel_num in range(1, 5):  # Assuming 4 channels for simplicity
            self.oscope.waveform.source = channel_num  # Set the waveform source to the current channel
            trace_data = self.oscope.waveform.fetch_trace()  # Fetch the waveform data for the channel
            if trace_data is not None:
                trace_data_dict[f'CHAN{channel_num}'] = trace_data
        self.canvas.update_multiple_traces(trace_data_dict)  # Update the GUI with fetched waveforms
        
    def resizeEvent(self, event):
        super(MainWindow, self).resizeEvent(event)
        # Reposition overlay controls when the main window is resized
        if self.canvas and self.overlayControls:
            self.overlayControls.move(self.canvas.native.width() - self.overlayControls.width() - 20, 20)

    def setupControls(self):

        self.acquire_dock = ControlDock("Acquire Controls", lambda oscope: AcquireControl(oscope), self.oscope, self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.acquire_dock)

        self.trigger_dock = ControlDock("Trigger Controls", lambda oscope: TriggerControl(oscope), self.oscope, self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.trigger_dock)

        self.timebase_dock = ControlDock("Timebase Controls", lambda oscope: TimebaseControl(oscope), self.oscope, self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.timebase_dock)

        self.waveform_dock = ControlDock("Waveform Controls", lambda oscope: WaveformControl(oscope), self.oscope, self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.waveform_dock)

        self.wavegen_dock = ControlDock("WaveGen Controls", lambda oscope: WaveGenControl(oscope), self.oscope, self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.wavegen_dock)

        self.channel_control = ChannelControl(self.oscope, self)
        self.channel_container = QWidget()
        self.channel_container_layout = QVBoxLayout(self.channel_container)
        self.channel_container_layout.addWidget(self.channel_control)
        self.channel_dock = QDockWidget("Channel Controls", self)
        self.channel_dock.setWidget(self.channel_container)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.channel_dock)

    def toggle_continuous_fetch(self, checked):
        if checked:
            self.start_continuous_fetch()
            self.runButton.setText("Stop Continuous")
        else:
            self.stop_continuous_fetch()
            self.runButton.setText("Run Continuous")

    def start_continuous_fetch(self):
        self.oscope.run()
        self.continuous_fetch = True
        if not self.fetch_thread.isRunning():
            self.fetch_thread.start()

    def stop_continuous_fetch(self):
        self.oscope.stop()
        self.continuous_fetch = False
    
    def on_data_fetched(self, trace_data_dict):
        self.canvas.update_multiple_traces(trace_data_dict)

def select_instrument(filter):
    unique_instruments, failed_queries = SCPIInstrument.list_resources(filter)
    
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
        return select_instrument()
    
    selected_key = list(unique_instruments.keys())[selected_index]
    return unique_instruments[selected_key]

if __name__ == '__main__':

    # The filter can be removed or changed for different connection types. 
    resource_string = select_instrument("TCPIP?*::INSTR")
    oscope = Oscilloscope(resource_string)
    try:
        oscope.open()
        print(f"Successfully connected to {oscope.identity().strip()}")
    except:
        pass

    oscope.reset()

    # Set up the trigger subsystem
    oscope.trigger.source = oscope.Source.CH1
    oscope.trigger.mode = oscope.trigger.Mode.EDGE
    oscope.trigger.slope = oscope.trigger.Slope.POSITIVE
    oscope.trigger.level = 2.0 #V

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
