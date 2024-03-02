# oscilloscope_gui.py
import logging
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QDockWidget, QTabWidget, QWidget, QCheckBox, QComboBox, QLineEdit, QLabel,QPushButton, QHBoxLayout, QColorDialog)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QDockWidget, QWidget, QPushButton, QDial, QLabel, QHBoxLayout, QColorDialog, QSlider, QGroupBox, QSizePolicy)
from PySide6.QtGui import QPalette, QColor
from vispy import scene, visuals
import numpy as np
from Pymetr.oscilloscope.core import Oscilloscope 
from Pymetr.instruments import Instrument
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
        if self.single_fetch_mode:
            self.single_fetch_mode = False  # Reset after single fetch

    def set_single_fetch_mode(self, mode):
        self.single_fetch_mode = mode

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

class WaveformControl(QWidget):
    def __init__(self, oscope, parent=None):
        super(WaveformControl, self).__init__(parent)
        self.oscope = oscope
        self.layout = QVBoxLayout(self)

        # Data Format
        self.format_label = QLabel("Data Format:")
        self.layout.addWidget(self.format_label)
        self.format_combobox = QComboBox()
        self.format_combobox.addItems(["BYTE", "WORD", "ASCII"])
        self.layout.addWidget(self.format_combobox)
        self.format_combobox.currentTextChanged.connect(self.update_format)

        # Points Mode
        self.points_mode_label = QLabel("Points Mode:")
        self.layout.addWidget(self.points_mode_label)
        self.points_mode_combobox = QComboBox()
        self.points_mode_combobox.addItems(["NORMAL", "MAXIMUM", "RAW"])
        self.layout.addWidget(self.points_mode_combobox)
        self.points_mode_combobox.currentTextChanged.connect(self.update_points_mode)

        # Number of Points
        self.num_points_label = QLabel("Number of Points:")
        self.layout.addWidget(self.num_points_label)
        self.num_points_field = QLineEdit()
        self.layout.addWidget(self.num_points_field)
        self.num_points_field.editingFinished.connect(self.update_num_points)

        # Fetch Button
        self.fetch_button = QPushButton("Fetch Waveform")
        self.layout.addWidget(self.fetch_button)
        self.fetch_button.clicked.connect(self.fetch_waveform)

    def update_format(self):
        self.oscope.waveform.format = self.format_combobox.currentText()

    def update_points_mode(self):
        self.oscope.waveform.points_mode = self.points_mode_combobox.currentText()

    def update_num_points(self):
        num_points = int(self.num_points_field.text())
        self.oscope.waveform.num_points = num_points

    def fetch_waveform(self):
            # Assuming a method to fetch and display waveform data
            # This might involve fetching data for all active channels and updating the display accordingly
            # You might need to implement or adjust this method based on how your application handles data visualization
            for channel_num in self.oscope.channels:
                if self.oscope.channels[channel_num].display == 'ON':
                    trace_data = self.oscope.waveform.fetch_trace(channel=channel_num)
                    # Update your visualization with the fetched trace_data here

class WaveGenControl(QWidget):
    def __init__(self, oscope, parent=None):
        super(WaveGenControl, self).__init__(parent)
        self.oscope = oscope
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        # Enable checkbox
        self.enable_checkbox = QCheckBox("Enable")
        self.enable_checkbox.stateChanged.connect(self.toggle_enable)
        self.layout.addWidget(self.enable_checkbox)

        # Frequency controls
        self.frequency_label = QLabel("Frequency:")
        self.frequency_field = QLineEdit()
        self.frequency_field.editingFinished.connect(self.update_frequency)
        self.layout.addWidget(self.frequency_label)
        self.layout.addWidget(self.frequency_field)

        # Waveform type controls
        self.waveform_type_label = QLabel("Waveform Type:")
        self.waveform_type_combobox = QComboBox()
        self.waveform_type_combobox.addItems(["Sine", "Square", "Triangle"])
        self.waveform_type_combobox.currentIndexChanged.connect(self.update_waveform_type)
        self.layout.addWidget(self.waveform_type_label)
        self.layout.addWidget(self.waveform_type_combobox)

        # Amplitude controls
        self.amplitude_label = QLabel("Amplitude:")
        self.amplitude_field = QLineEdit()
        self.amplitude_field.editingFinished.connect(self.update_amplitude)
        self.layout.addWidget(self.amplitude_label)
        self.layout.addWidget(self.amplitude_field)

    def connect_signals(self):
        # Connect UI elements to their corresponding methods
        pass  # Placeholder, as signals are connected in init_ui

    def toggle_enable(self, state):
        self.oscope.wavegen.output = 'ON' if state == Qt.Checked else 'OFF'
        
    def update_frequency(self):
        frequency = float(self.frequency_field.text())
        self.oscope.wavegen.frequency = frequency

    def update_waveform_type(self):
        waveform_type = self.waveform_type_combobox.currentText().lower()
        self.oscope.wavegen.function = waveform_type

    def update_amplitude(self):
        amplitude = float(self.amplitude_field.text())
        self.oscope.wavegen.amplitude = amplitude

    def sync(self):
        # Sync the GUI with the current state of the oscilloscope's waveform generator
        self.enable_checkbox.setChecked(self.oscope.wavegen.output == 'ON')
        self.frequency_field.setText(str(self.oscope.wavegen.frequency))
        self.waveform_type_combobox.setCurrentText(self.oscope.wavegen.function.capitalize())
        self.amplitude_field.setText(str(self.oscope.wavegen.amplitude))

class TriggerControl(QWidget):
    def __init__(self, oscope, parent=None):
        super(TriggerControl, self).__init__(parent)
        self.oscope = oscope
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        # Trigger Source
        self.trigger_source_label = QLabel("Trigger Source:")
        self.trigger_source_combobox = QComboBox()
        self.trigger_source_combobox.addItems(["Channel 1", "Channel 2", "External"])
        self.layout.addWidget(self.trigger_source_label)
        self.layout.addWidget(self.trigger_source_combobox)

        # Trigger Edge
        self.trigger_edge_label = QLabel("Trigger Edge:")
        self.trigger_edge_combobox = QComboBox()
        self.trigger_edge_combobox.addItems(["Rising", "Falling"])
        self.layout.addWidget(self.trigger_edge_label)
        self.layout.addWidget(self.trigger_edge_combobox)

        # Trigger Level
        self.trigger_value_label = QLabel("Trigger Level:")
        self.trigger_value_field = QLineEdit()
        self.layout.addWidget(self.trigger_value_label)
        self.layout.addWidget(self.trigger_value_field)

    def connect_signals(self):
        self.trigger_source_combobox.currentIndexChanged.connect(self.update_trigger_source)
        self.trigger_edge_combobox.currentIndexChanged.connect(self.update_trigger_edge)
        self.trigger_value_field.editingFinished.connect(self.update_trigger_level)

    def update_trigger_source(self):
        source = self.trigger_source_combobox.currentText()
        self.oscope.trigger.source = source

    def update_trigger_edge(self):
        edge = self.trigger_edge_combobox.currentText().lower()
        self.oscope.trigger.slope = edge

    def update_trigger_level(self):
        level = float(self.trigger_value_field.text())
        self.oscope.trigger.level = level

class AcquireControl(QWidget):
    def __init__(self, oscope, parent=None):
        super(AcquireControl, self).__init__(parent)
        self.oscope = oscope
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        # Maybe you wanna add more acquire settings here, like sample rate or mode
        # Example: Acquisition Mode (Normal, Peak Detect, High Resolution...)
        self.mode_label = QLabel("Acquisition Mode:")
        self.mode_combobox = QComboBox()
        self.mode_combobox.addItems(["Normal", "Peak Detect", "High Resolution"])
        self.layout.addWidget(self.mode_label)
        self.layout.addWidget(self.mode_combobox)

        # Sample Rate if applicable
        self.sample_rate_label = QLabel("Sample Rate (S/s):")
        self.sample_rate_field = QLineEdit()
        self.layout.addWidget(self.sample_rate_label)
        self.layout.addWidget(self.sample_rate_field)

    def connect_signals(self):
        self.mode_combobox.currentIndexChanged.connect(self.update_acquisition_mode)
        self.sample_rate_field.editingFinished.connect(self.update_sample_rate)

    def update_acquisition_mode(self):
        mode = self.mode_combobox.currentText()
        # Assuming your backend can handle setting the mode like this
        self.oscope.acquire.mode = mode.lower().replace(" ", "_")

    def update_sample_rate(self):
        rate = float(self.sample_rate_field.text())
        # Assuming your backend can handle setting the sample rate
        self.oscope.acquire.sample_rate = rate

    def sync(self):
        # You'd call this to update the GUI with the oscilloscope's current settings
        # Assuming your acquire settings are easily queryable
        self.mode_combobox.setCurrentText(self.oscope.acquire.mode.replace("_", " ").capitalize())
        self.sample_rate_field.setText(str(self.oscope.acquire.sample_rate))

class TimebaseControl(QWidget):
    def __init__(self, oscope, parent=None):
        super(TimebaseControl, self).__init__(parent)
        self.oscope = oscope
        self.layout = QVBoxLayout(self)

        # Timebase Scale
        self.scale_label = QLabel("Scale (s/div):")
        self.layout.addWidget(self.scale_label)
        self.scale_field = QLineEdit()
        self.layout.addWidget(self.scale_field)
        self.scale_field.editingFinished.connect(self.update_scale)

        # Timebase Position
        self.position_label = QLabel("Position (s):")
        self.layout.addWidget(self.position_label)
        self.position_field = QLineEdit()
        self.layout.addWidget(self.position_field)
        self.position_field.editingFinished.connect(self.update_position)

        # Apply Button (if immediate application is not desired)
        self.apply_button = QPushButton("Apply")
        self.layout.addWidget(self.apply_button)
        self.apply_button.clicked.connect(self.apply_changes)

    def update_scale(self):
        scale = float(self.scale_field.text())
        self.oscope.timebase.scale = scale

    def update_position(self):
        position = float(self.position_field.text())
        self.oscope.timebase.position = position

    def apply_changes(self):
        # This method might call other methods or simply be used to apply changes at once
        self.update_scale()
        self.update_position()

class ChannelControlPanel(QWidget):
    channel_colors = {1: "yellow", 2: "green", 3: "blue", 4: "red"}

    def __init__(self, channel, parent=None):
        super(ChannelControlPanel, self).__init__(parent)
        self.channel = channel

        main_layout = QHBoxLayout(self)

        self.channel_group_box = QGroupBox(f"Channel {self.channel.channel_number}")

        group_layout = QVBoxLayout()

        self.enable_button = QPushButton("Enable", self)
        self.enable_button.setCheckable(True)
        self.enable_button.setChecked(self.channel.display == 'ON')
        self.enable_button.toggled.connect(self.update_enable_state)

        # Set the initial color for the enable button based on the channel's display status
        self.update_button_color()
        group_layout.addWidget(self.enable_button)

        self.range_dial = QDial()
        self.range_dial.setRange(0, 3)  # Assuming 4 range options
        self.range_dial.setNotchesVisible(True)
        self.range_dial.valueChanged.connect(self.update_range_dial_label)
        self.range_label = QLabel("Range: ±1V")  # Default value
        group_layout.addWidget(self.range_dial)
        group_layout.addWidget(self.range_label)

        controls_layout = QHBoxLayout()

        self.coupling_toggle = QPushButton("Coupling: AC")  # Default to AC
        self.coupling_toggle.setCheckable(True)
        self.coupling_toggle.toggled.connect(self.update_coupling)
        controls_layout.addWidget(self.coupling_toggle)

        # Set the initial color of the color button based on the channel number
        initial_color = self.channel_colors.get(self.channel.channel_number, 'grey')
        self.color_button = QPushButton()
        self.color_button.setStyleSheet(f"background-color: {initial_color}")
        self.color_button.clicked.connect(self.open_color_dialog)
        controls_layout.addWidget(self.color_button)

        group_layout.addLayout(controls_layout)

        # Offset slider
        self.offset_slider = QSlider(Qt.Vertical)
        self.offset_slider.setMinimum(-100)  # Assuming offset range
        self.offset_slider.setMaximum(100)
        self.offset_slider.setValue(self.channel.offset)
        self.offset_slider.valueChanged.connect(self.update_offset)
        main_layout.addWidget(self.offset_slider)

        self.channel_group_box.setLayout(group_layout)
        main_layout.addWidget(self.channel_group_box)

    def update_enable_state(self, enabled):
        # Update the channel display state
        self.channel.display = 'ON' if enabled else 'OFF'
        self.update_button_color()

    def update_button_color(self):
        # Update the button color based on the channel state
        if self.channel.display == 'ON':
            color = self.channel_colors.get(self.channel.channel_number, 'grey')
            self.enable_button.setStyleSheet(f"background-color: {color};")
        else:
            self.enable_button.setStyleSheet("")  # Reset to default style or set to a disabled color

    def update_range_dial_label(self, value):
        ranges = ["±1V", "±2V", "±5V", "±10V"]
        self.range_label.setText(f"Range: {ranges[value]}")
        self.channel.range = ranges[value]

    def update_coupling(self, toggled):
        self.channel.coupling = 'DC' if toggled else 'AC'
        self.coupling_toggle.setText(f"Coupling: {'DC' if toggled else 'AC'}")

    def update_offset(self, value):
        self.channel.offset = value

    def open_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.color_button.setStyleSheet(f"background-color: {color.name()}")
            # Update the channel color here if needed

class ChannelControl(QWidget):
    # Define default channel colors
    DEFAULT_COLORS = {1: QColor('yellow'), 2: QColor('green'), 3: QColor('blue'), 4: QColor('red')}

    def __init__(self, oscope, parent=None):
        super(ChannelControl, self).__init__(parent)
        self.oscope = oscope
        self.layout = QHBoxLayout(self)  # Changed to horizontal layout
        
        # Create a ChannelControlPanel for each channel without passing the color
        for channel_num, channel in self.oscope.channels.items():
            channel_panel = ChannelControlPanel(channel)
            self.layout.addWidget(channel_panel)

class ControlDock(QDockWidget):
    def __init__(self, title, create_control_callback, oscope, parent=None):
        super(ControlDock, self).__init__(title, parent)
        self.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.oscope = oscope  # Store the oscilloscope reference for use in the controls
        self.main_widget = QWidget()
        self.setWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        # Create the specific control for this dock using the provided callback function
        self.control = create_control_callback(self.oscope)
        self.layout.addWidget(self.control)

        # Add stretch to push everything up
        self.layout.addStretch()

class MainWindow(QMainWindow):
    def __init__(self, oscope):
        super(MainWindow, self).__init__()
        self.setWindowTitle('Oscilloscope Visualization')
        self.oscope = oscope
        self.setupUI()
        self.continuous_fetch = False
        self.fetch_thread = FetchThread(self.oscope, self.get_continuous_fetch)
        self.fetch_thread.data_fetched.connect(self.on_data_fetched)
        
    def setupUI(self):
        self.setupCanvas()
        self.setupOverlayControls()
        self.setupControls()
        
    def setupCanvas(self):
        self.canvas = VisPyCanvas()
        self.setCentralWidget(self.canvas.native)
        
    def setupOverlayControls(self):
        # Container for the overlay controls
        self.overlayControls = QWidget(self.canvas.native)
        self.overlayControlsLayout = QVBoxLayout(self.overlayControls)
        self.overlayControls.setLayout(self.overlayControlsLayout)
        
        # Run Continuous Button
        self.runButton = QPushButton("Run Continuous")
        self.runButton.setCheckable(True)  # Make it a toggle button
        self.runButton.toggled.connect(self.toggle_continuous_fetch)
        self.overlayControlsLayout.addWidget(self.runButton)
        
        # Single Acquisition Button
        self.singleButton = QPushButton("Single Acquisition")
        self.singleButton.clicked.connect(self.single_fetch)
        self.overlayControlsLayout.addWidget(self.singleButton)
        
        # Position the overlay controls on the canvas
        self.overlayControls.move(self.canvas.native.width() - self.overlayControls.width() - 20, 20)
        
        # Optional: Make the overlay background semi-transparent or styled differently
        self.overlayControls.setStyleSheet("background-color: rgba(31, 31, 31, 150); padding: 5px;")
        
    def resizeEvent(self, event):
        super(MainWindow, self).resizeEvent(event)
        # Reposition overlay controls when the main window is resized
        if self.canvas and self.overlayControls:
            self.overlayControls.move(self.canvas.native.width() - self.overlayControls.width() - 20, 20)

    def setupControls(self):

        self.acquire_dock = ControlDock("Acquire Controls", lambda oscope: AcquireControl(oscope), self.oscope, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.acquire_dock)

        self.trigger_dock = ControlDock("Trigger Controls", lambda oscope: TriggerControl(oscope), self.oscope, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.trigger_dock)

        self.timebase_dock = ControlDock("Timebase Controls", lambda oscope: TimebaseControl(oscope), self.oscope, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.timebase_dock)

        self.waveform_dock = ControlDock("Waveform Controls", lambda oscope: WaveformControl(oscope), self.oscope, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.waveform_dock)

        self.wavegen_dock = ControlDock("WaveGen Controls", lambda oscope: WaveGenControl(oscope), self.oscope, self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.wavegen_dock)

        self.channel_control = ChannelControl(self.oscope, self)
        self.channel_container = QWidget()
        self.channel_container_layout = QVBoxLayout(self.channel_container)
        self.channel_container_layout.addWidget(self.channel_control)
        self.channel_dock = QDockWidget("Channel Controls", self)
        self.channel_dock.setWidget(self.channel_container)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.channel_dock)

        # Add this method to your Oscilloscope class in oscilloscope.py
    def wait_for_operation_complete(self, timeout=5):
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.oscope.query_operation_complete().strip() == '1':
                return True
            time.sleep(0.1)
        raise TimeoutError("Operation did not complete in time.")

    def toggle_continuous_fetch(self, checked):
        if checked:
            self.start_continuous_fetch()
            self.runButton.setText("Stop Continuous")
        else:
            self.stop_continuous_fetch()
            self.runButton.setText("Run Continuous")

    def start_continuous_fetch(self):
        self.fetch_thread.set_single_fetch_mode(False)
        self.oscope.run()
        self.continuous_fetch = True
        if not self.fetch_thread.isRunning():
            self.fetch_thread.start()

    def stop_continuous_fetch(self):
        self.oscope.stop()
        self.continuous_fetch = False

    def single_fetch(self):
        if self.continuous_fetch:
            self.stop_continuous_fetch()
        self.fetch_thread.set_single_fetch_mode(True)
        if not self.fetch_thread.isRunning():
            self.fetch_thread.start()
        else:
            self.fetch_thread.fetch_data()

    def get_continuous_fetch(self):
        return self.continuous_fetch
    
    def on_data_fetched(self, trace_data_dict):
        self.canvas.update_multiple_traces(trace_data_dict)

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
        return select_instrument()
    
    selected_key = list(unique_instruments.keys())[selected_index]
    return unique_instruments[selected_key]

if __name__ == '__main__':

    resource_string = select_instrument("TCPIP?*::INSTR")
    oscope = Oscilloscope(resource_string)
    try:
        oscope.open()
        print(f"Successfully connected to {oscope.identity().strip()}")

    except:
        pass

    oscope.reset()
    oscope.trigger.mode = 'edge'
    oscope.trigger.source = "CHANnel1"
    oscope.trigger.level = 2.0
    oscope.trigger.slope = 'positive'

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Fusion style works well with custom palettes

    dark_palette = QPalette()

    # Configure the dark palette
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
