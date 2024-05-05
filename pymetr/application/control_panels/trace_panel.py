# --- trace_panel.py ---
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
from PySide6.QtWidgets import QWidget, QVBoxLayout, QDockWidget
from PySide6.QtCore import Qt

from pymetr.core.trace import Trace

class TracePanel(QDockWidget):
    
    def __init__(self, trace_manager, trace_plot, parent=None):
        super().__init__("", parent)
        self.setMinimumWidth(200) 
        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self.trace_manager = trace_manager
        self.trace_plot = trace_plot

        self.dock_widget = QWidget()
        self.dock_layout = QVBoxLayout(self.dock_widget)

        self.trace_parameter_tree = ParameterTree()
        self.dock_layout.addWidget(self.trace_parameter_tree)

        self.setWidget(self.dock_widget)


    def handle_trace_parameter_changes(self, param, changes):
        for param, change, data in changes:
            if change == 'value':
                trace_id = param.parent().name()
                if param.name() == 'visible':
                    self.trace_manager.traceVisibilityChanged.emit(trace_id, data)
                elif param.name() == 'color':
                    self.trace_manager.traceColorChanged.emit(trace_id, data)
                elif param.name() == 'label':
                    self.trace_manager.traceLabelChanged.emit(trace_id, data)
                elif param.name() == 'line_thickness':
                    self.trace_manager.traceLineThicknessChanged.emit(trace_id, data)
                elif param.name() == 'line_style':
                    self.trace_manager.traceLineStyleChanged.emit(trace_id, data)
            elif change == 'removed':
                trace_id = param.name()
                self.trace_manager.traceRemoved.emit(trace_id)

    def update_parameter_tree(self, trace_data=None):
        if trace_data is None:
            trace_data = self.trace_manager.traces
    
        self.trace_parameter_tree.clear()
        self.trace_parameters = Parameter.create(name='Traces', type='group', children=[])

        for trace in trace_data:
            if isinstance(trace, Trace):
                trace_label = trace.label
                trace_attrs = trace.__dict__
            else:
                continue

            trace_param = Parameter.create(name=trace_label, type='group', children=[
                {'name': 'Label', 'type': 'str', 'value': trace_label},
                {'name': 'Visible', 'type': 'bool', 'value': trace_attrs.get('visible', True)},
                {'name': 'Color', 'type': 'color', 'value': trace.color},
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
            self.trace_parameters.addChild(trace_param)

        self.trace_parameter_tree.setParameters(self.trace_parameters, showTop=False)
        self.trace_parameters.sigTreeStateChanged.connect(self.handle_trace_parameter_changes)

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
            if parameter == 'mode':
                self.trace_manager.set_trace_mode(trace_id, value)
            elif trace.mode == 'Isolate':
                if parameter == 'color':
                    axis = self.trace_plot.trace_axes.get(trace.label)
                    if axis:
                        axis.setPen(pg.mkPen(color=value))
            self.trace_manager.emit_trace_data()

    def remove_trace(self, trace_id):
        for trace in self.trace_manager.traces:
            if trace.label == trace_id:
                self.trace_manager.remove_trace(trace)
                break