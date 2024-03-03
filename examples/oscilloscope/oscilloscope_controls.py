from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QDockWidget, QTabWidget, QWidget, QCheckBox, QComboBox, QLineEdit, QLabel,QPushButton, QHBoxLayout, QColorDialog)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QDockWidget, QWidget, QPushButton, QDial, QLabel, QHBoxLayout, QColorDialog, QSlider, QGroupBox, QSizePolicy)
from PySide6.QtGui import QPalette, QColor
from utilities import si_str_to_float

class InstrumentSubsystemControl(QWidget):
    """
    Creates a graphical user interface control linked to a specific property of an instrument subsystem.

    :param subsystem: The subsystem to which this control is linked.
    :type subsystem: InstrumentSubsystem
    :param property_name: The name of the property in the subsystem this control manipulates.
    :type property_name: str
    :param control_type: The type of control ('combo', 'line_edit', 'checkbox', 'slider', 'dial').
    :type control_type: str
    :param label_text: The text label for the control.
    :type label_text: str
    :param options: The list of options for a combo box control, defaults to None.
    :type options: list, optional
    :param ranges: The min and max range for slider/dial controls, defaults to None.
    :type ranges: tuple, optional
    :param parent: The parent widget, defaults to None.
    :type parent: QWidget, optional
    """
    def __init__(self, subsystem, property_name, control_type, label_text, options=None, ranges=None, parent=None):
        super().__init__(parent=parent)
        self.subsystem = subsystem
        self.property_name = property_name
        self.control_type = control_type
        self.options = options  # For combo boxes
        self.ranges = ranges  # For sliders and dials
        self.label = QLabel(label_text)
        self.control = self.construct_control()

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.control)

        self.pull_setting()
        # Adjusting the size policy to allow vertical shrinking
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.widget.setSizePolicy(sizePolicy)

    def construct_control(self):
        if self.control_type == 'combo':
            widget = QComboBox()
            widget.addItems(self.options)
            widget.currentTextChanged.connect(lambda: self.push_setting(widget.currentText()))
        elif self.control_type == 'line_edit':
            widget = QLineEdit()
            widget.editingFinished.connect(lambda: self.push_setting(widget.text()))
        elif self.control_type == 'checkbox':
            widget = QCheckBox()
            widget.stateChanged.connect(lambda state: self.push_setting(state == Qt.Checked))
        elif self.control_type == 'slider':
            widget = QSlider(Qt.Horizontal)
            if self.ranges:
                widget.setMinimum(self.ranges[0])
                widget.setMaximum(self.ranges[1])
            widget.valueChanged.connect(lambda: self.push_setting(widget.value()))
        elif self.control_type == 'dial':
            widget = QDial()
            if self.ranges:
                widget.setMinimum(self.ranges[0])
                widget.setMaximum(self.ranges[1])
            widget.valueChanged.connect(lambda: self.push_setting(widget.value()))
        else:
            raise ValueError("Unsupported control type")
        return widget

    def push_setting(self, value):
        if hasattr(self.subsystem, self.property_name):
            setattr(self.subsystem, self.property_name, value)

    def pull_setting(self):
        if hasattr(self.subsystem, self.property_name):
            value = getattr(self.subsystem, self.property_name)
            if self.control_type in ['combo', 'line_edit']:
                self.control.setText(str(value))
            elif self.control_type == 'checkbox':
                self.control.setChecked(value == 'ON')
            elif self.control_type in ['slider', 'dial']:
                self.control.setValue(int(value))

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

    def update_format(self):
        self.oscope.waveform.format = self.format_combobox.currentText()

    def update_points_mode(self):
        self.oscope.waveform.points_mode = self.points_mode_combobox.currentText()

    def update_num_points(self):
        num_points = int(self.num_points_field.text())
        self.oscope.waveform.num_points = num_points


class WaveGenControl(QWidget):
    def __init__(self, oscope, parent=None):
        super(WaveGenControl, self).__init__(parent)
        self.oscope = oscope
        self.init_ui()
        # self.connect_signals()
        self.sync()  # Ensure sync is called to update UI with initial values

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        # Replace enable checkbox with a QPushButton for output state
        self.output_state_button = QPushButton("Output State: OFF")
        self.output_state_button.clicked.connect(self.toggle_output)
        self.layout.addWidget(self.output_state_button)

        # Frequency controls
        self.frequency_label = QLabel("Frequency:")
        self.frequency_field = QLineEdit()
        self.frequency_field.editingFinished.connect(self.update_frequency)
        self.layout.addWidget(self.frequency_label)
        self.layout.addWidget(self.frequency_field)

        # Waveform type controls
        self.waveform_type_label = QLabel("Waveform Type:")
        self.waveform_type_combobox = QComboBox()
        # Load waveform types from the Function enum, capitalizing the first letter
        self.waveform_type_combobox.addItems([func.name.capitalize() for func in self.oscope.wavegen.Function])
        self.waveform_type_combobox.currentIndexChanged.connect(self.update_waveform_type)
        self.layout.addWidget(self.waveform_type_label)
        self.layout.addWidget(self.waveform_type_combobox)

        # Amplitude controls
        self.amplitude_label = QLabel("Amplitude:")
        self.amplitude_field = QLineEdit()
        self.layout.addWidget(self.amplitude_field)  # Ensure the field is added to the layout
        self.amplitude_field.editingFinished.connect(self.update_amplitude)
        self.layout.addWidget(self.amplitude_label)

    def sync(self):
        # Sync the GUI with the current state of the oscilloscope's waveform generator
        output_state = self.oscope.wavegen.output
        # Adjusting for the instrument's response format
        if output_state in ['ON', '1']:
            self.output_state_button.setText("Output State: ON")
            self.output_state_button.setStyleSheet("background-color: green;")
        else:
            self.output_state_button.setText("Output State: OFF")
            self.output_state_button.setStyleSheet("")

        self.frequency_field.setText(str(self.oscope.wavegen.frequency))
        # Ensure capitalization matches the enum's name format
        waveform_function = self.oscope.wavegen.function.capitalize()
        self.waveform_type_combobox.setCurrentText(waveform_function)
        self.amplitude_field.setText(str(self.oscope.wavegen.amplitude))

    def update_output_button(self, is_on):
        if is_on:
            self.output_state_button.setText("Output State: ON")
            self.output_state_button.setStyleSheet("background-color: green;")
        else:
            self.output_state_button.setText("Output State: OFF")
            self.output_state_button.setStyleSheet("")

    def toggle_output(self):
        # Toggle the output state and update the button
        current_state = self.oscope.wavegen.output
        new_state = 'OFF' if current_state == 'ON' else 'ON'
        self.oscope.wavegen.output = new_state
        self.update_output_button(new_state == 'ON')

    def update_frequency(self):
        # Update frequency based on the field's value
        frequency = si_str_to_float(self.frequency_field.text())
        self.oscope.wavegen.frequency = frequency

    def update_waveform_type(self):
        # Update waveform type based on the combobox selection
        waveform_type = self.waveform_type_combobox.currentText().upper()
        self.oscope.wavegen.function = waveform_type

    def update_amplitude(self):
        # Update amplitude based on the field's value
        amplitude = si_str_to_float(self.amplitude_field.text())
        self.oscope.wavegen.amplitude = amplitude

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
        level = si_str_to_float(self.trigger_value_field.text())
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
        rate = si_str_to_float(self.sample_rate_field.text())
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
        scale = si_str_to_float(self.scale_field.text())
        self.oscope.timebase.scale = scale

    def update_position(self):
        position = si_str_to_float(self.position_field.text())
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
