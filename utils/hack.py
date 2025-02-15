import sys
from PySide6 import QtGui, QtCore

class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.centre = QtGui.QMainWindow(self)
        self.centre.setWindowFlags(QtCore.Qt.Widget)
        self.centre.setDockOptions(
            QtGui.QMainWindow.AnimatedDocks |
            QtGui.QMainWindow.AllowNestedDocks)
        self.setCentralWidget(self.centre)
        self.dockCentre1 = QtGui.QDockWidget(self.centre)
        self.dockCentre1.setWindowTitle('Centre 1')
        self.centre.addDockWidget(
            QtCore.Qt.LeftDockWidgetArea, self.dockCentre1)
        self.dockCentre2 = QtGui.QDockWidget(self.centre)
        self.dockCentre2.setWindowTitle('Centre 2')
        self.centre.addDockWidget(
            QtCore.Qt.RightDockWidgetArea, self.dockCentre2)
        self.dockLeft = QtGui.QDockWidget(self)
        self.dockLeft.setWindowTitle('Left')
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.dockLeft)
        self.dockRight = QtGui.QDockWidget(self)
        self.dockRight.setWindowTitle('Right')
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dockRight)
        self.menuBar().addMenu('File').addAction('Quit', self.close)

if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)
    window = MainWindow()
    window.setGeometry(500, 50, 600, 400)
    window.show()
    sys.exit(app.exec_())