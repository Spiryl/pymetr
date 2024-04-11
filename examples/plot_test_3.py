import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np
import random

class Trace:
    def __init__(self, label=None, color=None, mode='Group', data=None, line_thickness=1.0, alpha=1.0, line_style='-'):
        self.label = label
        self.color = color
        self.mode = mode
        self.data = data if data is not None else np.array([])
        self.visible = True
        self.x_range = None
        self.y_range = None
        self.line_thickness = line_thickness
        self.alpha = alpha
        self.line_style = line_style

class TraceManager(QtCore.QObject):
    traceDataChanged = QtCore.Signal(object)

    def __init__(self):
        super().__init__()
        self.traces = []
        self.plot_mode = 'Add'
        self.trace_mode = 'Group'  # Add this line

    def add_trace(self, trace):
        if self.plot_mode == "Replace":
            self.traces.clear()
        trace.mode = self.trace_mode 
        self.traces.append(trace)
        self.emit_trace_data()

    def remove_trace(self, trace):
        if trace in self.traces:
            self.traces.remove(trace)
            self.emit_trace_data()

    def emit_trace_data(self):
        trace_data = {trace.label: {
            'label': trace.label,
            'color': trace.color,
            'mode': trace.mode,
            'data': trace.data.tolist(),
            'visible': trace.visible,
            'line_thickness': trace.line_thickness,
            'line_style': trace.line_style
        } for trace in self.traces}
        self.traceDataChanged.emit(trace_data)

class TraceDock(QtWidgets.QDockWidget):
    
    traceModeChanged = QtCore.Signal(str)  # Add this line
    roiPlotEnabled = QtCore.Signal(bool)

    def __init__(self, parent=None, trace_manager=None):
        super().__init__("Trace Settings", parent)
        self.setMinimumWidth(200) 
        self.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)

        self.trace_manager = trace_manager

        self.dock_widget = QtWidgets.QWidget()
        self.dock_layout = QtWidgets.QVBoxLayout(self.dock_widget)

        self.plot_mode_combo_box = QtWidgets.QComboBox()
        self.plot_mode_combo_box.addItems(["Add", "Replace"])
        self.plot_mode_combo_box.currentIndexChanged.connect(self.on_plot_mode_changed)
        self.dock_layout.addWidget(self.plot_mode_combo_box)

        self.trace_mode_combo_box = QtWidgets.QComboBox()
        self.trace_mode_combo_box.addItems(["Group", "Isolate"])
        self.trace_mode_combo_box.currentIndexChanged.connect(self.on_trace_mode_changed)
        self.dock_layout.addWidget(self.trace_mode_combo_box)
        self.trace_mode_combo_box.setCurrentText(self.trace_manager.trace_mode)

        self.roi_plot_checkbox = QtWidgets.QCheckBox("Enable ROI Plot")
        self.roi_plot_checkbox.setChecked(False)
        self.roi_plot_checkbox.stateChanged.connect(self.on_roi_plot_checkbox_changed)
        self.dock_layout.addWidget(self.roi_plot_checkbox)

        self.trace_parameter_tree = pg.parametertree.ParameterTree()
        self.dock_layout.addWidget(self.trace_parameter_tree)

        self.setWidget(self.dock_widget)

        self.trace_manager.traceDataChanged.connect(self.update_parameter_tree)

    def on_roi_plot_checkbox_changed(self, state):
        self.roiPlotEnabled.emit(state == QtCore.Qt.Checked)

    def on_plot_mode_changed(self, index):
        plot_mode = self.plot_mode_combo_box.itemText(index)
        self.trace_manager.plot_mode = plot_mode
        self.trace_manager.emit_trace_data()

    def on_trace_mode_changed(self, index):
        trace_mode = self.trace_mode_combo_box.itemText(index)
        self.traceModeChanged.emit(trace_mode)  # Update this line
        self.trace_manager.trace_mode = trace_mode  # Add this line

    def update_parameter_tree(self, trace_data):
        self.trace_parameter_tree.clear()
        for trace_id, trace_info in trace_data.items():
            trace_param = pg.parametertree.Parameter.create(name=trace_id, type='group', children=[
                {'name': 'Label', 'type': 'str', 'value': trace_info['label']},
                {'name': 'Visible', 'type': 'bool', 'value': trace_info['visible']},
                {'name': 'Color', 'type': 'color', 'value': trace_info['color']},
                {'name': 'Mode', 'type': 'list', 'limits': ['Group', 'Isolate'], 'value': trace_info['mode']},
                {'name': 'Extra', 'type': 'group', 'expanded': False, 'children': [
                    {'name': 'Line Thickness', 'type': 'float', 'value': trace_info.get('line_thickness', 1.0), 'step': 0.1, 'limits': (0.1, 10.0)},
                    {'name': 'Line Style', 'type': 'list', 'limits': ['Solid', 'Dash', 'Dot', 'Dash-Dot'], 'value': trace_info.get('line_style', 'Solid')}
                ]},
                {'name': 'Delete', 'type': 'action'}
            ])
            trace_param.child('Delete').sigActivated.connect(lambda _, tid=trace_id: self.remove_trace(tid))
            trace_param.child('Label').sigValueChanged.connect(lambda param, val, tid=trace_id: self.update_trace_label(tid, val))
            trace_param.child('Visible').sigValueChanged.connect(lambda param, val, tid=trace_id: self.update_trace_parameter(tid, 'visible', val))
            trace_param.child('Color').sigValueChanged.connect(lambda param, val, tid=trace_id: self.update_trace_parameter(tid, 'color', val))
            trace_param.child('Mode').sigValueChanged.connect(lambda param, val, tid=trace_id: self.update_trace_parameter(tid, 'mode', val))
            trace_param.child('Extra').child('Line Thickness').sigValueChanged.connect(lambda param, val, tid=trace_id: self.update_trace_parameter(tid, 'line_thickness', val))
            trace_param.child('Extra').child('Line Style').sigValueChanged.connect(lambda param, val, tid=trace_id: self.update_trace_parameter(tid, 'line_style', val))
            self.trace_parameter_tree.addParameters(trace_param)

    def update_trace_label(self, trace_id, label):
        for trace in self.trace_manager.traces:
            if trace.label == trace_id:
                trace.label = label
                self.trace_manager.emit_trace_data()
                break

    def update_trace_parameter(self, trace_id, parameter, value):
        for trace in self.trace_manager.traces:
            if trace.label == trace_id:
                setattr(trace, parameter, value)
                self.trace_manager.emit_trace_data()
                break

    def remove_trace(self, trace_id):
        for trace in self.trace_manager.traces:
            if trace.label == trace_id:
                self.trace_manager.remove_trace(trace)
                break

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.central_widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)

        self.plot_widget = pg.PlotWidget()
        self.layout.addWidget(self.plot_widget)
        self.plot_item = self.plot_widget.getPlotItem()

        self.legend = pg.LegendItem(offset=(70, 30))
        self.legend.setParentItem(self.plot_item)

        self.trace_manager = TraceManager()
        self.trace_dock = TraceDock(self, self.trace_manager)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.trace_dock)

        self.add_trace_button = QtWidgets.QPushButton("Add Trace")
        self.add_trace_button.clicked.connect(self.add_trace)
        self.layout.addWidget(self.add_trace_button)

        self.setCentralWidget(self.central_widget)

        self.additional_axes = []
        self.additional_view_boxes = []
        self.traces = []

        self.roi_plot_item = None
        self.roi_plot = None
        self.roi = None

        self.trace_manager.traceDataChanged.connect(self.update_plot)
        self.trace_dock.traceModeChanged.connect(self.on_trace_mode_changed)
        self.trace_dock.roiPlotEnabled.connect(self.on_roi_plot_enabled)

    def on_roi_plot_enabled(self, enabled):
        if enabled:
            self.roi_plot_item = self.plot_layout.addPlot(row=1, col=0, rowSpan=1, height=100)
            self.roi_plot = self.roi_plot_item.vb

            self.roi = pg.LinearRegionItem()
            self.roi.setZValue(-10)
            self.roi_plot.addItem(self.roi)

            self.roi.sigRegionChanged.connect(self.update_main_plot)
            self.plot_item.sigXRangeChanged.connect(self.update_roi_plot)
        else:
            if self.roi_plot_item is not None:
                self.plot_layout.removeItem(self.roi_plot_item)
                self.roi_plot_item = None
                self.roi_plot = None
                self.roi = None

    def update_main_plot(self):
        if self.roi is not None:
            self.plot_item.setXRange(*self.roi.getRegion(), padding=0)

    def update_roi_plot(self):
        if self.roi is not None:
            view_range = self.plot_item.getViewBox().viewRange()[0]
            self.roi.setRegion(view_range)

    def clear_roi_plot(self):
        if self.roi_plot_item is not None:
            self.roi_plot_item.clear()

    def update_main_plot(self):
        if self.roi is not None:
            self.plot_item.vb.setXRange(*self.roi.getRegion(), padding=0)

    def update_roi_plot(self):
        if self.roi is not None:
            view_range = self.plot_item.vb.viewRange()[0]
            self.roi.setRegion(view_range)
    def add_trace(self):
        trace = TraceGenerator.generate_random_trace(self.trace_manager.trace_mode)
        self.trace_manager.add_trace(trace)

    def on_trace_mode_changed(self, trace_mode):
        self.trace_manager.trace_mode = trace_mode

    def update_plot(self, trace_data):
        self.plot_item.clear()
        self.clear_additional_axes()
        if self.roi_plot_item is not None:
            self.roi_plot_item.clear()

        for trace in self.trace_manager.traces:
            visible = trace.visible
            color = trace.color
            legend_alias = trace.label
            x = np.arange(len(trace.data))
            y = trace.data
            mode = trace.mode

            if visible:
                pen = pg.mkPen(color=color, width=trace.line_thickness, style=self.get_line_style(trace.line_style))
                
                if mode == "Group":
                    curve = pg.PlotCurveItem(x, y, pen=pen, name=legend_alias)
                    self.plot_item.addItem(curve)
                    self.legend.addItem(curve, legend_alias)
                    self.traces.append(curve)
                    trace.y_range = self.plot_item.vb.viewRange()[1]  # Update the y-range for traces in a group
                    if self.roi_plot_item is not None:
                        roi_curve = self.roi_plot_item.plot(x, y, pen=pen, name=legend_alias)
                else:  # Isolate mode
                    axis = pg.AxisItem("right", pen=pen)
                    self.plot_item.layout.addItem(axis, 2, self.trace_manager.traces.index(trace) + 2)
                    self.additional_axes.append(axis)

                    view_box = pg.ViewBox()
                    self.plot_widget.scene().addItem(view_box)
                    axis.linkToView(view_box)
                    view_box.setXLink(self.plot_item)
                    self.additional_view_boxes.append(view_box)

                    curve = pg.PlotCurveItem(x, y, pen=pen, name=legend_alias)
                    curve.setOpacity(trace.alpha)  # Set the opacity value on the curve item
                    view_box.addItem(curve)
                    self.legend.addItem(curve, legend_alias)
                    self.traces.append(curve)
                    if trace.y_range is not None:
                        view_box.setRange(yRange=trace.y_range)

                    if self.roi_plot_item is not None:
                        roi_axis = pg.AxisItem("right", pen=pen)
                        self.roi_plot_item.layout.addItem(roi_axis, 2, self.trace_manager.traces.index(trace) + 2)

                        roi_view_box = pg.ViewBox()
                        self.roi_plot_item.scene().addItem(roi_view_box)
                        roi_axis.linkToView(roi_view_box)
                        roi_view_box.setXLink(self.roi_plot_item)

                        roi_curve = roi_view_box.plot(x, y, pen=pen, name=legend_alias)

                    print(f"Trace: {trace.label}, Visible: {trace.visible}, Mode: {trace.mode}, Y-Range: {trace.y_range}")  # Debug information

        self.plot_item.vb.sigResized.connect(self.update_view_boxes)
        self.update_main_plot()
        if self.roi_plot is not None:
            self.roi_plot.autoRange()

    def get_line_style(self, line_style):
        if line_style == 'Solid':
            return QtCore.Qt.SolidLine
        elif line_style == 'Dash':
            return QtCore.Qt.DashLine
        elif line_style == 'Dot':
            return QtCore.Qt.DotLine
        elif line_style == 'Dash-Dot':
            return QtCore.Qt.DashDotLine
        else:
            return QtCore.Qt.SolidLine

    def handle_view_box_range_changed(self, view_box, trace):
        x_range, y_range = view_box.viewRange()
        trace.x_range = x_range
        trace.y_range = y_range
        self.trace_manager.emit_trace_data()

    def clear_additional_axes(self):
        for axis in self.additional_axes:
            self.plot_item.layout.removeItem(axis)
            axis.deleteLater()
        for view_box in self.additional_view_boxes:
            self.plot_widget.scene().removeItem(view_box)
            view_box.deleteLater()
        self.additional_axes.clear()
        self.additional_view_boxes.clear()
        self.legend.clear()

    def update_view_boxes(self):
        for view_box in self.additional_view_boxes:
            view_box.setGeometry(self.plot_item.vb.sceneBoundingRect())

class TraceGenerator:
    trace_counter = 1

    @staticmethod
    def generate_random_trace(mode='Group'):
        trace_name = f"Trace {TraceGenerator.trace_counter}"
        TraceGenerator.trace_counter += 1
        random_color = pg.intColor(random.randint(0, 255))
        x = np.arange(100)
        y = np.random.normal(loc=0, scale=20, size=100)
        trace = Trace(label=trace_name, color=random_color, mode=mode, data=y)
        return trace

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    main_window = MainWindow()
    main_window.show()
    app.exec()