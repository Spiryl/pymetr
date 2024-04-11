import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
import numpy as np

# Initialize the application and create the main window
app = QtWidgets.QApplication([])
main_window = QtWidgets.QMainWindow()
central_widget = QtWidgets.QWidget(main_window)
layout = QtWidgets.QVBoxLayout(central_widget)

# Create the plot widget and add to the layout
plot_widget = pg.PlotWidget()
layout.addWidget(plot_widget)
plot_item = plot_widget.getPlotItem()

# Create combo box for selecting plotting mode and button for generating plots
combo_box = QtWidgets.QComboBox()
combo_box.addItems(["Single Axis", "Separate Axes"])
layout.addWidget(combo_box)

button = QtWidgets.QPushButton("Generate Plots")
layout.addWidget(button)

# Initialize a legend for the plot
legend = pg.LegendItem(offset=(70, 30))
legend.setParentItem(plot_item)

# Keep references to additional axes and ViewBoxes
additional_axes = []
additional_view_boxes = []
primary_curve = None  # The curve displayed on the primary Y-axis

# Define a function to clear additional axes and ViewBoxes
def clear_additional_axes():
    global additional_axes, additional_view_boxes
    # Remove additional axes and ViewBoxes from the plot item and scene
    for axis in additional_axes:
        plot_item.layout.removeItem(axis)
        axis.deleteLater()
    for view_box in additional_view_boxes:
        plot_widget.scene().removeItem(view_box)
        view_box.deleteLater()
    additional_axes.clear()
    additional_view_boxes.clear()
    legend.clear()  # Clear the legend as well

# Define a function to update ViewBoxes geometry when resizing
def update_view_boxes():
    # Update each ViewBox to match the plot item's geometry
    for view_box in additional_view_boxes:
        view_box.setGeometry(plot_item.vb.sceneBoundingRect())

# Define a function to handle curve click events
def trace_clicked(curve):
    global primary_curve, additional_axes, additional_view_boxes
    # Move the clicked curve to the primary Y-axis
    primary_curve = curve
    plot_item.clear()
    clear_additional_axes()
    plot_item.addItem(curve)  # Add the clicked curve to the primary axis
    legend.addItem(curve, curve.name())  # Update the legend

# Define a function to generate new plots based on the combo box selection
def generate_plots():
    global primary_curve
    plot_item.clear()
    clear_additional_axes()  # Start with a fresh plot item
    x = np.arange(100)

    # Generate four curves
    for i in range(4):
        y = np.random.normal(loc=i * 5, scale=20, size=100)
        curve = pg.PlotCurveItem(x, y, pen=pg.mkPen(pg.intColor(i), width=2), name=f"Trace {i+1}")
        plot_item.addItem(curve)
        legend.addItem(curve, f"Trace {i+1}")  # Add curve to the legend

        if i == 0:
            primary_curve = curve  # Set the first curve as the primary curve

        # If Separate Axes mode is selected, create new axes for other curves
        if combo_box.currentText() == "Separate Axes" and i != 0:
            axis = pg.AxisItem("right", pen=curve.opts['pen'])
            plot_item.layout.addItem(axis, 2, 2 + i)
            additional_axes.append(axis)

            view_box = pg.ViewBox()
            plot_widget.scene().addItem(view_box)
            axis.linkToView(view_box)
            view_box.setXLink(plot_item)
            additional_view_boxes.append(view_box)

            view_box.addItem(curve)  # Add curve to the new ViewBox

    # Connect the update function to the resize signal and curve click events
    plot_item.vb.sigResized.connect(update_view_boxes)
    for curve in plot_item.curves:
        curve.setClickable(True)
        curve.sigClicked.connect(lambda _, c=curve: trace_clicked(c))

# Connect the button click to the generate_plots function
button.clicked.connect(generate_plots)

# Set the central widget and show the main window
main_window.setCentralWidget(central_widget)
main_window.show()

# Start the Qt event loop
app.exec()
