import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
from pyqtgraph.parametertree import Parameter, ParameterTree, interact
import numpy as np
import random

# Initialize the application and create the main window
app = QtWidgets.QApplication([])
main_window = QtWidgets.QMainWindow()
central_widget = QtWidgets.QWidget(main_window)
layout = QtWidgets.QVBoxLayout(central_widget)

# Create the plot widget and add to the layout
plot_widget = pg.PlotWidget()
layout.addWidget(plot_widget)
plot_item = plot_widget.getPlotItem()

# Initialize a legend for the plot
legend = pg.LegendItem(offset=(70, 30))
legend.setParentItem(plot_item)

# Create the parameter tree widget for trace parameters
trace_params = []

trace_parameter_tree = ParameterTree()
params = Parameter.create(name='params', type='group', children=trace_params)
trace_parameter_tree.setParameters(params)

# Create a dock widget for the trace parameter tree
trace_dock_widget = QtWidgets.QDockWidget("Trace Parameters", main_window)
trace_dock_widget.setWidget(trace_parameter_tree)
main_window.addDockWidget(QtCore.Qt.RightDockWidgetArea, trace_dock_widget)

# Create combo box for selecting plotting mode, spin box for selecting number of traces, and button for adding traces
combo_box = QtWidgets.QComboBox()
combo_box.addItems(["Single Axis", "Separate Axes"])
layout.addWidget(combo_box)

add_replace_combo_box = QtWidgets.QComboBox()
add_replace_combo_box.addItems(["Add", "Replace"])
layout.addWidget(add_replace_combo_box)

num_traces_spin_box = QtWidgets.QSpinBox()
num_traces_spin_box.setMinimum(1)
num_traces_spin_box.setMaximum(10)
num_traces_spin_box.setValue(1)
layout.addWidget(num_traces_spin_box)

add_trace_button = QtWidgets.QPushButton("Add Trace(s)")
layout.addWidget(add_trace_button)

# Keep references to additional axes and ViewBoxes
additional_axes = []
additional_view_boxes = []
traces = []
trace_data = {}

# Define a function to clear additional axes and ViewBoxes
def clear_additional_axes():
    global additional_axes, additional_view_boxes
    for axis in additional_axes:
        plot_item.layout.removeItem(axis)
        axis.deleteLater()
    for view_box in additional_view_boxes:
        plot_widget.scene().removeItem(view_box)
        view_box.deleteLater()
    additional_axes.clear()
    additional_view_boxes.clear()
    legend.clear()

# Define a function to update ViewBoxes geometry when resizing
def update_view_boxes():
    for view_box in additional_view_boxes:
        view_box.setGeometry(plot_item.vb.sceneBoundingRect())

# Define a function to handle view box range changes and update the trace parameters
def handle_view_box_range_changed(view_box, trace_param):
    x_range, y_range = view_box.viewRange()
    trace_param.child('Scale', 'X').setValue(x_range[0])
    trace_param.child('Scale', 'Y').setValue(y_range[0])

# Define a function to generate plot data for a trace
def generate_plot_data(trace_param):
    x = np.arange(100)
    y = np.random.normal(loc=0, scale=20, size=100)
    trace_param.child('Data', 'X').setValue(x.tolist())
    trace_param.child('Data', 'Y').setValue(y.tolist())
    trace_data[trace_param.name()] = {'x': x, 'y': y}

# Define a function to update the plot based on the trace parameter tree settings
def update_plot():
    print("Updating plot...")
    plot_item.clear()
    clear_additional_axes()

    for trace_param in params.children():
        visible = trace_param.child('Visible').value()
        color = trace_param.child('Color').value()
        legend_alias = trace_param.child('Legend').value()
        x = trace_data[trace_param.name()]['x']
        y = trace_data[trace_param.name()]['y']

        print(f"Trace: {trace_param.name()}, Visible={visible}, Color={color}, Legend={legend_alias}")
        print(f"  Data: X={x}, Y={y}")

        if visible:
            pen = pg.mkPen(color, width=2)

            if combo_box.currentText() == "Single Axis":
                curve = pg.PlotCurveItem(x, y, pen=pen, name=legend_alias)
                plot_item.addItem(curve)
                legend.addItem(curve, legend_alias)
                traces.append(curve)
            else:
                axis = pg.AxisItem("right", pen=pen)
                plot_item.layout.addItem(axis, 2, params.children().index(trace_param) + 2)
                additional_axes.append(axis)

                view_box = pg.ViewBox()
                plot_widget.scene().addItem(view_box)
                axis.linkToView(view_box)
                view_box.setXLink(plot_item)
                additional_view_boxes.append(view_box)

                curve = pg.PlotCurveItem(x, y, pen=pen, name=legend_alias)
                view_box.addItem(curve)
                legend.addItem(curve, legend_alias)
                traces.append(curve)

                # Connect the view box range changed signal to update the trace parameters
                view_box.sigRangeChanged.connect(lambda _, vb=view_box, tp=trace_param: handle_view_box_range_changed(vb, tp))

    # Auto-scale the plot item and view boxes for the first plot
    if len(traces) == 1:
        plot_item.enableAutoRange()
        for view_box in additional_view_boxes:
            view_box.enableAutoRange()

    plot_item.vb.sigResized.connect(update_view_boxes)

# Define a function to add new trace(s)
def add_traces():
    print("Adding new trace(s)...")
    num_traces = num_traces_spin_box.value()
    for _ in range(num_traces):
        existing_trace_numbers = [int(trace_param.name().split(' ')[-1]) for trace_param in params.children()]
        next_trace_number = max(existing_trace_numbers) + 1 if existing_trace_numbers else 1
        trace_name = f"Trace {next_trace_number}"
        random_color = pg.intColor(random.randint(0, 255))
        trace_params = [
            {'name': 'Visible', 'type': 'bool', 'value': True},
            {'name': 'Color', 'type': 'color', 'value': random_color},
            {'name': 'Legend', 'type': 'str', 'value': trace_name},
            {'name': 'Scale', 'type': 'group', 'children': [
                {'name': 'X', 'type': 'float', 'value': 0.0, 'readonly': True},
                {'name': 'Y', 'type': 'float', 'value': 0.0, 'readonly': True}
            ]},
            {'name': 'Data', 'type': 'group', 'children': [
                {'name': 'X', 'type': 'list', 'value': [], 'visible': False},
                {'name': 'Y', 'type': 'list', 'value': [], 'visible': False}
            ]},
            {'name': 'Delete', 'type': 'action'}
        ]
        trace_param = Parameter.create(name=trace_name, type='group', children=trace_params)
        if add_replace_combo_box.currentText() == "Replace":
            params.clearChildren()
            trace_data.clear()
        params.addChild(trace_param)
        trace_param.child('Delete').sigActivated.connect(lambda _, tp=trace_param: delete_trace(tp))
        generate_plot_data(trace_param)
    update_plot()

# Define a function to handle the delete action
def delete_trace(trace_param):
    print(f"Deleting trace: {trace_param.name()}")
    params.removeChild(trace_param)
    trace_data.pop(trace_param.name(), None)
    update_plot()

# Define a function to handle legend changes
def handle_legend_change(trace_param, value):
    print(f"Legend changed for {trace_param.name()}: {value}")
    legend_alias = value
    curve = traces[params.children().index(trace_param)]
    legend.items[curve][1].setText(legend_alias)
    update_plot()

# Define a function to handle color changes
def handle_color_change(trace_param, value):
    print(f"Color changed for {trace_param.name()}: {value}")
    color = value
    curve = traces[params.children().index(trace_param)]
    curve.setPen(pg.mkPen(color, width=2))
    update_plot()

# Connect the button click to its respective function
add_trace_button.clicked.connect(add_traces)

# Connect the trace parameter tree changes to their respective functions
params.sigTreeStateChanged.connect(lambda _, __: update_plot())
for trace_param in params.children():
    trace_param.child('Delete').sigActivated.connect(lambda _, tp=trace_param: delete_trace(tp))
    trace_param.child('Legend').sigValueChanged.connect(lambda value, tp=trace_param: handle_legend_change(tp, value))
    trace_param.child('Color').sigValueChanged.connect(lambda value, tp=trace_param: handle_color_change(tp, value))

# Set the central widget and show the main window
main_window.setCentralWidget(central_widget)
main_window.show()

# Start the Qt event loop
app.exec()