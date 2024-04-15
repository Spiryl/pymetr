# --- trace_panel.py ---
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QDockWidget
from PySide6.QtCore import QObject, Signal, Qt

from pymetr.instrument import Trace

class TraceManager(QObject):
    traceDataChanged = Signal(list)
    traceAdded = Signal(Trace)

    def __init__(self):
        super().__init__()
        self.traces = []
        self.plot_mode = 'Add'
        self.trace_mode = 'Group'

    def add_trace(self, data):
        print(f"Received trace data in TraceManager: {data}")
        if self.plot_mode == "Replace":
            self.traces.clear()

        if isinstance(data, Trace):
            # If data is a single Trace object
            data.mode = self.trace_mode
            self.traces.append(data)
        elif isinstance(data, (list, tuple)):
            # If data is a list or tuple of Trace objects or arrays
            for item in data:
                trace = self.create_trace(item)
                if trace:
                    self.traces.append(trace)
        elif isinstance(data, dict):
            # If data is a dictionary representing a trace
            trace = self.create_trace(data)
            if trace:
                self.traces.append(trace)
        else:
            # If data is a single array or list of values
            trace = self.create_trace(data)
            if trace:
                self.traces.append(trace)

        self.emit_trace_data()
        self.traceAdded.emit(trace)

    def create_trace(self, data):
        if isinstance(data, Trace):
            return data
        elif isinstance(data, (list, tuple, np.ndarray)):
            return Trace(label=f"Trace {len(self.traces) + 1}", data=data)
        elif isinstance(data, dict):
            return Trace(**data)
        else:
            print(f"Unsupported data type: {type(data)}")
            return None

    def clear_traces(self):
        self.traces.clear()
        self.emit_trace_data()

    def remove_trace(self, trace):
        if trace in self.traces:
            self.traces.remove(trace)
            self.emit_trace_data()

    def on_plot_mode_changed(self, mode):
        self.plot_mode = mode

    def on_trace_mode_changed(self, mode):
        self.trace_mode = mode

    def set_plot_mode(self, mode):
        self.plot_mode = mode
        self.emit_trace_data()

    def set_trace_mode(self, mode):
        self.trace_mode = mode
        for trace in self.traces:
            trace.mode = mode
        self.emit_trace_data()

    def emit_trace_data(self):
        self.traceDataChanged.emit(self.traces)

class TracePanel(QDockWidget):
    def __init__(self, trace_manager, parent=None):
        super().__init__("", parent)
        self.setMinimumWidth(200) 
        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self.trace_manager = trace_manager

        self.dock_widget = QWidget()
        self.dock_layout = QVBoxLayout(self.dock_widget)

        self.trace_parameter_tree = pg.parametertree.ParameterTree()
        self.dock_layout.addWidget(self.trace_parameter_tree)

        self.setWidget(self.dock_widget)

        self.trace_manager.traceDataChanged.connect(self.update_parameter_tree)

    def update_parameter_tree(self, trace_data):
        self.trace_parameter_tree.clear()
        for trace in trace_data:
            if isinstance(trace, Trace):
                trace_label = trace.label
                trace_attrs = trace.__dict__
            elif isinstance(trace, dict):
                trace_label = trace['label']
                trace_attrs = trace
            else:
                # If trace is not a Trace object or a dictionary, skip it
                continue

            trace_param = pg.parametertree.Parameter.create(name=trace_label, type='group', children=[
                {'name': 'Label', 'type': 'str', 'value': trace_label},
                {'name': 'Visible', 'type': 'bool', 'value': trace_attrs.get('visible', True)},
                {'name': 'Color', 'type': 'color', 'value': trace_attrs.get('color', 'ffffff')},
                {'name': 'Mode', 'type': 'list', 'limits': ['Group', 'Isolate'], 'value': trace_attrs.get('mode', 'Group')},
                {'name': 'Extra', 'type': 'group', 'expanded': False, 'children': [
                    {'name': 'Line Thickness', 'type': 'float', 'value': trace_attrs.get('line_thickness', 1.0), 'step': 0.1, 'limits': (0.1, 10.0)},
                    {'name': 'Line Style', 'type': 'list', 'limits': ['Solid', 'Dash', 'Dot', 'Dash-Dot'], 'value': trace_attrs.get('line_style', 'Solid')}
                ]},
                {'name': 'Delete', 'type': 'action'}
            ])
            trace_param.child('Delete').sigActivated.connect(lambda _, tid=trace_label: self.remove_trace(tid))
            trace_param.child('Label').sigValueChanged.connect(lambda param, val, tid=trace_label: self.update_trace_label(tid, val))
            trace_param.child('Visible').sigValueChanged.connect(lambda param, val, tid=trace_label: self.update_trace_parameter(tid, 'visible', val))
            trace_param.child('Color').sigValueChanged.connect(lambda param, val, tid=trace_label: self.update_trace_parameter(tid, 'color', val))
            trace_param.child('Mode').sigValueChanged.connect(lambda param, val, tid=trace_label: self.update_trace_parameter(tid, 'mode', val))
            trace_param.child('Extra').child('Line Thickness').sigValueChanged.connect(lambda param, val, tid=trace_label: self.update_trace_parameter(tid, 'line_thickness', val))
            trace_param.child('Extra').child('Line Style').sigValueChanged.connect(lambda param, val, tid=trace_label: self.update_trace_parameter(tid, 'line_style', val))
            self.trace_parameter_tree.addParameters(trace_param)

    def update_trace_label(self, trace_id, label):
        for trace in self.trace_manager.traces:
            if trace.label == trace_id:
                trace.label = label
                self.trace_manager.emit_trace_data()
                break

    def update_trace_parameter(self, trace_id, parameter, value):
        trace = next((t for t in self.trace_manager.traces if t.label == trace_id), None)
        if trace:
            setattr(trace, parameter, value)
            if trace.mode == 'Isolate':
                if parameter == 'color':
                    axis = self.parent().trace_axes.get(trace.label)
                    if axis:
                        axis.setPen(pg.mkPen(color=value))
            self.trace_manager.emit_trace_data()

    def remove_trace(self, trace_id):
        for trace in self.trace_manager.traces:
            if trace.label == trace_id:
                self.trace_manager.remove_trace(trace)
                break