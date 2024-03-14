# test_gui.py
import sys
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QDockWidget, QSplitter, QComboBox)
from PySide6.QtCore import Qt
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
from PySide6.QtCore import QFile, QTextStream

class InstrumentControlGUI(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Instrument Control and Data Acquisition")
        self.setGeometry(100, 100, 1200, 800)
        self.splitter = QSplitter()

        self.mainWidget = QWidget()
        self.setCentralWidget(self.mainWidget)
        self.layout = QVBoxLayout(self.mainWidget)

        # Initialize the Parameter Tree and Plot Widget
        self.initPlotWidget()
        self.initDockWidgets()

    def initDockWidgets(self):
        # DockWidget for Parameter Tree and other controls
        controlDockWidget = QDockWidget("Instrument Controls", self)
        controlDockWidget.setAllowedAreas(Qt.RightDockWidgetArea)

        # Wrapper widget for the dock content
        controlWidget = QWidget()
        controlLayout = QVBoxLayout(controlWidget)

        # Add your parameter tree and other controls here
        self.initParamTree()
        controlLayout.addWidget(self.paramTree)

        # Add instrument selection controls here
        # ... (Your code to add instrument selection controls)

        # Place the Update Plot button in the dock as well
        self.plotUpdateButton = QPushButton("Update Plot")
        self.plotUpdateButton.clicked.connect(self.updatePlot)
        controlLayout.addWidget(self.plotUpdateButton)

        controlDockWidget.setWidget(controlWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, controlDockWidget)

    def initPlotWidget(self):
        self.plotWidget = pg.PlotWidget()
        self.setCentralWidget(self.plotWidget)        

    def initParamTree(self):
        # Parameter tree configuration
        # we'll build a parameter tree here. 
        self.paramTree = ParameterTree()
        self.rootParam = Parameter.create(name='params', type='group', children=params)
        self.paramTree.setParameters(self.rootParam, showTop=False)
        self.paramTree.setParameters(Parameter.create(name='params', type='group', children=params), showTop=False)
        self.splitter.addWidget(self.paramTree)

    def updatePlot(self):
        self.plotWidget.clear()
        p = self.rootParam
        amplitude = p.child('Sin Wave Parameters', 'Amplitude').value()
        frequency = p.child('Sin Wave Parameters', 'Frequency').value()
        phase = p.child('Sin Wave Parameters', 'Phase').value()
        noise = p.child('Sin Wave Parameters', 'Noise').value()
        
        x = np.linspace(0, 2 * np.pi, 1000)
        y = amplitude * np.sin(frequency * x + phase) + np.random.normal(size=1000) * noise
        self.plotWidget.plot(x, y, pen='r')

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Set the 'Fusion' style for the application
    app.setStyle("Fusion")

    # Load and apply the stylesheet file
    styleSheetFile = QFile("styles.qss")  # Update the path to where your QSS file is
    if styleSheetFile.open(QFile.ReadOnly | QFile.Text):
        textStream = QTextStream(styleSheetFile)
        app.setStyleSheet(textStream.readAll())
    
    mainWindow = InstrumentControlGUI()
    mainWindow.show()
    sys.exit(app.exec())
