from PySide6.QtWidgets import QVBoxLayout, QStackedWidget, QWidget
from pymetr.application.control_panels.trace_control_panel import TraceControlPanel
from pymetr.application.control_panels.marker_control_panel import MarkerControlPanel
from pymetr.application.control_panels.cursor_control_panel import CursorControlPanel
from pymetr.application.control_panels.measurement_control_panel import MeasurementControlPanel
from pymetr.application.control_panels.calculation_control_panel import CalculationControlPanel
from pymetr.application.control_panels.instrument_control_panel import InstrumentControlPanel
from pymetr.application.control_panels.display_control_panel import DisplayControlPanel
from pymetr.application.control_panels.console_control_panel import ConsoleControlPanel

class ControlPanel(QWidget):
    def __init__(self, trace_manager, instrument_manager, trace_plot, parent=None):
        super().__init__(parent)

        self.control_panel_layout = QVBoxLayout()
        self.control_panel_stack = QStackedWidget()

        self.instrument_control_panel = InstrumentControlPanel(instrument_manager)
        self.trace_control_panel = TraceControlPanel(trace_manager)
        self.marker_control_panel = MarkerControlPanel()
        self.cursor_control_panel = CursorControlPanel()
        self.measurement_control_panel = MeasurementControlPanel()
        self.calculation_control_panel = CalculationControlPanel()
        self.display_control_panel = DisplayControlPanel(trace_plot)
        self.console_control_panel = ConsoleControlPanel()

        self.control_panel_stack.addWidget(self.instrument_control_panel)
        self.control_panel_stack.addWidget(self.trace_control_panel)
        self.control_panel_stack.addWidget(self.marker_control_panel)
        self.control_panel_stack.addWidget(self.cursor_control_panel)
        self.control_panel_stack.addWidget(self.measurement_control_panel)
        self.control_panel_stack.addWidget(self.calculation_control_panel)
        self.control_panel_stack.addWidget(self.display_control_panel)
        self.control_panel_stack.addWidget(self.console_control_panel)

        self.control_panel_layout.addWidget(self.control_panel_stack)
        self.setLayout(self.control_panel_layout)