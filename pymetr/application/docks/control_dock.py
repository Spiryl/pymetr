# pymetr/application/control_dock.py
from PySide6.QtWidgets import QDockWidget, QTabWidget, QWidget, QPushButton, QVBoxLayout
from PySide6.QtCore import Qt

from pymetr.application.control_panels.trace_control_panel import TraceControlPanel
from pymetr.application.control_panels.marker_control_panel import MarkerControlPanel
from pymetr.application.control_panels.cursor_control_panel import CursorControlPanel
from pymetr.application.control_panels.measurement_control_panel import MeasurementControlPanel
from pymetr.application.control_panels.calculation_control_panel import CalculationControlPanel
from pymetr.application.control_panels.instrument_control_panel import InstrumentControlPanel

class ControlDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Control Panel", parent)
        self.setAllowedAreas(Qt.BottomDockWidgetArea)

        self.tab_widget = QTabWidget()
        
        self.trace_control_Panel = TraceControlPanel()
        self.marker_control_Panel = MarkerControlPanel()
        self.cursor_control_Panel = CursorControlPanel()
        self.measurement_control_Panel = MeasurementControlPanel()
        self.calculation_control_Panel = CalculationControlPanel()
        self.instrument_control_Panel = InstrumentControlPanel()

        self.tab_widget.addTab(self.trace_control_Panel, "Traces")
        self.tab_widget.addTab(self.marker_control_Panel, "Markers")
        self.tab_widget.addTab(self.cursor_control_Panel, "Cursors")
        self.tab_widget.addTab(self.measurement_control_Panel, "Measurements")
        self.tab_widget.addTab(self.calculation_control_Panel, "Calculations")
        self.tab_widget.addTab(self.instrument_control_Panel, "Instruments")

        self.button_layout = QVBoxLayout()
        self.add_toggle_button("Traces", self.trace_control_Panel)
        self.add_toggle_button("Markers", self.marker_control_Panel)
        self.add_toggle_button("Cursors", self.cursor_control_Panel)
        self.add_toggle_button("Measurements", self.measurement_control_Panel)
        self.add_toggle_button("Calculations", self.calculation_control_Panel)
        self.add_toggle_button("Instruments", self.instrument_control_Panel)

        main_layout = QVBoxLayout()
        main_layout.addLayout(self.button_layout)
        main_layout.addWidget(self.tab_widget)

        container_widget = QWidget()
        container_widget.setLayout(main_layout)
        self.setWidget(container_widget)

    def add_toggle_button(self, label, Panel):
        button = QPushButton(label)
        button.setCheckable(True)
        button.clicked.connect(lambda checked: self.toggle_Panel(Panel, checked))
        self.button_layout.addWidget(button)

    def toggle_Panel(self, Panel, checked):
        index = self.tab_widget.indexOf(Panel)
        if checked:
            self.tab_widget.setCurrentIndex(index)
        else:
            self.tab_widget.setCurrentIndex(-1)  # Hide all tabs