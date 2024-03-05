from PySide6.QtWidgets import (QVBoxLayout, QDockWidget, QTabWidget, QWidget, QCheckBox, QComboBox, QLineEdit, QLabel,QPushButton, QHBoxLayout, QColorDialog)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QPushButton, QDial, QLabel, QHBoxLayout, QColorDialog, QSlider, QGroupBox, QSizePolicy, QFormLayout)
from PySide6.QtGui import QColor
from utilities import si_str_to_float
from pymetr.oscilloscope import Trigger, WaveGen, Waveform, Acquire,  Timebase


class WaveformControl(QWidget):
    def __init__(self, instrument, parent=None):
        super(WaveformControl, self).__init__(parent)
        self.instrument = instrument
        self.init_ui()
        # Assuming connect_signals is intended for connecting UI signals
        self.connect_signals()
        self.sync()  # Ensure sync is called to update UI with initial values

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Form layout for waveform controls
        form_layout = QFormLayout()
        main_layout.addLayout(form_layout)

        # Data Format
        self.format_combobox = QComboBox()
        self.format_combobox.addItems(["BYTE", "WORD", "ASCII"])
        form_layout.addRow("Data Format:", self.format_combobox)

        # Points Mode
        self.points_mode_combobox = QComboBox()
        self.points_mode_combobox.addItems(["NORMAL", "MAXIMUM", "RAW"])
        form_layout.addRow("Points Mode:", self.points_mode_combobox)

        # Number of Points
        self.num_points_field = QLineEdit()
        form_layout.addRow("Number of Points:", self.num_points_field)

    def connect_signals(self):
        self.format_combobox.currentTextChanged.connect(self.update_format)
        self.points_mode_combobox.currentTextChanged.connect(self.update_points_mode)
        self.num_points_field.editingFinished.connect(self.update_num_points)

    def update_format(self):
        # Logic to update the waveform format based on the combobox selection
        self.instrument.waveform.format = self.format_combobox.currentText()

    def update_points_mode(self):
        # Logic to update the points mode based on the combobox selection
        self.instrument.waveform.points_mode = self.points_mode_combobox.currentText()

    def update_num_points(self):
        # Logic to update the number of points based on the field's value
        num_points = int(self.num_points_field.text())
        self.instrument.waveform.num_points = num_points

    def sync(self):
        # Update UI elements with current settings from the oscillinstrument
        self.format_combobox.setCurrentText(self.instrument.waveform.format)
        self.points_mode_combobox.setCurrentText(self.instrument.waveform.points_mode)
        self.num_points_field.setText(str(self.instrument.waveform.num_points))

class WaveGenControl(QWidget):
    def __init__(self, instrument, parent=None):
        super(WaveGenControl, self).__init__(parent)
        self.instrument = instrument
        self.init_ui()
        self.sync()  # Ensure sync is called to update UI with initial values

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Output state button
        self.output_state_button = QPushButton("Output: OFF")
        self.output_state_button.clicked.connect(self.toggle_output)
        main_layout.addWidget(self.output_state_button)

        # Form layout for controls
        form_layout = QFormLayout()
        main_layout.addLayout(form_layout)

        # Waveform type controls
        self.waveform_type_combobox = QComboBox()
        self.waveform_type_combobox.addItems([func.name.capitalize() for func in self.instrument.wavegen.Function])
        self.waveform_type_combobox.currentIndexChanged.connect(self.update_waveform_type)
        form_layout.addRow("Waveform Type:", self.waveform_type_combobox)

        # Frequency controls
        self.frequency_field = QLineEdit()
        self.frequency_field.editingFinished.connect(self.update_frequency)
        form_layout.addRow("Frequency (Hz):", self.frequency_field)

        # Amplitude controls
        self.amplitude_field = QLineEdit()
        self.amplitude_field.editingFinished.connect(self.update_amplitude)
        form_layout.addRow("Amplitude (Vpp):", self.amplitude_field)

        # Offset controls
        self.offset_field = QLineEdit()
        self.offset_field.editingFinished.connect(self.update_offset)
        form_layout.addRow("Offset (V):", self.offset_field)

    def update_output_button(self, is_on):
        if is_on:
            self.output_state_button.setText("Output State: ON")
            self.output_state_button.setStyleSheet("background-color: green;")
        else:
            self.output_state_button.setText("Output State: OFF")
            self.output_state_button.setStyleSheet("")

    def toggle_output(self):
        # Toggle the output state and update the button
        current_state = self.instrument.wavegen.output
        new_state = 'OFF' if current_state == 'ON' else 'ON'
        self.instrument.wavegen.output = new_state
        self.update_output_button(new_state == 'ON')

    def update_frequency(self):
        # Update frequency based on the field's value
        frequency = si_str_to_float(self.frequency_field.text())
        self.instrument.wavegen.frequency = frequency

    def update_waveform_type(self):
        # Update waveform type based on the combobox selection
        waveform_type = self.waveform_type_combobox.currentText().upper()
        self.instrument.wavegen.function = waveform_type

    def update_amplitude(self):
        # Update amplitude based on the field's value
        amplitude = si_str_to_float(self.amplitude_field.text())
        self.instrument.wavegen.amplitude = amplitude

    def update_offset(self):
        # Update offset based on the field's value
        offset = float(self.offset_field.text())  # Convert the input to a float
        self.instrument.wavegen.offset = offset  # Set the new offset value

    def sync(self):
        # Sync the GUI with the current state of the oscillinstrument's waveform generator
        output_state = self.instrument.wavegen.output
        # Adjusting for the instrument's response format
        if output_state in ['ON', '1']:
            self.output_state_button.setText("Output: ON")
            self.output_state_button.setStyleSheet("background-color: purple;")
        else:
            self.output_state_button.setText("Output: OFF")
            self.output_state_button.setStyleSheet("")

        # Ensure capitalization matches the enum's name format
        waveform_function = self.instrument.wavegen.function.capitalize()
        self.waveform_type_combobox.setCurrentText(waveform_function)
        self.frequency_field.setText(str(self.instrument.wavegen.frequency))
        self.amplitude_field.setText(str(self.instrument.wavegen.amplitude))
        self.offset_field.setText(str(self.instrument.wavegen.offset))

class TriggerControl(QWidget):
    def __init__(self, instrument, parent=None):
        super(TriggerControl, self).__init__(parent)
        self.instrument = instrument
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        main_layout.addLayout(form_layout)

        # Source
        self.trigger_source_combobox = QComboBox()
        self.trigger_source_combobox.addItems([source.name for source in Trigger.Source])
        form_layout.addRow(QLabel("Source:"), self.trigger_source_combobox)

        # Edge
        self.trigger_edge_combobox = QComboBox()
        self.trigger_edge_combobox.addItems(["Rising", "Falling"])
        form_layout.addRow(QLabel("Edge:"), self.trigger_edge_combobox)

        # Level
        self.trigger_level_field = QLineEdit()
        form_layout.addRow(QLabel("Level:"), self.trigger_level_field)

        # Mode
        self.trigger_mode_combobox = QComboBox()
        self.trigger_mode_combobox.addItems([mode.name for mode in Trigger.Mode])
        form_layout.addRow(QLabel("Mode:"), self.trigger_mode_combobox)

        # Slope
        self.trigger_slope_combobox = QComboBox()
        self.trigger_slope_combobox.addItems([slope.name for slope in Trigger.Slope])
        form_layout.addRow(QLabel("Slope:"), self.trigger_slope_combobox)


    def connect_signals(self):
        self.trigger_source_combobox.currentIndexChanged.connect(self.update_trigger_source)
        self.trigger_edge_combobox.currentIndexChanged.connect(self.update_trigger_edge)
        self.trigger_level_field.editingFinished.connect(self.update_trigger_level)

    def update_trigger_source(self):
        # Get the current text, replace spaces and make it uppercase to match the enum naming convention
        selected_source_str = self.trigger_source_combobox.currentText().replace(" ", "").upper()
        # Use the enum directly since the __str__ method returns the name
        self.instrument.trigger.source = getattr(self._parent.Source, selected_source_str)

    def update_trigger_edge(self):
        edge = self.trigger_edge_combobox.currentText().lower()
        self.instrument.trigger.slope = edge

    def update_trigger_level(self):
        level = si_str_to_float(self.trigger_level_field.text())
        self.instrument.trigger.level = level

    def sync(self):
        # Use the getters to fetch the current settings from the oscillinstrument
        current_mode = self.instrument.trigger.mode
        current_source = self.instrument.trigger.source
        current_level = self.instrument.trigger.level
        current_slope = self.instrument.trigger.slope

        # Update the combobox and field values to reflect the current settings
        self.trigger_mode_combobox.setCurrentText(current_mode.name)
        self.trigger_source_combobox.setCurrentText(current_source)  # Assuming this returns a string
        self.trigger_level_field.setText(str(current_level))
        self.trigger_slope_combobox.setCurrentText(current_slope.name)


class AcquireControl(QWidget):
    def __init__(self, instrument, parent=None):
        super(AcquireControl, self).__init__(parent)
        self.instrument = instrument
        self.init_ui()
        self.sync() 

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Acquisition Mode
        self.mode_combobox = QComboBox()
        self.mode_combobox.addItems([mode.name for mode in Acquire.Mode])
        self.mode_combobox.currentIndexChanged.connect(self.update_acquisition_mode)
        form_layout.addRow("Acquisition Mode:", self.mode_combobox)
        
        # Sample Rate
        self.sample_rate_field = QLineEdit()
        self.sample_rate_field.editingFinished.connect(self.update_sample_rate)
        form_layout.addRow("Sample Rate (S/s):", self.sample_rate_field)

        main_layout.addLayout(form_layout)

    def update_acquisition_mode(self):
        # Logic to update the acquisition mode based on the combobox selection
        mode = self.mode_combobox.currentText()
        self.instrument.acquire.mode = mode.lower().replace(" ", "_")

    def update_sample_rate(self):
        # Logic to update the sample rate based on the field's value
        rate = si_str_to_float(self.sample_rate_field.text())
        self.instrument.acquire.sample_rate = rate

    def sync(self):
        # Update UI elements with current settings from the oscillinstrument
        self.mode_combobox.setCurrentText(str(self.instrument.acquire.mode))
        self.sample_rate_field.setText(str(self.instrument.acquire.sample_rate))

class TimebaseControl(QWidget):
    def __init__(self, instrument, parent=None):
        super(TimebaseControl, self).__init__(parent)
        self.instrument = instrument
        self.init_ui()
        self.connect_signals()
        self.sync()  # Ensure the UI is updated with initial values from the oscillinstrument

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Timebase Scale
        self.scale_field = QLineEdit()
        form_layout.addRow("Scale (s/div):", self.scale_field)

        # Timebase Position
        self.position_field = QLineEdit()
        form_layout.addRow("Position (s):", self.position_field)

        # Add the form layout to the main layout
        main_layout.addLayout(form_layout)

        # Apply Button (if immediate application is not desired)
        self.apply_button = QPushButton("Apply")
        main_layout.addWidget(self.apply_button)

    def connect_signals(self):
        self.scale_field.editingFinished.connect(self.update_scale)
        self.position_field.editingFinished.connect(self.update_position)
        self.apply_button.clicked.connect(self.apply_changes)

    def update_scale(self):
        # Logic to update the timebase scale based on the field's value
        scale = self.si_str_to_float(self.scale_field.text())
        self.instrument.timebase.scale = scale

    def update_position(self):
        # Logic to update the timebase position based on the field's value
        position = self.si_str_to_float(self.position_field.text())
        self.instrument.timebase.position = position

    def apply_changes(self):
        # Apply changes method, could be used to apply all changes at once if needed
        self.update_scale()
        self.update_position()

    def sync(self):
        # Update UI elements with current settings from the oscillinstrument
        self.scale_field.setText(str(self.instrument.timebase.scale))
        self.position_field.setText(str(self.instrument.timebase.position))

    def sync(self):
        # Update UI elements with the current settings from the instrument object
        self.scale_field.setText(str(self.instrument.timebase.scale))
        self.position_field.setText(str(self.instrument.timebase.position))


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
        self.offset_slider.setMinimum(-70)  # Assuming offset range
        self.offset_slider.setMaximum(70)
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

    def __init__(self, instrument, parent=None):
        super(ChannelControl, self).__init__(parent)
        self.instrument = instrument
        self.layout = QHBoxLayout(self)  # Changed to horizontal layout
        
        # Create a ChannelControlPanel for each channel without passing the color
        for channel_num, channel in self.instrument.channels.items():
            channel_panel = ChannelControlPanel(channel)
            self.layout.addWidget(channel_panel)

class ControlDock(QDockWidget):
    def __init__(self, title, create_control_callback, instrument, parent=None):
        super(ControlDock, self).__init__(title, parent)
        self.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.instrument = instrument  # Store the oscillinstrument reference for use in the controls
        self.main_widget = QWidget()
        self.setWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        # Create the specific control for this dock using the provided callback function
        self.control = create_control_callback(self.instrument)
        self.layout.addWidget(self.control)

        # Add stretch to push everything up
        self.layout.addStretch()
