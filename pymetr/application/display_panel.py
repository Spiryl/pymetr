# --- display_panel.py ---
from PySide6.QtWidgets import QWidget, QVBoxLayout
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