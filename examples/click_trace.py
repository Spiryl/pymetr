import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
import numpy as np

app = QtWidgets.QApplication([])
main_window = QtWidgets.QMainWindow()
central_widget = QtWidgets.QWidget()
main_window.setCentralWidget(central_widget)
layout = QtWidgets.QVBoxLayout(central_widget)
plot_widget = pg.PlotWidget()
layout.addWidget(plot_widget)

# Simplified version to demonstrate correct signal handling
def trace_clicked(curve):
    print(f"Clicked on curve: {curve.name()}")

x = np.linspace(0, 10, 100)
y = np.sin(x)

curve = plot_widget.plot(x, y, name='Sine Wave', pen='r')
curve.setCurveClickable(True)
curve.sigClicked.connect(lambda ev: trace_clicked(curve))  # Correctly connect signal

main_window.show()
app.exec_()