import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
import numpy as np

app = QtWidgets.QApplication([])

# Create the main window and layout
main_window = QtWidgets.QMainWindow()
central_widget = QtWidgets.QWidget()
main_window.setCentralWidget(central_widget)
layout = QtWidgets.QVBoxLayout(central_widget)

# Create the plot widget and add it to the layout
plot_widget = pg.PlotWidget()
layout.addWidget(plot_widget)
plot_item = plot_widget.getPlotItem()

# This list will store tuples of (axis, viewBox, curve) for additional plots
additional_plots = []

# Generate primary plot data
x = np.arange(100)
primary_y = np.random.normal(size=100)
primary_curve = plot_item.plot(x, primary_y, pen='r')

# Button for cycling through plot configurations
button = QtWidgets.QPushButton("Cycle Plot Configuration")
layout.addWidget(button)

def update_views():
    """Update the geometry of additional view boxes to match the main plot."""
    for _, view_box, _ in additional_plots:
        view_box.setGeometry(plot_item.vb.sceneBoundingRect())

def cycle_plots():
    """Cycle through configurations, adding or resetting additional plots."""
    config = len(additional_plots)
    if config == 4:  # If at max configuration, reset to just the primary plot
        # Clear existing additional plots
        for axis, view_box, curve in additional_plots:
            plot_item.layout.removeItem(axis)
            view_box.removeItem(curve)
            plot_widget.scene().removeItem(view_box)
        additional_plots.clear()
    else:
        # Add a new axis, view box, and plot
        axis = pg.AxisItem('right', pen=pg.mkPen(pg.intColor(config)))
        view_box = pg.ViewBox()
        plot_item.layout.addItem(axis, 2, 2 + config)  # Offset each new axis
        plot_item.scene().addItem(view_box)
        axis.linkToView(view_box)
        view_box.setXLink(plot_item)

        # Generate new plot data and add to the new view box
        y = np.random.normal(loc=(config + 1) * 5, scale=20, size=100)
        curve = pg.PlotCurveItem(x, y, pen=pg.mkPen(pg.intColor(config)))
        view_box.addItem(curve)

        # Store the new plot components
        additional_plots.append((axis, view_box, curve))
        update_views()  # Ensure the new view box is correctly sized and positioned

    # Update all view boxes to match the main plot's geometry
    update_views()

# Connect the button's clicked signal to the cycle_plots function
button.clicked.connect(cycle_plots)

# Ensure additional view boxes are updated when the main plot resizes
plot_item.vb.sigResized.connect(update_views)

main_window.show()
app.exec_()
