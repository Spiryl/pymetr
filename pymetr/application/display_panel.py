# --- display_panel.py ---
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QComboBox, QFrame
from PySide6.QtCore import Signal
from pyqtgraph.parametertree import ParameterTree, Parameter

class DisplayPanel(QWidget):
    plotModeChanged = Signal(str)
    traceModeChanged = Signal(str)
    roiPlotToggled = Signal(bool)
    gridToggled = Signal(bool)
    xLogScaleToggled = Signal(bool)
    yLogScaleToggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.params = [
            {'name': 'Plot Settings', 'type': 'group', 'children': [
                {'name': 'Grid', 'type': 'bool', 'value': False},
                {'name': 'X Log Scale', 'type': 'bool', 'value': False},
                {'name': 'Y Log Scale', 'type': 'bool', 'value': False},
            ]},
            {'name': 'Axes Settings', 'type': 'group', 'children': [
                {'name': 'X Axis', 'type': 'group', 'children': [
                    {'name': 'Label', 'type': 'str', 'value': 'X'},
                    {'name': 'Start', 'type': 'float', 'value': 0},
                    {'name': 'Stop', 'type': 'float', 'value': 100},
                ]},
                {'name': 'Y Axis', 'type': 'group', 'children': [
                    {'name': 'Label', 'type': 'str', 'value': 'Y'},
                    {'name': 'Start', 'type': 'float', 'value': 0},
                    {'name': 'Stop', 'type': 'float', 'value': 100},
                ]},
            ]},
            {'name': 'Region Plot Settings', 'type': 'group', 'children': [
                {'name': 'Enable', 'type': 'bool', 'value': False},
            ]},
            {'name': 'Trace Settings', 'type': 'group', 'children': [
                {'name': 'Plot Mode', 'type': 'list', 'limits': ["Add", "Replace"], 'value': "Add"},
                {'name': 'Trace Mode', 'type': 'list', 'limits': ["Group", "Isolate"], 'value': "Group"},
                {'name': 'Anti-aliasing', 'type': 'bool', 'value': True},
                {'name': 'Default Line Thickness', 'type': 'float', 'value': 1.0},
                {'name': 'Default Line Style', 'type': 'list', 'limits': ['Solid', 'Dash', 'Dot', 'Dash-Dot'], 'value': 'Solid'},
            ]},
        ]

        self.parameter_tree = ParameterTree()
        self.parameter = Parameter.create(name='params', type='group', children=self.params)
        self.parameter_tree.setParameters(self.parameter, showTop=False)
        self.layout.addWidget(self.parameter_tree)

        self.connect_signals()

    def connect_signals(self):
        self.parameter.param('Plot Settings', 'Grid').sigValueChanged.connect(
            lambda param, value: self.gridToggled.emit(value)
        )
        self.parameter.param('Plot Settings', 'X Log Scale').sigValueChanged.connect(
            lambda param, value: self.xLogScaleToggled.emit(value)
        )
        self.parameter.param('Plot Settings', 'Y Log Scale').sigValueChanged.connect(
            lambda param, value: self.yLogScaleToggled.emit(value)
        )
        self.parameter.param('Region Plot Settings', 'Enable').sigValueChanged.connect(
            lambda param, value: self.roiPlotToggled.emit(value)
        )
        self.parameter.param('Trace Settings', 'Plot Mode').sigValueChanged.connect(
            lambda param, value: self.plotModeChanged.emit(value)
        )
        self.parameter.param('Trace Settings', 'Trace Mode').sigValueChanged.connect(
            lambda param, value: self.traceModeChanged.emit(value)
        )

class QuickPanel(QWidget):
    plotModeChanged = Signal(str)
    traceModeChanged = Signal(str)
    roiPlotToggled = Signal(bool)
    groupAllClicked = Signal()
    isolateAllClicked = Signal()
    testTraceClicked = Signal()
    clearTracesClicked = Signal()
    addInstrumentClicked = Signal()
    screenshotClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QHBoxLayout(self)

        self.add_instrument_button = QPushButton("Add Instrument")
        self.add_instrument_button.clicked.connect(self.on_add_instrument_clicked)
        self.layout.addWidget(self.add_instrument_button)

        self.layout.addWidget(QFrame(frameShape=QFrame.VLine))

        self.plot_mode_combo_box = QComboBox()
        self.plot_mode_combo_box.addItems(["Add", "Replace"])
        self.plot_mode_combo_box.currentTextChanged.connect(self.on_plot_mode_changed)
        self.layout.addWidget(self.plot_mode_combo_box)

        self.roi_plot_toggle = QPushButton("Region Plot")
        self.roi_plot_toggle.setCheckable(True)
        self.roi_plot_toggle.setChecked(False)
        self.roi_plot_toggle.toggled.connect(self.on_roi_plot_toggled)
        self.layout.addWidget(self.roi_plot_toggle)

        self.screenshot_button = QPushButton("Screenshot")
        self.screenshot_button.clicked.connect(self.on_screenshot_clicked)
        self.layout.addWidget(self.screenshot_button)

        self.layout.addWidget(QFrame(frameShape=QFrame.VLine))

        self.trace_mode_combo_box = QComboBox()
        self.trace_mode_combo_box.addItems(["Group", "Isolate"])
        self.trace_mode_combo_box.currentTextChanged.connect(self.on_trace_mode_changed)
        self.layout.addWidget(self.trace_mode_combo_box)

        self.group_all_button = QPushButton("Group All")
        self.group_all_button.clicked.connect(self.on_group_all_clicked)
        self.layout.addWidget(self.group_all_button)

        self.isolate_all_button = QPushButton("Isolate All")
        self.isolate_all_button.clicked.connect(self.on_isolate_all_clicked)
        self.layout.addWidget(self.isolate_all_button)

        self.test_trace_button = QPushButton("Test Trace")
        self.test_trace_button.clicked.connect(self.on_test_trace_clicked)
        self.layout.addWidget(self.test_trace_button)

        self.clear_traces_button = QPushButton("Clear Traces")
        self.clear_traces_button.clicked.connect(self.on_clear_traces_clicked)
        self.layout.addWidget(self.clear_traces_button)

    def on_add_instrument_clicked(self):
        self.addInstrumentClicked.emit()

    def on_plot_mode_changed(self, plot_mode):
        self.plotModeChanged.emit(plot_mode)

    def on_roi_plot_toggled(self, checked):
        self.roiPlotToggled.emit(checked)

    def on_screenshot_clicked(self):
        self.screenshotClicked.emit()

    def on_trace_mode_changed(self, trace_mode):
        self.traceModeChanged.emit(trace_mode)

    def on_group_all_clicked(self):
        self.groupAllClicked.emit()

    def on_isolate_all_clicked(self):
        self.isolateAllClicked.emit()

    def on_test_trace_clicked(self):
        self.testTraceClicked.emit()

    def on_clear_traces_clicked(self):
        self.clearTracesClicked.emit()