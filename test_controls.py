from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QComboBox, QFormLayout
from PySide6.QtWidgets import QMainWindow, QTabWidget, QApplication

from PySide6.QtCore import Qt
import logging
from pymetr.instrument import Instrument 
from pymetr.oscilloscope_subsystems import Acquire, Channel, Timebase, Trigger, WaveGen, Waveform

class AcquireControl(QWidget):
    def __init__(self, instrument, parent=None):
        super().__init__(parent)
        self.instrument = instrument
        self.init_ui()
        self.sync()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        # Acquire.mode control widget
        self.mode_combobox = QComboBox()
        self.mode_combobox.addItems([item.name for item in Acquire.Modes])
        form_layout.addRow(QLabel('Mode'), self.mode_combobox)

        # Acquire.type control widget
        self.type_combobox = QComboBox()
        self.type_combobox.addItems([item.name for item in Acquire.Types])
        form_layout.addRow(QLabel('Type'), self.type_combobox)

        # Acquire.sample_rate control widget
        self.sample_rate_field = QLineEdit()
        form_layout.addRow(QLabel('Sample_rate'), self.sample_rate_field)

        # Acquire.count control widget
        self.count_field = QLineEdit()
        form_layout.addRow(QLabel('Count'), self.count_field)
        self.connect_signals()

    def connect_signals(self):
        self.mode_combobox.currentIndexChanged.connect(self.update_mode)
        self.type_combobox.currentIndexChanged.connect(self.update_type)
        self.sample_rate_field.editingFinished.connect(self.update_sample_rate)
        self.count_field.editingFinished.connect(self.update_count)

    def update_mode(self):
        self.instrument.acquire.mode = self.mode_combobox.currentText()

    def update_type(self):
        self.instrument.acquire.type = self.type_combobox.currentText()

    def update_sample_rate(self):
        self.instrument.acquire.sample_rate = self.sample_rate_field.text()

    def update_count(self):
        self.instrument.acquire.count = self.count_field.text()

    def sync(self):
        # Sync UI with current instrument state
        self.mode_combobox.findText(str(self.instrument.acquire.mode), Qt.MatchContains)
        self.type_combobox.findText(str(self.instrument.acquire.type), Qt.MatchContains)
        self.sample_rate_field.setText(str(self.instrument.acquire.sample_rate))
        self.count_field.setText(str(self.instrument.acquire.count))

class ChannelControl(QWidget):
    def __init__(self, instrument, parent=None):
        super().__init__(parent)
        self.instrument = instrument
        self.init_ui()
        self.sync()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        # Channel.display control widget
        self.display_combobox = QComboBox()
        self.display_combobox.addItems([item.name for item in Channel.Displays])
        form_layout.addRow(QLabel('Display'), self.display_combobox)

        # Channel.scale control widget
        self.scale_field = QLineEdit()
        form_layout.addRow(QLabel('Scale'), self.scale_field)

        # Channel.offset control widget
        self.offset_field = QLineEdit()
        form_layout.addRow(QLabel('Offset'), self.offset_field)

        # Channel.coupling control widget
        self.coupling_combobox = QComboBox()
        self.coupling_combobox.addItems([item.name for item in Channel.Couplings])
        form_layout.addRow(QLabel('Coupling'), self.coupling_combobox)

        # Channel.probe_attenuation control widget
        self.probe_attenuation_field = QLineEdit()
        form_layout.addRow(QLabel('Probe_attenuation'), self.probe_attenuation_field)
        self.connect_signals()

    def connect_signals(self):
        self.display_combobox.currentIndexChanged.connect(self.update_display)
        self.scale_field.editingFinished.connect(self.update_scale)
        self.offset_field.editingFinished.connect(self.update_offset)
        self.coupling_combobox.currentIndexChanged.connect(self.update_coupling)
        self.probe_attenuation_field.editingFinished.connect(self.update_probe_attenuation)

    def update_display(self):
        self.instrument.channel.display = self.display_combobox.currentText()

    def update_scale(self):
        self.instrument.channel.scale = self.scale_field.text()

    def update_offset(self):
        self.instrument.channel.offset = self.offset_field.text()

    def update_coupling(self):
        self.instrument.channel.coupling = self.coupling_combobox.currentText()

    def update_probe_attenuation(self):
        self.instrument.channel.probe_attenuation = self.probe_attenuation_field.text()

    def sync(self):
        # Sync UI with current instrument state
        self.display_combobox.findText(str(self.instrument.channel.display), Qt.MatchContains)
        self.scale_field.setText(str(self.instrument.channel.scale))
        self.offset_field.setText(str(self.instrument.channel.offset))
        self.coupling_combobox.findText(str(self.instrument.channel.coupling), Qt.MatchContains)
        self.probe_attenuation_field.setText(str(self.instrument.channel.probe_attenuation))

class TimebaseControl(QWidget):
    def __init__(self, instrument, parent=None):
        super().__init__(parent)
        self.instrument = instrument
        self.init_ui()
        self.sync()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        # Timebase.mode control widget
        self.mode_combobox = QComboBox()
        self.mode_combobox.addItems([item.name for item in Timebase.Modes])
        form_layout.addRow(QLabel('Mode'), self.mode_combobox)

        # Timebase.reference control widget
        self.reference_combobox = QComboBox()
        self.reference_combobox.addItems([item.name for item in Timebase.References])
        form_layout.addRow(QLabel('Reference'), self.reference_combobox)

        # Timebase.scale control widget
        self.scale_field = QLineEdit()
        form_layout.addRow(QLabel('Scale'), self.scale_field)

        # Timebase.position control widget
        self.position_field = QLineEdit()
        form_layout.addRow(QLabel('Position'), self.position_field)

        # Timebase.range control widget
        self.range_field = QLineEdit()
        form_layout.addRow(QLabel('Range'), self.range_field)
        self.connect_signals()

    def connect_signals(self):
        self.mode_combobox.currentIndexChanged.connect(self.update_mode)
        self.reference_combobox.currentIndexChanged.connect(self.update_reference)
        self.scale_field.editingFinished.connect(self.update_scale)
        self.position_field.editingFinished.connect(self.update_position)
        self.range_field.editingFinished.connect(self.update_range)

    def update_mode(self):
        self.instrument.timebase.mode = self.mode_combobox.currentText()

    def update_reference(self):
        self.instrument.timebase.reference = self.reference_combobox.currentText()

    def update_scale(self):
        self.instrument.timebase.scale = self.scale_field.text()

    def update_position(self):
        self.instrument.timebase.position = self.position_field.text()

    def update_range(self):
        self.instrument.timebase.range = self.range_field.text()

    def sync(self):
        # Sync UI with current instrument state
        self.mode_combobox.findText(str(self.instrument.timebase.mode), Qt.MatchContains)
        self.reference_combobox.findText(str(self.instrument.timebase.reference), Qt.MatchContains)
        self.scale_field.setText(str(self.instrument.timebase.scale))
        self.position_field.setText(str(self.instrument.timebase.position))
        self.range_field.setText(str(self.instrument.timebase.range))

class TriggerControl(QWidget):
    def __init__(self, instrument, parent=None):
        super().__init__(parent)
        self.instrument = instrument
        self.init_ui()
        self.sync()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        # Trigger.mode control widget
        self.mode_combobox = QComboBox()
        self.mode_combobox.addItems([item.name for item in Trigger.Modes])
        form_layout.addRow(QLabel('Mode'), self.mode_combobox)

        # Trigger.source control widget
        self.source_combobox = QComboBox()
        self.source_combobox.addItems([item.name for item in Trigger.Sources])
        form_layout.addRow(QLabel('Source'), self.source_combobox)

        # Trigger.level control widget
        self.level_field = QLineEdit()
        form_layout.addRow(QLabel('Level'), self.level_field)

        # Trigger.slope control widget
        self.slope_combobox = QComboBox()
        self.slope_combobox.addItems([item.name for item in Trigger.Slopes])
        form_layout.addRow(QLabel('Slope'), self.slope_combobox)

        # Trigger.sweep control widget
        self.sweep_combobox = QComboBox()
        self.sweep_combobox.addItems([item.name for item in Trigger.Sweeps])
        form_layout.addRow(QLabel('Sweep'), self.sweep_combobox)
        self.connect_signals()

    def connect_signals(self):
        self.mode_combobox.currentIndexChanged.connect(self.update_mode)
        self.source_combobox.currentIndexChanged.connect(self.update_source)
        self.level_field.editingFinished.connect(self.update_level)
        self.slope_combobox.currentIndexChanged.connect(self.update_slope)
        self.sweep_combobox.currentIndexChanged.connect(self.update_sweep)

    def update_mode(self):
        self.instrument.trigger.mode = self.mode_combobox.currentText()

    def update_source(self):
        self.instrument.trigger.source = self.source_combobox.currentText()

    def update_level(self):
        self.instrument.trigger.level = self.level_field.text()

    def update_slope(self):
        self.instrument.trigger.slope = self.slope_combobox.currentText()

    def update_sweep(self):
        self.instrument.trigger.sweep = self.sweep_combobox.currentText()

    def sync(self):
        # Sync UI with current instrument state
        self.mode_combobox.findText(str(self.instrument.trigger.mode), Qt.MatchContains)
        self.source_combobox.findText(str(self.instrument.trigger.source), Qt.MatchContains)
        self.level_field.setText(str(self.instrument.trigger.level))
        self.slope_combobox.findText(str(self.instrument.trigger.slope), Qt.MatchContains)
        self.sweep_combobox.findText(str(self.instrument.trigger.sweep), Qt.MatchContains)

class WaveGenControl(QWidget):
    def __init__(self, instrument, parent=None):
        super().__init__(parent)
        self.instrument = instrument
        self.init_ui()
        self.sync()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        # WaveGen.function control widget
        self.function_combobox = QComboBox()
        self.function_combobox.addItems([item.name for item in WaveGen.Functions])
        form_layout.addRow(QLabel('Function'), self.function_combobox)

        # WaveGen.frequency control widget
        self.frequency_field = QLineEdit()
        form_layout.addRow(QLabel('Frequency'), self.frequency_field)

        # WaveGen.amplitude control widget
        self.amplitude_field = QLineEdit()
        form_layout.addRow(QLabel('Amplitude'), self.amplitude_field)

        # WaveGen.output control widget
        self.output_combobox = QComboBox()
        self.output_combobox.addItems([item.name for item in WaveGen.Outputs])
        form_layout.addRow(QLabel('Output'), self.output_combobox)

        # WaveGen.offset control widget
        self.offset_field = QLineEdit()
        form_layout.addRow(QLabel('Offset'), self.offset_field)
        self.connect_signals()

    def connect_signals(self):
        self.function_combobox.currentIndexChanged.connect(self.update_function)
        self.frequency_field.editingFinished.connect(self.update_frequency)
        self.amplitude_field.editingFinished.connect(self.update_amplitude)
        self.output_combobox.currentIndexChanged.connect(self.update_output)
        self.offset_field.editingFinished.connect(self.update_offset)

    def update_function(self):
        self.instrument.wavegen.function = self.function_combobox.currentText()

    def update_frequency(self):
        self.instrument.wavegen.frequency = self.frequency_field.text()

    def update_amplitude(self):
        self.instrument.wavegen.amplitude = self.amplitude_field.text()

    def update_output(self):
        self.instrument.wavegen.output = self.output_combobox.currentText()

    def update_offset(self):
        self.instrument.wavegen.offset = self.offset_field.text()

    def sync(self):
        # Sync UI with current instrument state
        self.function_combobox.findText(str(self.instrument.wavegen.function), Qt.MatchContains)
        self.frequency_field.setText(str(self.instrument.wavegen.frequency))
        self.amplitude_field.setText(str(self.instrument.wavegen.amplitude))
        self.output_combobox.findText(str(self.instrument.wavegen.output), Qt.MatchContains)
        self.offset_field.setText(str(self.instrument.wavegen.offset))

class WaveformControl(QWidget):
    def __init__(self, instrument, parent=None):
        super().__init__(parent)
        self.instrument = instrument
        self.init_ui()
        self.sync()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        # Waveform.source control widget
        self.source_combobox = QComboBox()
        self.source_combobox.addItems([item.name for item in Waveform.Sources])
        form_layout.addRow(QLabel('Source'), self.source_combobox)

        # Waveform.format control widget
        self.format_combobox = QComboBox()
        self.format_combobox.addItems([item.name for item in Waveform.Formats])
        form_layout.addRow(QLabel('Format'), self.format_combobox)

        # Waveform.points_mode control widget
        self.points_mode_combobox = QComboBox()
        self.points_mode_combobox.addItems([item.name for item in Waveform.Points_modes])
        form_layout.addRow(QLabel('Points_mode'), self.points_mode_combobox)

        # Waveform.points control widget
        self.points_field = QLineEdit()
        form_layout.addRow(QLabel('Points'), self.points_field)

        # Waveform.preamble control widget
        self.preamble_field = QLineEdit()
        form_layout.addRow(QLabel('Preamble'), self.preamble_field)

        # Waveform.unsigned control widget
        self.unsigned_field = QLineEdit()
        form_layout.addRow(QLabel('Unsigned'), self.unsigned_field)
        self.connect_signals()

    def connect_signals(self):
        self.source_combobox.currentIndexChanged.connect(self.update_source)
        self.format_combobox.currentIndexChanged.connect(self.update_format)
        self.points_mode_combobox.currentIndexChanged.connect(self.update_points_mode)
        self.points_field.editingFinished.connect(self.update_points)
        self.preamble_field.editingFinished.connect(self.update_preamble)
        self.unsigned_field.editingFinished.connect(self.update_unsigned)

    def update_source(self):
        self.instrument.waveform.source = self.source_combobox.currentText()

    def update_format(self):
        self.instrument.waveform.format = self.format_combobox.currentText()

    def update_points_mode(self):
        self.instrument.waveform.points_mode = self.points_mode_combobox.currentText()

    def update_points(self):
        self.instrument.waveform.points = self.points_field.text()

    def update_preamble(self):
        self.instrument.waveform.preamble = self.preamble_field.text()

    def update_unsigned(self):
        self.instrument.waveform.unsigned = self.unsigned_field.text()

    def sync(self):
        # Sync UI with current instrument state
        self.source_combobox.findText(str(self.instrument.waveform.source), Qt.MatchContains)
        self.format_combobox.findText(str(self.instrument.waveform.format), Qt.MatchContains)
        self.points_mode_combobox.findText(str(self.instrument.waveform.points_mode), Qt.MatchContains)
        self.points_field.setText(str(self.instrument.waveform.points))
        self.preamble_field.setText(str(self.instrument.waveform.preamble))
        self.unsigned_field.setText(str(self.instrument.waveform.unsigned))

class MyInstrument(Instrument):
    def __init__(self, resource_string):
        super().__init__(resource_string)
        self.acquire = Acquire(self)
        self.channel = Channel(self)
        self.timebase = Timebase(self)
        self.trigger = Trigger(self)
        self.wavegen = WaveGen(self)
        self.waveform = Waveform(self)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    app = QApplication([])
    main_win = QMainWindow()
    tab_widget = QTabWidget()
    main_win.setCentralWidget(tab_widget)
    resource_string = Instrument.select_instrument('TCPIP?*::INSTR')
    instr = MyInstrument(resource_string)
    instr.open()
    acquire_tab = AcquireControl(instr)
    tab_widget.addTab(acquire_tab, "Acquire")
    channel_tab = ChannelControl(instr)
    tab_widget.addTab(channel_tab, "Channel")
    timebase_tab = TimebaseControl(instr)
    tab_widget.addTab(timebase_tab, "Timebase")
    trigger_tab = TriggerControl(instr)
    tab_widget.addTab(trigger_tab, "Trigger")
    wavegen_tab = WaveGenControl(instr)
    tab_widget.addTab(wavegen_tab, "WaveGen")
    waveform_tab = WaveformControl(instr)
    tab_widget.addTab(waveform_tab, "Waveform")
    main_win.show()
    app.exec()
