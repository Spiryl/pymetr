import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.getLogger('pyvisa').setLevel(logging.CRITICAL)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(name)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

import sys
import os
os.environ['PYQTGRAPH_QT_LIB'] = 'PySide6'

import pyqtgraph as pg
pg.setConfigOptions(antialias=True)

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QDockWidget, QSplitter
from PySide6.QtWidgets import QWidget, QMainWindow, QTabWidget, QStackedWidget
from PySide6.QtWidgets import QMenuBar, QPushButton
from PySide6.QtCore import Qt, QFile, QTextStream, QSize

from pymetr.application.control_panels.quick_panel import QuickPanel
from pymetr.application.trace_plot import TracePlot
from pymetr.application.control_panels.trace_control_panel import TraceControlPanel
from pymetr.application.control_panels.display_panel import DisplayPanel
from pymetr.application.control_panels.marker_control_panel import MarkerControlPanel
from pymetr.application.control_panels.cursor_control_panel import CursorControlPanel
from pymetr.application.control_panels.measurement_control_panel import MeasurementControlPanel
from pymetr.application.control_panels.calculation_control_panel import CalculationControlPanel
from pymetr.application.control_panels.instrument_control_panel import InstrumentControlPanel
from pymetr.application.managers.instrument_manager import InstrumentManager
from pymetr.application.factories.instrument_interface import InstrumentInterface
from pymetr.application.managers.trace_manager import TraceManager

# TODO:  Build out MainMenuBar into its own class.
class MainMenuBar(QMenuBar):
    def __init__(self, parent=None):
        super(MainMenuBar, self).__init__(parent)

        # File menu
        self.fileMenu = self.addMenu("&File")
        self.toolMenu = self.addMenu("&Tools")
        self.settingsMenu = self.addMenu("&Settings")

        # Add actions to the file menu
        self.setupFileMenuActions(parent)

    def setupFileMenuActions(self, parent):
        exportPlotAction = QAction("&Export Plot", self)
        exportPlotAction.triggered.connect(self.exportPlot)
        self.fileMenu.addAction(exportPlotAction)

        generateReportAction = QAction("&Generate Report", self)
        generateReportAction.triggered.connect(self.generateReport)
        self.fileMenu.addAction(generateReportAction)

        importTraceDataAction = QAction("&Import Trace Data", self)
        importTraceDataAction.triggered.connect(self.importTraceData)
        self.fileMenu.addAction(importTraceDataAction)

    # Placeholder methods for menu actions
    def exportPlot(self):
        # Placeholder for export plot logic
        print("Exporting plot...")

    def generateReport(self):
        # Placeholder for generate report logic
        print("Generating report...")

    def importTraceData(self):
        # Placeholder for import trace data logic
        print("Importing trace data...")

class PyMetrMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyMetr - Instrument Control")
        self.setGeometry(100, 100, 1200, 800)

        # Create an instance of the MainMenuBar
        self.menuBar = MainMenuBar(self)
        self.setMenuBar(self.menuBar)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # --- Quick Panel ---
        self.quick_panel = QuickPanel(self)
        self.main_layout.addWidget(self.quick_panel)

        # --- Plot Displays ---
        self.instrument_manager = InstrumentManager()
        self.trace_manager = TraceManager()
        self.trace_plot = TracePlot(self.trace_manager, self)

        # --- Control Panels ---
        self.control_panel_layout = QVBoxLayout()
        self.control_panel_stack = QStackedWidget()

        self.trace_control_panel = TraceControlPanel(self.trace_manager)
        self.marker_control_panel = MarkerControlPanel()
        self.cursor_control_panel = CursorControlPanel()
        self.measurement_control_panel = MeasurementControlPanel()
        self.calculation_control_panel = CalculationControlPanel()
        self.instrument_control_panel = InstrumentControlPanel(self.instrument_manager)
        self.display_panel = DisplayPanel(self.trace_plot)

        self.control_panel_stack.addWidget(self.trace_control_panel)
        self.control_panel_stack.addWidget(self.marker_control_panel)
        self.control_panel_stack.addWidget(self.cursor_control_panel)
        self.control_panel_stack.addWidget(self.measurement_control_panel)
        self.control_panel_stack.addWidget(self.calculation_control_panel)
        self.control_panel_stack.addWidget(self.instrument_control_panel)
        self.control_panel_stack.addWidget(self.display_panel)

        self.control_panel_layout.addWidget(self.control_panel_stack)
        self.control_panel_widget = QWidget()
        self.control_panel_widget.setLayout(self.control_panel_layout)
        self.control_panel_height = 301 # TODO: Move to application state class

        # --- Main Splitter ---
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.addWidget(self.trace_plot)
        self.main_splitter.addWidget(self.control_panel_widget)
        self.main_layout.addWidget(self.main_splitter)
        self.main_splitter.splitterMoved.connect(self.update_control_panel_height)

        handle_width = 6 
        self.main_splitter.setHandleWidth(handle_width)

        # Button bar dock widget setup
        self.button_bar_dock = QDockWidget("Control Toggles", self)
        self.button_bar_dock.setObjectName("toggleDock")  # Set a unique object name
        self.button_bar_dock.setAllowedAreas(Qt.LeftDockWidgetArea)
        self.button_bar_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)  # Make the dock static
        self.button_bar_dock.setTitleBarWidget(QWidget())  # Remove the title bar
        self.button_bar_dock.setFixedWidth(70)  # Set the fixed width of the dock

        self.button_bar_widget = QWidget()
        self.button_bar_layout = QVBoxLayout(self.button_bar_widget)
        self.setup_control_toggle_buttons()  # Setup toggle buttons within the button bar
        self.button_bar_dock.setWidget(self.button_bar_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.button_bar_dock)

        # --- Instrument Interface Dock ---
        self.instrument_dock = QDockWidget("Instrument Controls", self)
        self.instrument_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.instrument_tab_widget = QTabWidget()
        self.instrument_dock.setWidget(self.instrument_tab_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.instrument_dock)

        self.control_panel_stack.setCurrentWidget(self.instrument_control_panel)
        self.connect_signals()

        self.hide_instrument_dock()

    def setup_control_toggle_buttons(self):
        self.toggle_buttons_layout = self.button_bar_layout
        # self.button_bar_layout.addStretch(1)
        self.toggle_buttons = {}
        self.button_bar_layout.addStretch(1)
        self.add_toggle_button("Instruments", self.instrument_control_panel, "pymetr/application/icons/instruments.png")
        self.toggle_buttons[self.instrument_control_panel].setChecked(True)  # Set the "Instruments" button as initially checked
        self.add_toggle_button("Traces", self.trace_control_panel, "pymetr/application/icons/traces.png")
        self.add_toggle_button("Markers", self.marker_control_panel, "pymetr/application/icons/markers.png")
        self.add_toggle_button("Cursors", self.cursor_control_panel, "pymetr/application/icons/cursors.png")
        self.add_toggle_button("Measurements", self.measurement_control_panel, "pymetr/application/icons/measurements.png")
        self.add_toggle_button("Calculations", self.calculation_control_panel, "pymetr/application/icons/calculations.png")
        self.add_toggle_button("Plot Display", self.display_panel, "pymetr/application/icons/plot.png")
        self.add_toggle_button("Console", self.calculation_control_panel, "pymetr/application/icons/console.png")
        # self.button_bar_layout.addStretch(1)
        

        # --- Instrument Interface Dock ---
        self.instrument_dock = QDockWidget("Instrument Controls", self)
        self.instrument_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.instrument_tab_widget = QTabWidget()
        self.instrument_dock.setWidget(self.instrument_tab_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.instrument_dock)

        self.control_panel_stack.setCurrentWidget(self.instrument_control_panel)
        self.hide_instrument_dock()

    def update_control_panel_height(self, pos, index):
        if index == 1:
            self.control_panel_height = self.main_splitter.sizes()[1]

    def add_toggle_button(self, label, panel, icon_path):
        button = QPushButton()
        button.setCheckable(True)
        button.setIcon(QIcon(icon_path))
        button.setIconSize(QSize(45, 45))  # Adjust the icon size as needed
        button.setProperty("class", "toggle_button")  # Set a custom style class
        button.toggled.connect(lambda checked, panel=panel: self.toggle_panel(panel, checked))
        self.toggle_buttons_layout.addWidget(button)
        self.toggle_buttons[panel] = button

    def toggle_panel(self, panel, checked):
        print(f"Toggle panel: {panel}, checked={checked}")
        if checked:
            self.control_panel_stack.setCurrentWidget(panel)
            self.control_panel_widget.show()
            panel_height = self.control_panel_height
            print(f"Panel height: {panel_height}")

            # Adjust the splitter sizes to show the control panel
            self.main_splitter.setSizes([self.height() - panel_height, panel_height])

            # Uncheck other toggle buttons
            for other_panel, button in self.toggle_buttons.items():
                if other_panel != panel:
                    button.setChecked(False)
        else:
            # Check if any other toggle button is checked
            any_button_checked = any(button.isChecked() for button in self.toggle_buttons.values())

            if not any_button_checked:
                self.control_panel_stack.setCurrentIndex(-1)
                self.main_splitter.setSizes([self.height(), 0])
                print("Control panel hidden")

    def connect_signals(self):

        # --- Trace Manager  -------------------------------------
        self.trace_manager.traceDataChanged.connect(self.trace_plot.update_plot)

        self.trace_manager.traceVisibilityChanged.connect(self.trace_plot.update_trace_visibility)
        self.trace_manager.traceLabelChanged.connect(self.trace_plot.update_trace_label)
        self.trace_manager.traceColorChanged.connect(self.trace_plot.update_trace_color)
        self.trace_manager.traceLineThicknessChanged.connect(self.trace_plot.update_trace_line_thickness)
        self.trace_manager.traceLineStyleChanged.connect(self.trace_plot.update_trace_line_style)
        self.trace_manager.traceRemoved.connect(self.trace_plot.remove_trace)
        self.trace_manager.traceRemoved.connect(self.trace_control_panel.remove_trace)
        # self.trace_manager.tracesCleared.connect(self.trace_control_panel.clear_traces)
        self.trace_manager.tracesCleared.connect(self.trace_plot.clear_traces)

        self.quick_panel.plotModeChanged.connect(self.trace_manager.set_plot_mode)
        self.quick_panel.roiPlotToggled.connect(self.trace_plot.on_roi_plot_enabled)
        self.quick_panel.roiPlotToggled.connect(self.trace_manager.emit_trace_data)
        self.quick_panel.testTraceClicked.connect(self.trace_manager.add_random_trace)
        self.quick_panel.screenshotClicked.connect(self.trace_plot.capture_screenshot)


        self.instrument_control_panel.instrument_connected.connect(self.on_instrument_connected)
        self.instrument_control_panel.instrument_disconnected.connect(self.on_instrument_disconnected)
        self.instrument_control_panel.no_instruments_connected.connect(self.hide_instrument_dock)

    def on_instrument_connected(self, unique_id):
        logger.debug("Instrument connected")
        instrument = self.instrument_manager.instruments[unique_id]

        # Create a new dock widget for the instrument
        instrument_dock = QDockWidget(unique_id, self)
        instrument_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        instrument_dock.setMinimumWidth(250)

        # Create a new instrument panel for the connected instrument
        instrument_panel = InstrumentInterface(self.instrument_manager)
        instrument_panel.setup_interface(instrument, unique_id)
        instrument_panel.continuous_mode_changed.connect(self.trace_plot.set_continuous_mode)
        instrument_panel.plot_update_requested.connect(self.trace_plot.update_plot)
        instrument_panel.trace_data_ready.connect(self.trace_manager.add_trace)
        instrument_dock.setWidget(instrument_panel)

        self.addDockWidget(Qt.RightDockWidgetArea, instrument_dock)

        # Tabify the new dock widget with the previous dock widget (if any)
        if hasattr(self, 'last_instrument_dock'):
            self.tabifyDockWidget(self.last_instrument_dock, instrument_dock)

        # Set the new dock widget as the last instrument dock
        self.last_instrument_dock = instrument_dock
        self.quick_panel.plotModeChanged.connect(instrument_panel.set_plot_mode)

        # Critical re reset the ready for data.
        self.trace_plot.finished_update.connect(instrument['instance'].set_ready_for_data)

    def on_instrument_disconnected(self, unique_id):
        logger.debug(f"Instrument {unique_id} disconnected.")
        self.instrument_control_panel.remove_instrument_interface(unique_id)
        self.check_instrument_dock(unique_id)

    def show_instrument_dock(self, unique_id):
        if not self.instrument_dock:
            self.instrument_dock = QDockWidget("Instrument Controls", self)
            self.instrument_dock.setAllowedAreas(Qt.RightDockWidgetArea)
            self.instrument_tab_widget = QTabWidget()
            self.instrument_dock.setWidget(self.instrument_tab_widget)
            self.addDockWidget(Qt.RightDockWidgetArea, self.instrument_dock)

        instrument_interface = self.instrument_control_panel.add_instrument_interface(unique_id)
        self.instrument_tab_widget.addTab(instrument_interface, unique_id)

    def hide_instrument_dock(self):
        if self.instrument_dock:
            self.instrument_dock.hide()

    def check_instrument_dock(self, unique_id):
        if self.instrument_tab_widget:
            for i in range(self.instrument_tab_widget.count()):
                if self.instrument_tab_widget.tabText(i) == unique_id:
                    self.instrument_tab_widget.removeTab(i)
                    break
            if not self.instrument_tab_widget.count():
                self.hide_instrument_dock()

    # def on_continuous_mode_changed(self, enabled):
    #     if enabled:
    #         self.trace_manager.traceDataChanged.disconnect(self.trace_panel.update_parameter_tree)
    #         # Disconnect the traceDataChanged signal when in continuous mode
    #         # self.trace_manager.traceDataChanged.disconnect(self.trace_plot.update_plot)
    #     else:
    #         self.trace_manager.traceDataChanged.connect(self.trace_panel.update_parameter_tree)
    #         # Reconnect the traceDataChanged signal when not in continuous mode
    #         # self.trace_manager.traceDataChanged.connect(self.trace_plot.update_plot)

if __name__ == "__main__":

    sys.argv += ['-platform', 'windows:darkmode=2']
    app = pg.mkQApp("Dynamic Instrument Control Application")
    app.setStyle("Fusion")

    # Load and apply the stylesheet file
    styleSheetFile = QFile("pymetr/application/styles.qss")  # Update the path to where your QSS file is
    if styleSheetFile.open(QFile.ReadOnly | QFile.Text):
        textStream = QTextStream(styleSheetFile)
        app.setStyleSheet(textStream.readAll())

    mainWindow = PyMetrMainWindow()
    mainWindow.show()
    sys.exit(app.exec())