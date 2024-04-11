import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np
import random

class TraceDock(QtWidgets.QDockWidget):
    newTraceDataReceived = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super(TraceDock, self).__init__("Trace Settings", parent)
        self.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)

        self.dockWidget = QtWidgets.QWidget()
        self.dockLayout = QtWidgets.QVBoxLayout(self.dockWidget)

        self.plotModeComboBox = QtWidgets.QComboBox()
        self.plotModeComboBox.addItems(["Add", "Replace"])
        self.plotModeComboBox.currentIndexChanged.connect(self.onPlotModeChanged)
        self.dockLayout.addWidget(self.plotModeComboBox)

        self.traceModeComboBox = QtWidgets.QComboBox()
        self.traceModeComboBox.addItems(["Main Plot", "Multiple Plots"])
        self.traceModeComboBox.currentIndexChanged.connect(self.onTraceModeChanged)
        self.dockLayout.addWidget(self.traceModeComboBox)

        self.traceTreeWidget = QtWidgets.QTreeWidget()
        self.traceTreeWidget.setColumnCount(4)
        self.traceTreeWidget.setHeaderLabels(["Trace", "Visible", "Color", "Plot Mode"])
        self.dockLayout.addWidget(self.traceTreeWidget)

        self.setWidget(self.dockWidget)
        self.traceData = {}

    def onPlotModeChanged(self, index):
        plotMode = self.plotModeComboBox.itemText(index)
        if plotMode == "Replace":
            self.traceTreeWidget.clear()
            self.traceData = {}
        self.newTraceDataReceived.emit(self.traceData)

    def onTraceModeChanged(self, index):
        self.newTraceDataReceived.emit(self.traceData)

    def onNewTraceData(self, data):
        self.traceData.update(data)
        self.updateTraceTreeWidget()

    def updateTraceTreeWidget(self):
        self.traceTreeWidget.clear()
        for traceId, traceInfo in self.traceData.items():
            color = traceInfo.get('color', pg.intColor(random.randint(0, 255)))
            visible = traceInfo.get('visible', True)
            plotMode = traceInfo.get('plotMode', 'Main Plot')

            traceItem = QtWidgets.QTreeWidgetItem([traceId, str(visible), pg.mkColor(color).name(), plotMode])
            self.traceTreeWidget.addTopLevelItem(traceItem)

        self.newTraceDataReceived.emit(self.traceData)

class TraceGeneratorDock(QtWidgets.QDockWidget):
    newTraceDataGenerated = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super(TraceGeneratorDock, self).__init__("Trace Generator", parent)
        self.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)

        self.dockLayout = QtWidgets.QVBoxLayout()
        self.dockWidget = QtWidgets.QWidget()
        self.dockWidget.setLayout(self.dockLayout)

        self.numTracesSpinBox = QtWidgets.QSpinBox()
        self.numTracesSpinBox.setMinimum(1)
        self.numTracesSpinBox.setMaximum(10)
        self.numTracesSpinBox.setValue(1)
        self.dockLayout.addWidget(self.numTracesSpinBox)

        self.addTraceButton = QtWidgets.QPushButton("Add Trace(s)")
        self.addTraceButton.clicked.connect(self.generateTraces)
        self.dockLayout.addWidget(self.addTraceButton)

        self.setWidget(self.dockWidget)

    def generateTraces(self):
        numTraces = self.numTracesSpinBox.value()
        traceData = {}
        for i in range(numTraces):
            traceId = f'Trace {i + 1}'
            color = pg.intColor(random.randint(0, 255))
            data = np.random.normal(0, 1, 100)
            traceData[traceId] = {'data': data, 'color': color}
        self.newTraceDataGenerated.emit(traceData)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trace Plotter")
        self.setGeometry(100, 100, 800, 600)

        self.traceGeneratorDock = TraceGeneratorDock(self)
        self.traceGeneratorDock.newTraceDataGenerated.connect(self.onNewTraceData)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.traceGeneratorDock)

        self.traceDock = TraceDock(self)
        self.traceDock.newTraceDataReceived.connect(self.updatePlot)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.traceDock)

        self.plotWidget = pg.PlotWidget()
        self.setCentralWidget(self.plotWidget)
        self.plotItem = self.plotWidget.getPlotItem()

        self.traces = []
        self.axes = []

    def onNewTraceData(self, data):
        self.traceDock.onNewTraceData(data)

    def updatePlot(self, traceData):
        self.plotItem.clear()
        self.traces = []
        self.axes = []

        traceMode = self.traceDock.traceModeComboBox.currentText()

        for traceId, traceInfo in traceData.items():
            visible = traceInfo.get('visible', True)
            color = traceInfo.get('color', pg.intColor(random.randint(0, 255)))
            plotMode = traceInfo.get('plotMode', 'Main Plot')
            data = traceInfo.get('data', [])

            if visible:
                pen = pg.mkPen(color, width=2)

                if traceMode == "Main Plot" or plotMode == 'Main Plot':
                    curve = self.plotItem.plot(data, pen=pen, name=traceId)
                    self.traces.append(curve)
                else:
                    axisIndex = len(self.axes)
                    axis = pg.AxisItem("right")
                    axis.setLabel(traceId)
                    self.plotItem.layout.addItem(axis, 2, axisIndex + 2)
                    axis.linkToView(self.plotItem.vb)
                    self.plotItem.vb.sigResized.connect(axis.updateAutoFillBackground)
                    self.axes.append(axis)

                    viewBox = pg.ViewBox()
                    viewBox.setXLink(self.plotItem)
                    axis.linkToView(viewBox)
                    viewBox.addItem(pg.PlotCurveItem(data, pen=pen, name=traceId))
                    self.plotWidget.scene().addItem(viewBox)
                    self.traces.append(viewBox)

                    viewBox.sigRangeChanged.connect(lambda _, vb=viewBox, traceId=traceId: self.handle_view_box_range_changed(vb, traceId, traceData))

        self.plotItem.autoRange()
        self.plotItem.vb.sigResized.connect(self.updateViewBoxes)

    def handle_view_box_range_changed(self, view_box, traceId, traceData):
        if isinstance(view_box, pg.ViewBox):
            _, y_range = view_box.viewRange()
            traceData[traceId]['verticalScale'] = y_range

    def updateViewBoxes(self):
        for viewBox in self.traces:
            if isinstance(viewBox, pg.ViewBox):
                viewBox.setGeometry(self.plotItem.vb.sceneBoundingRect())
                viewBox.linkedViewChanged(self.plotItem.vb, viewBox.XAxis)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    mainWindow = MainWindow()
    mainWindow.show()
    app.exec()