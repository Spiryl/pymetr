from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QComboBox, QCheckBox, QFormLayout
from PySide6.QtWidgets import QMainWindow, QTabWidget, QApplication
from PySide6.QtCore import Qt
import logging
from pymetr.instrument import Instrument 
from scratch.dark_style import get_dark_palette 
from pymetr.instruments.dsox1204g import Acquire, Channel, Timebase, Trigger, WaveGen, Waveform

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

        # 'mode' Control Widget
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([item.name for item in Acquire.None])
        form_layout.addRow(QLabel('   Mode   '), self.mode_combo)

        # 'type' Control Widget
        self.type_combo = QComboBox()
        self.type_combo.addItems([item.name for item in Acquire.None])
        form_layout.addRow(QLabel('   Type   '), self.type_combo)

        # 'sample_rate' Control Widget
        self.sample_rate_edit = QLineEdit()

        form_layout.addRow(QLabel('   Sample_rate   '), self.sample_rate_edit)

        # 'count' Control Widget
        self.count_edit = QLineEdit()

        form_layout.addRow(QLabel('   Count   '), self.count_edit)

        self.connect_signals()

    def connect_signals(self):
        self.mode_combo.currentIndexChanged.connect(lambda: self.update_mode(self.mode_combo.currentText()))
        self.type_combo.currentIndexChanged.connect(lambda: self.update_type(self.type_combo.currentText()))
        self.sample_rate_edit.editingFinished.connect(lambda: self.update_sample_rate(self.sample_rate_edit.text()))
        self.count_edit.editingFinished.connect(lambda: self.update_count(self.count_edit.text()))

    def update_mode(self, value):
        self.instrument.acquire.mode = value

    def update_type(self, value):
        self.instrument.acquire.type = value

    def update_sample_rate(self, value):
        self.instrument.acquire.sample_rate = value

    def update_count(self, value):
        self.instrument.acquire.count = value

    def sync(self):
        # Sync UI with current instrument state
        current_value = str(self.instrument.acquire.mode)

        index = self.mode_combo.findText(current_value, Qt.MatchContains)
        self.mode_combo.setCurrentIndex(index)
        current_value = str(self.instrument.acquire.type)

        index = self.type_combo.findText(current_value, Qt.MatchContains)
        self.type_combo.setCurrentIndex(index)
        current_text = str(self.instrument.acquire.sample_rate)

        self.sample_rate_edit.setText(current_text)
        current_text = str(self.instrument.acquire.count)

        self.count_edit.setText(current_text)

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

        # 'coupling' Control Widget
        self.coupling_combo = QComboBox()
        self.coupling_combo.addItems([item.name for item in Channel.None])
        form_layout.addRow(QLabel('   Coupling   '), self.coupling_combo)

        # 'display' Control Widget
        self.display_check = QCheckBox()
        self.display_check.setCheckable(True)
        form_layout.addRow(QLabel('   Display   '), self.display_check)

        # 'scale' Control Widget
        self.scale_edit = QLineEdit()

        form_layout.addRow(QLabel('   Scale   '), self.scale_edit)

        # 'offset' Control Widget
        self.offset_edit = QLineEdit()

        form_layout.addRow(QLabel('   Offset   '), self.offset_edit)

        # 'probe_attenuation' Control Widget
        self.probe_attenuation_edit = QLineEdit()

        form_layout.addRow(QLabel('   Probe_attenuation   '), self.probe_attenuation_edit)

        self.connect_signals()

    def connect_signals(self):
        self.coupling_combo.currentIndexChanged.connect(lambda: self.update_coupling(self.coupling_combo.currentText()))
        self.display_check.stateChanged.connect(lambda state: self.update_display(state))
        self.scale_edit.editingFinished.connect(lambda: self.update_scale(self.scale_edit.text()))
        self.offset_edit.editingFinished.connect(lambda: self.update_offset(self.offset_edit.text()))
        self.probe_attenuation_edit.editingFinished.connect(lambda: self.update_probe_attenuation(self.probe_attenuation_edit.text()))

    def update_coupling(self, value):
        self.instrument.channel.coupling = value

    def update_display(self, value):
        converted_value = '1' if value else '0'
        self.instrument.channel.display = converted_value

    def update_scale(self, value):
        self.instrument.channel.scale = value

    def update_offset(self, value):
        self.instrument.channel.offset = value

    def update_probe_attenuation(self, value):
        self.instrument.channel.probe_attenuation = value

    def sync(self):
        # Sync UI with current instrument state
        current_value = str(self.instrument.channel.coupling)

        index = self.coupling_combo.findText(current_value, Qt.MatchContains)
        self.coupling_combo.setCurrentIndex(index)
        current_state = self.instrument.channel.display == '1'

        self.display_check.setChecked(current_state)
        current_text = str(self.instrument.channel.scale)

        self.scale_edit.setText(current_text)
        current_text = str(self.instrument.channel.offset)

        self.offset_edit.setText(current_text)
        current_text = str(self.instrument.channel.probe_attenuation)

        self.probe_attenuation_edit.setText(current_text)

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

        # 'mode' Control Widget
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([item.name for item in Timebase.None])
        form_layout.addRow(QLabel('   Mode   '), self.mode_combo)

        # 'reference' Control Widget
        self.reference_combo = QComboBox()
        self.reference_combo.addItems([item.name for item in Timebase.None])
        form_layout.addRow(QLabel('   Reference   '), self.reference_combo)

        # 'scale' Control Widget
        self.scale_edit = QLineEdit()

        form_layout.addRow(QLabel('   Scale   '), self.scale_edit)

        # 'position' Control Widget
        self.position_edit = QLineEdit()

        form_layout.addRow(QLabel('   Position   '), self.position_edit)

        # 'range' Control Widget
        self.range_edit = QLineEdit()

        form_layout.addRow(QLabel('   Range   '), self.range_edit)

        self.connect_signals()

    def connect_signals(self):
        self.mode_combo.currentIndexChanged.connect(lambda: self.update_mode(self.mode_combo.currentText()))
        self.reference_combo.currentIndexChanged.connect(lambda: self.update_reference(self.reference_combo.currentText()))
        self.scale_edit.editingFinished.connect(lambda: self.update_scale(self.scale_edit.text()))
        self.position_edit.editingFinished.connect(lambda: self.update_position(self.position_edit.text()))
        self.range_edit.editingFinished.connect(lambda: self.update_range(self.range_edit.text()))

    def update_mode(self, value):
        self.instrument.timebase.mode = value

    def update_reference(self, value):
        self.instrument.timebase.reference = value

    def update_scale(self, value):
        self.instrument.timebase.scale = value

    def update_position(self, value):
        self.instrument.timebase.position = value

    def update_range(self, value):
        self.instrument.timebase.range = value

    def sync(self):
        # Sync UI with current instrument state
        current_value = str(self.instrument.timebase.mode)

        index = self.mode_combo.findText(current_value, Qt.MatchContains)
        self.mode_combo.setCurrentIndex(index)
        current_value = str(self.instrument.timebase.reference)

        index = self.reference_combo.findText(current_value, Qt.MatchContains)
        self.reference_combo.setCurrentIndex(index)
        current_text = str(self.instrument.timebase.scale)

        self.scale_edit.setText(current_text)
        current_text = str(self.instrument.timebase.position)

        self.position_edit.setText(current_text)
        current_text = str(self.instrument.timebase.range)

        self.range_edit.setText(current_text)

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

        # 'mode' Control Widget
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([item.name for item in Trigger.None])
        form_layout.addRow(QLabel('   Mode   '), self.mode_combo)

        # 'source' Control Widget
        self.source_combo = QComboBox()
        self.source_combo.addItems([item.name for item in Trigger.None])
        form_layout.addRow(QLabel('   Source   '), self.source_combo)

        # 'slope' Control Widget
        self.slope_combo = QComboBox()
        self.slope_combo.addItems([item.name for item in Trigger.None])
        form_layout.addRow(QLabel('   Slope   '), self.slope_combo)

        # 'sweep' Control Widget
        self.sweep_combo = QComboBox()
        self.sweep_combo.addItems([item.name for item in Trigger.None])
        form_layout.addRow(QLabel('   Sweep   '), self.sweep_combo)

        # 'level' Control Widget
        self.level_edit = QLineEdit()

        form_layout.addRow(QLabel('   Level   '), self.level_edit)

        self.connect_signals()

    def connect_signals(self):
        self.mode_combo.currentIndexChanged.connect(lambda: self.update_mode(self.mode_combo.currentText()))
        self.source_combo.currentIndexChanged.connect(lambda: self.update_source(self.source_combo.currentText()))
        self.slope_combo.currentIndexChanged.connect(lambda: self.update_slope(self.slope_combo.currentText()))
        self.sweep_combo.currentIndexChanged.connect(lambda: self.update_sweep(self.sweep_combo.currentText()))
        self.level_edit.editingFinished.connect(lambda: self.update_level(self.level_edit.text()))

    def update_mode(self, value):
        self.instrument.trigger.mode = value

    def update_source(self, value):
        self.instrument.trigger.source = value

    def update_slope(self, value):
        self.instrument.trigger.slope = value

    def update_sweep(self, value):
        self.instrument.trigger.sweep = value

    def update_level(self, value):
        self.instrument.trigger.level = value

    def sync(self):
        # Sync UI with current instrument state
        current_value = str(self.instrument.trigger.mode)

        index = self.mode_combo.findText(current_value, Qt.MatchContains)
        self.mode_combo.setCurrentIndex(index)
        current_value = str(self.instrument.trigger.source)

        index = self.source_combo.findText(current_value, Qt.MatchContains)
        self.source_combo.setCurrentIndex(index)
        current_value = str(self.instrument.trigger.slope)

        index = self.slope_combo.findText(current_value, Qt.MatchContains)
        self.slope_combo.setCurrentIndex(index)
        current_value = str(self.instrument.trigger.sweep)

        index = self.sweep_combo.findText(current_value, Qt.MatchContains)
        self.sweep_combo.setCurrentIndex(index)
        current_text = str(self.instrument.trigger.level)

        self.level_edit.setText(current_text)

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

        # 'function' Control Widget
        self.function_combo = QComboBox()
        self.function_combo.addItems([item.name for item in WaveGen.None])
        form_layout.addRow(QLabel('   Function   '), self.function_combo)

        # 'output' Control Widget
        self.output_check = QCheckBox()
        self.output_check.setCheckable(True)
        form_layout.addRow(QLabel('   Output   '), self.output_check)

        # 'frequency' Control Widget
        self.frequency_edit = QLineEdit()

        form_layout.addRow(QLabel('   Frequency   '), self.frequency_edit)

        # 'amplitude' Control Widget
        self.amplitude_edit = QLineEdit()

        form_layout.addRow(QLabel('   Amplitude   '), self.amplitude_edit)

        # 'offset' Control Widget
        self.offset_edit = QLineEdit()

        form_layout.addRow(QLabel('   Offset   '), self.offset_edit)

        self.connect_signals()

    def connect_signals(self):
        self.function_combo.currentIndexChanged.connect(lambda: self.update_function(self.function_combo.currentText()))
        self.output_check.stateChanged.connect(lambda state: self.update_output(state))
        self.frequency_edit.editingFinished.connect(lambda: self.update_frequency(self.frequency_edit.text()))
        self.amplitude_edit.editingFinished.connect(lambda: self.update_amplitude(self.amplitude_edit.text()))
        self.offset_edit.editingFinished.connect(lambda: self.update_offset(self.offset_edit.text()))

    def update_function(self, value):
        self.instrument.wavegen.function = value

    def update_output(self, value):
        converted_value = '1' if value else '0'
        self.instrument.wavegen.output = converted_value

    def update_frequency(self, value):
        self.instrument.wavegen.frequency = value

    def update_amplitude(self, value):
        self.instrument.wavegen.amplitude = value

    def update_offset(self, value):
        self.instrument.wavegen.offset = value

    def sync(self):
        # Sync UI with current instrument state
        current_value = str(self.instrument.wavegen.function)

        index = self.function_combo.findText(current_value, Qt.MatchContains)
        self.function_combo.setCurrentIndex(index)
        current_state = self.instrument.wavegen.output == '1'

        self.output_check.setChecked(current_state)
        current_text = str(self.instrument.wavegen.frequency)

        self.frequency_edit.setText(current_text)
        current_text = str(self.instrument.wavegen.amplitude)

        self.amplitude_edit.setText(current_text)
        current_text = str(self.instrument.wavegen.offset)

        self.offset_edit.setText(current_text)

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

        # 'source' Control Widget
        self.source_combo = QComboBox()
        self.source_combo.addItems([item.name for item in Waveform.None])
        form_layout.addRow(QLabel('   Source   '), self.source_combo)

        # 'format' Control Widget
        self.format_combo = QComboBox()
        self.format_combo.addItems([item.name for item in Waveform.None])
        form_layout.addRow(QLabel('   Format   '), self.format_combo)

        # 'points_mode' Control Widget
        self.points_mode_combo = QComboBox()
        self.points_mode_combo.addItems([item.name for item in Waveform.None])
        form_layout.addRow(QLabel('   Points_mode   '), self.points_mode_combo)

        # 'unsigned' Control Widget
        self.unsigned_check = QCheckBox()
        self.unsigned_check.setCheckable(True)
        form_layout.addRow(QLabel('   Unsigned   '), self.unsigned_check)

        # 'points' Control Widget
        self.points_edit = QLineEdit()

        form_layout.addRow(QLabel('   Points   '), self.points_edit)

        self.connect_signals()

    def connect_signals(self):
        self.source_combo.currentIndexChanged.connect(lambda: self.update_source(self.source_combo.currentText()))
        self.format_combo.currentIndexChanged.connect(lambda: self.update_format(self.format_combo.currentText()))
        self.points_mode_combo.currentIndexChanged.connect(lambda: self.update_points_mode(self.points_mode_combo.currentText()))
        self.unsigned_check.stateChanged.connect(lambda state: self.update_unsigned(state))
        self.points_edit.editingFinished.connect(lambda: self.update_points(self.points_edit.text()))

    def update_source(self, value):
        self.instrument.waveform.source = value

    def update_format(self, value):
        self.instrument.waveform.format = value

    def update_points_mode(self, value):
        self.instrument.waveform.points_mode = value

    def update_unsigned(self, value):
        converted_value = '1' if value else '0'
        self.instrument.waveform.unsigned = converted_value

    def update_points(self, value):
        self.instrument.waveform.points = value

    def sync(self):
        # Sync UI with current instrument state
        current_value = str(self.instrument.waveform.source)

        index = self.source_combo.findText(current_value, Qt.MatchContains)
        self.source_combo.setCurrentIndex(index)
        current_value = str(self.instrument.waveform.format)

        index = self.format_combo.findText(current_value, Qt.MatchContains)
        self.format_combo.setCurrentIndex(index)
        current_value = str(self.instrument.waveform.points_mode)

        index = self.points_mode_combo.findText(current_value, Qt.MatchContains)
        self.points_mode_combo.setCurrentIndex(index)
        current_state = self.instrument.waveform.unsigned == '1'

        self.unsigned_check.setChecked(current_state)
        current_text = str(self.instrument.waveform.points)

        self.points_edit.setText(current_text)

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
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    app = QApplication([])
    dark_palette = get_dark_palette()
    app.setStyle("Fusion")
    app.setPalette(dark_palette)
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
