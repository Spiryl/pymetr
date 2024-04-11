import numpy as np
import pyqtgraph as pg
import random
from pyqtgraph.parametertree import ParameterTree, Parameter
from pyqtgraph.Qt import QtWidgets
from PySide6.QtCore import Signal, QObject
from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtGui

class Trace(QtCore.QObject):
    def __init__(self, label=None, color=None, alpha=1.0, mode='single', scale=None, data=None, data_units=None, x_range=None, x_range_units=None, line_type='solid', stats=None, visible=True):
        super().__init__()
        self._label = label
        self._color = color or pg.intColor(random.randint(0, 255))
        self._alpha = alpha
        self._mode = mode
        self._scale = scale
        self._data = data if data is not None else np.array([])
        self._data_units = data_units
        self._x_range = x_range
        self._x_range_units = x_range_units
        self._line_type = line_type
        self._stats = stats or {}
        self._visible = visible

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value):
        self._label = value

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value

    @property
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self, value):
        self._alpha = value

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self._mode = value

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value):
        self._scale = value

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def data_units(self):
        return self._data_units

    @data_units.setter
    def data_units(self, value):
        self._data_units = value

    @property
    def x_range(self):
        return self._x_range

    @x_range.setter
    def x_range(self, value):
        self._x_range = value

    @property
    def x_range_units(self):
        return self._x_range_units

    @x_range_units.setter
    def x_range_units(self, value):
        self._x_range_units = value

    @property
    def line_type(self):
        return self._line_type

    @line_type.setter
    def line_type(self, value):
        self._line_type = value

    @property
    def stats(self):
        return self._stats

    @stats.setter
    def stats(self, value):
        self._stats = value

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = value

class TraceManager(QtCore.QObject):
    traceAdded = QtCore.Signal(object)
    traceRemoved = QtCore.Signal(object)
    traceUpdated = QtCore.Signal(object)
    traceDataChanged = QtCore.Signal(dict)

    def __init__(self):
        super().__init__()
        self.traces = []
        self.trace_mode = 'Single'
        self.plot_mode = 'Add'

    def add_trace(self, trace):
        if self.plot_mode == "Replace":
            self.traces.clear()
        trace.mode = self.trace_mode
        self.traces.append(trace)
        self.traceAdded.emit(trace)
        self.emit_trace_data()

    def remove_trace(self, trace):
        if trace in self.traces:
            self.traces.remove(trace)
            self.traceRemoved.emit(trace)
            self.emit_trace_data()

    def update_trace_parameter(self, trace, parameter, value):
        setattr(trace, parameter, value)
        self.traceUpdated.emit(trace)
        self.emit_trace_data()

    def emit_trace_data(self):
        trace_data = {trace.label: {
            'color': trace.color,
            'alpha': trace.alpha,
            'mode': trace.mode,
            'scale': trace.scale,
            'data': trace.data.tolist(),
            'data_units': trace.data_units,
            'x_range': trace.x_range,
            'x_range_units': trace.x_range_units,
            'line_type': trace.line_type,
            'stats': trace.stats,
            'visible': trace.visible  # Include the visible attribute
        } for trace in self.traces}
        self.traceDataChanged.emit(trace_data)

class TraceDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None, trace_manager=None):
        super().__init__("Trace Settings", parent)
        self.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)

        self.trace_manager = trace_manager

        self.dock_widget = QtWidgets.QWidget()
        self.dock_layout = QtWidgets.QVBoxLayout(self.dock_widget)

        self.plot_mode_combo_box = QtWidgets.QComboBox()
        self.plot_mode_combo_box.addItems(["Add", "Replace"])
        self.plot_mode_combo_box.currentIndexChanged.connect(self.on_plot_mode_changed)
        self.dock_layout.addWidget(self.plot_mode_combo_box)

        self.trace_mode_combo_box = QtWidgets.QComboBox()
        self.trace_mode_combo_box.addItems(["Single", "Isolate"])
        self.trace_mode_combo_box.currentIndexChanged.connect(self.on_trace_mode_changed)
        self.dock_layout.addWidget(self.trace_mode_combo_box)

        self.trace_parameter_tree = ParameterTree()
        self.dock_layout.addWidget(self.trace_parameter_tree)

        self.setWidget(self.dock_widget)

        self.trace_manager.traceDataChanged.connect(self.update_parameter_tree)

    def on_plot_mode_changed(self, index):
        plot_mode = self.plot_mode_combo_box.itemText(index)
        self.trace_manager.plot_mode = plot_mode  # Update this line
        self.trace_manager.emit_trace_data()

    def on_trace_mode_changed(self, index):
        trace_mode = self.trace_mode_combo_box.itemText(index)
        self.trace_manager.trace_mode = trace_mode
        self.trace_manager.emit_trace_data()

    def update_parameter_tree(self, trace_data):
        self.trace_parameter_tree.clear()
        for trace_id, trace_info in trace_data.items():
            trace_param = Parameter.create(name=trace_id, type='group', children=ParameterTreeFactory.create_parameter_children(trace_info))
            trace_param.child('Delete').sigActivated.connect(lambda _, tid=trace_id: self.remove_trace(tid))
            trace_param.child('visible').sigValueChanged.connect(lambda _, tid=trace_id: self.update_trace_parameter(tid, 'visible', _))
            trace_param.child('color').sigValueChanged.connect(lambda _, tid=trace_id: self.update_trace_parameter(tid, 'color', _))
            trace_param.child('alpha').sigValueChanged.connect(lambda _, tid=trace_id: self.update_trace_parameter(tid, 'alpha', _))
            trace_param.child('scale').sigValueChanged.connect(lambda _, tid=trace_id: self.update_trace_parameter(tid, 'scale', _))
            trace_param.child('mode').sigValueChanged.connect(lambda _, tid=trace_id: self.update_trace_parameter(tid, 'mode', _))
            self.trace_parameter_tree.addParameters(trace_param)

    def update_trace_parameter(self, trace_id, parameter, value):
        trace = self.get_trace_by_id(trace_id)
        if trace:
            setattr(trace, parameter, value)
            self.trace_manager.traceUpdated.emit(trace)
            self.trace_manager.emit_trace_data()

    def get_trace_by_id(self, trace_id):
        for trace in self.trace_manager.traces:
            if trace.label == trace_id:
                return trace
        return None

    def remove_trace(self, trace_id):
        for trace in self.trace_manager.traces:
            if trace.label == trace_id:
                self.trace_manager.remove_trace(trace)
                self.trace_manager.emit_trace_data()
                break
        self.clean_up_axes()

    def clean_up_axes(self):
        plot_item = self.parent().plot_widget.getPlotItem()
        for axis in plot_item.axes:
            if axis != plot_item.getAxis('bottom') and axis != plot_item.getAxis('left'):
                plot_item.layout.removeItem(axis)
                axis.deleteLater()
        for view_box in plot_item.scene().items():
            if isinstance(view_box, pg.ViewBox) and view_box != plot_item.vb:
                plot_item.scene().removeItem(view_box)
                view_box.deleteLater()

class ParameterTreeFactory:
    @staticmethod
    def create_parameter_children(trace_info):
        children = [
            {'name': 'visible', 'type': 'bool', 'value': trace_info['visible']},
            {'name': 'color', 'type': 'color', 'value': trace_info['color']},
            {'name': 'alpha', 'type': 'float', 'value': trace_info['alpha'], 'limits': (0, 1)},
            {'name': 'scale', 'type': 'list', 'value': trace_info['scale']},
            {'name': 'data', 'type': 'list', 'value': trace_info['data'], 'visible': False},
            {'name': 'data_units', 'type': 'str', 'value': trace_info['data_units']},
            {'name': 'x_range', 'type': 'list', 'value': trace_info['x_range'], 'visible': False},
            {'name': 'x_range_units', 'type': 'str', 'value': trace_info['x_range_units'], 'visible': False},
            {'name': 'line_type', 'type': 'list', 'limits': ['solid', 'dashed', 'dotted'], 'value': trace_info['line_type'], 'visible': False},
            {'name': 'stats', 'type': 'group', 'children': [{'name': k, 'type': 'str', 'value': v} for k, v in trace_info['stats'].items()]},
            {'name': 'mode', 'type': 'list', 'limits': ['Single', 'Isolate'], 'value': trace_info['mode']},
            {'name': 'Delete', 'type': 'action'}
        ]
        return children

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Trace Plotter")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QtWidgets.QWidget()
        self.central_layout = QtWidgets.QVBoxLayout(self.central_widget)

        self.plot_widget = pg.PlotWidget()
        self.central_layout.addWidget(self.plot_widget)

        self.trace_manager = TraceManager()
        self.trace_manager.traceDataChanged.connect(self.update_plot)

        self.trace_dock = TraceDock(self, trace_manager=self.trace_manager)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.trace_dock)

        self.trace_generator_dock = TraceGeneratorDock(self, trace_manager=self.trace_manager)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.trace_generator_dock)

        self.setCentralWidget(self.central_widget)

    def update_plot(self, trace_data):
        self.plot_widget.clear()
        legend = self.plot_widget.addLegend(offset=(50, 10))

        for trace_id, trace_info in trace_data.items():
            visible = trace_info['visible']
            color = trace_info['color']
            data = trace_info['data']
            line_type = trace_info['line_type']
            mode = trace_info['mode']

            if visible:
                color.setAlpha(int(trace_info['alpha'] * 255))
                pen = pg.mkPen(color, width=2, style=self.get_line_style(line_type))

                if mode == 'Single':
                    plot_item = self.plot_widget.plot(data, pen=pen, name=trace_id)
                    legend.addItem(plot_item, trace_id)
                else:
                    axis_item = pg.AxisItem("right")
                    axis_item.setLabel("")  # Remove the label on the viewbox axes
                    axis_item.setPen(pen)
                    self.plot_widget.getPlotItem().layout.addItem(axis_item, 2, len(self.plot_widget.getPlotItem().axes) + 2)
                    view_box = pg.ViewBox()
                    axis_item.linkToView(view_box)
                    view_box.setXLink(self.plot_widget.getPlotItem())
                    plot_item = pg.PlotCurveItem(data, pen=pen, name=trace_id)
                    view_box.addItem(plot_item)
                    self.plot_widget.getPlotItem().scene().addItem(view_box)
                    legend.addItem(plot_item, trace_id)

        # Remove legend items for traces that are no longer visible
        legend_items = legend.items.copy()
        for sample, label in legend_items:
            if label.text not in trace_data or not trace_data[label.text]['visible']:
                legend.removeItem(label.text)

    def get_line_style(self, line_type):
        if line_type == 'solid':
            return QtCore.Qt.SolidLine
        elif line_type == 'dashed':
            return QtCore.Qt.DashLine
        elif line_type == 'dotted':
            return QtCore.Qt.DotLine
        else:
            return QtCore.Qt.SolidLine

class TraceGeneratorDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None, trace_manager=None):
        super().__init__("Trace Generator", parent)
        self.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)

        self.trace_manager = trace_manager

        self.dock_widget = QtWidgets.QWidget()
        self.dock_layout = QtWidgets.QVBoxLayout(self.dock_widget)

        self.add_trace_button = QtWidgets.QPushButton("Add Trace")
        self.add_trace_button.clicked.connect(self.generate_trace)
        self.dock_layout.addWidget(self.add_trace_button)

        self.setWidget(self.dock_widget)

    def generate_trace(self):
        trace_name = self.generate_random_name()
        color = self.generate_random_color()
        num_points = self.generate_random_num_points()
        signal_type = self.generate_random_signal_type()

        data = self.generate_signal_data(signal_type, num_points)
        trace = Trace(label=trace_name, color=color, data=data)
        self.trace_manager.add_trace(trace)

    def generate_random_name(self):
        return f"Trace {random.randint(1, 100)}"

    def generate_random_color(self):
        return pg.intColor(random.randint(0, 255))

    def generate_random_num_points(self):
        return random.randint(50, 200)

    def generate_random_signal_type(self):
        signal_types = ["Sine Wave", "Square Wave", "Triangle Wave", "Noise"]
        return random.choice(signal_types)

    def generate_signal_data(self, signal_type, num_points):
        x = np.linspace(0, 10, num_points)
        if signal_type == "Sine Wave":
            y = np.sin(2 * np.pi * x)
        elif signal_type == "Square Wave":
            y = np.sign(np.sin(2 * np.pi * x))
        elif signal_type == "Triangle Wave":
            y = np.abs(np.sin(2 * np.pi * x))
        else:  # Noise
            y = np.random.rand(num_points)
        return y

if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())