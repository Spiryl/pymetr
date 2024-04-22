# --- display_panel.py ---
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QComboBox, QFrame
from PySide6.QtCore import Signal
from pyqtgraph.parametertree import ParameterTree, Parameter

class DisplayPanel(QWidget):
    gridToggled = Signal(bool)
    xLogScaleToggled = Signal(bool)
    yLogScaleToggled = Signal(bool)
    xGridChanged = Signal(bool)
    yGridChanged = Signal(bool)
    titleChanged = Signal(str)
    titleVisibilityChanged = Signal(bool)
    xLabelChanged = Signal(str)
    xLabelVisibilityChanged = Signal(bool)
    yLabelChanged = Signal(str)
    yLabelVisibilityChanged = Signal(bool)

    def __init__(self, trace_plot, parent=None):
        super().__init__(parent)
        self.trace_plot = trace_plot
        self.layout = QVBoxLayout(self)

        self.params = [
            {'name': 'Plot Settings', 'type': 'group', 'children': [
                {'name': 'Grid', 'type': 'bool', 'value': False},
                {'name': 'X Log Scale', 'type': 'bool', 'value': False},
                {'name': 'Y Log Scale', 'type': 'bool', 'value': False},
                {'name': 'X Grid', 'type': 'bool', 'value': True},
                {'name': 'Y Grid', 'type': 'bool', 'value': True},
            ]},
            {'name': 'Labels', 'type': 'group', 'children': [
                {'name': 'Title', 'type': 'str', 'value': 'Plot Title'},
                {'name': 'Show Title', 'type': 'bool', 'value': True},
                {'name': 'X Label', 'type': 'str', 'value': 'X'},
                {'name': 'Show X Label', 'type': 'bool', 'value': True},
                {'name': 'Y Label', 'type': 'str', 'value': 'Y'},
                {'name': 'Show Y Label', 'type': 'bool', 'value': True},
            ]},
            {'name': 'Trace Settings', 'type': 'group', 'children': [
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
        self.parameter.param('Plot Settings', 'X Grid').sigValueChanged.connect(
            lambda param, value: self.xGridChanged.emit(value)
        )
        self.parameter.param('Plot Settings', 'Y Grid').sigValueChanged.connect(
            lambda param, value: self.yGridChanged.emit(value)
        )
        self.parameter.param('Labels', 'Title').sigValueChanged.connect(
            lambda param, value: self.titleChanged.emit(value)
        )
        self.parameter.param('Labels', 'Show Title').sigValueChanged.connect(
            lambda param, value: self.titleVisibilityChanged.emit(value)
        )
        self.parameter.param('Labels', 'X Label').sigValueChanged.connect(
            lambda param, value: self.xLabelChanged.emit(value)
        )
        self.parameter.param('Labels', 'Show X Label').sigValueChanged.connect(
            lambda param, value: self.xLabelVisibilityChanged.emit(value)
        )
        self.parameter.param('Labels', 'Y Label').sigValueChanged.connect(
            lambda param, value: self.yLabelChanged.emit(value)
        )
        self.parameter.param('Labels', 'Show Y Label').sigValueChanged.connect(
            lambda param, value: self.yLabelVisibilityChanged.emit(value)
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
        self.plot_mode_combo_box.addItems(["Single", "Stack", "Run"])
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