# pymetr/application/control_dock.py
from PySide6.QtWidgets import QWidget

class MeasurementControlPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # TODO: Implement MeasurementControlPanel