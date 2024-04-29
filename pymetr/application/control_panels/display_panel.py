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

