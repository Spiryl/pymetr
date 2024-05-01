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
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout,QDockWidget, QSplitter, QToolBar
from PySide6.QtWidgets import QWidget, QMainWindow, QTabWidget, QStackedWidget
from PySide6.QtWidgets import QMenuBar, QColorDialog, QComboBox, QPushButton
from PySide6.QtCore import Qt, QFile, QTextStream, QSize
from PySide6.QtCore import Signal, Qt

from pymetr.application.trace_plot import TracePlot
from pymetr.application.control_panels.trace_control_panel import TraceControlPanel
from pymetr.application.control_panels.display_panel import DisplayPanel
from pymetr.application.control_panels.marker_control_panel import MarkerControlPanel
from pymetr.application.control_panels.cursor_control_panel import CursorControlPanel
from pymetr.application.control_panels.measurement_control_panel import MeasurementControlPanel
from pymetr.application.control_panels.calculation_control_panel import CalculationControlPanel
from pymetr.application.control_panels.instrument_control_panel import InstrumentControlPanel
from pymetr.application.control_panels.console_panel import ConsolePanel
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

class QuickToolbar(QToolBar):
    plotModeChanged = Signal(str)
    roiPlotToggled = Signal(bool)
    testTraceClicked = Signal()
    screenshotClicked = Signal()
    highlightColorChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.color_palette = ['#5E57FF', '#4BFF36', '#F23CA6', '#FF9535', '#02FEE4', '#2F46FA', '#FFFE13', '#55FC77']

        spacer = QWidget()
        spacer.setFixedSize(20, 20)  # Set the desired spacing (width, height)
        self.addWidget(spacer)

        self.color_picker_button = QPushButton()
        self.color_picker_button.setStyleSheet("background-color: #5E57FF; width: 20px; height: 20px;")
        self.color_picker_button.clicked.connect(self.show_color_dialog)
        self.addWidget(self.color_picker_button)

        self.addSeparator()

        self.plot_mode_combo_box = QComboBox()
        self.plot_mode_combo_box.addItems(["Single", "Stack", "Run"])
        self.plot_mode_combo_box.currentTextChanged.connect(self.on_plot_mode_changed)
        self.addWidget(self.plot_mode_combo_box)

        self.addSeparator()

        self.roi_plot_action = self.addAction(QIcon("path/to/roi_plot_icon.png"), "Region Plot")
        self.roi_plot_action.setCheckable(True)
        self.roi_plot_action.toggled.connect(self.on_roi_plot_toggled)

        self.screenshot_action = self.addAction(QIcon("path/to/screenshot_icon.png"), "Screenshot")
        self.screenshot_action.triggered.connect(self.on_screenshot_clicked)

        self.test_trace_action = self.addAction(QIcon("path/to/test_trace_icon.png"), "Test Trace")
        self.test_trace_action.triggered.connect(self.on_test_trace_clicked)

    def on_color_changed(self, color):
        self.highlightColorChanged.emit(color)

    def on_plot_mode_changed(self, plot_mode):
        self.plotModeChanged.emit(plot_mode)

    def on_roi_plot_toggled(self, checked):
        self.roiPlotToggled.emit(checked)

    def on_screenshot_clicked(self):
        self.screenshotClicked.emit()

    def on_test_trace_clicked(self):
        self.testTraceClicked.emit()

    def show_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            new_color = color.name()
            self.color_picker_button.setStyleSheet(f"background-color: {new_color}; width: 20px; height: 20px;")
            self.update_stylesheet(new_color)

    def update_stylesheet(self, new_color):
        # Read the current stylesheet
        with open("pymetr/application/styles.qss", "r") as f:
            stylesheet = f.read()

        # Replace the old highlight color with the new color
        old_color = "#5E57FF"
        stylesheet = stylesheet.replace(old_color, new_color)

        # Set the updated stylesheet on the application
        app = pg.mkQApp()  # Get the application instance
        app.setStyleSheet(stylesheet)

class PyMetrMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()  # Call the __init__ method of the base class (QMainWindow)

        self.setWindowTitle("PyMetr - Instrument Control")
        self.setGeometry(100, 100, 1200, 800)

        # Create an instance of the MainMenuBar
        self.menuBar = MainMenuBar(self)
        self.setMenuBar(self.menuBar)

        # Create the toolbar
        self.toolbar = QToolBar("Control Toggles", self)
        self.toolbar.setOrientation(Qt.Vertical)
        self.toolbar.setIconSize(QSize(35, 35))  # Set the icon size for all actions in the toolbar
        self.toolbar.setMovable(False)  # Make the toolbar fixed
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)

        # # Style the toolbar and apply spacing programmatically
        # self.toolbar.setStyleSheet("""
        #     QToolBar { background-color: #2A2A2A; }
        #     QToolButton { border: none; padding: 8px; }
        #     QToolButton:hover { background-color: #3E3E3E; border: 1px solid #5E57FF; }
        # """)

        spacer = QWidget()
        spacer.setFixedSize(20, 20)  # Set the desired spacing (width, height)
        self.toolbar.addWidget(spacer)

        # spacer = QWidget()
        # spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.toolbar.addWidget(spacer)

        # Initialize the dictionary to track toggle actions
        self.toggle_actions = {}

        # Create the quick toolbar dock
        self.quick_toolbar_dock = QDockWidget("Quick Toolbar", self)
        self.quick_toolbar_dock.setAllowedAreas(Qt.TopDockWidgetArea)
        self.quick_toolbar_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.quick_toolbar_dock.setTitleBarWidget(QWidget())  # Hide the title bar

        # Create the quick toolbar
        self.quick_toolbar = QuickToolbar(self)
        self.quick_toolbar_dock.setWidget(self.quick_toolbar)
        self.addDockWidget(Qt.TopDockWidgetArea, self.quick_toolbar_dock)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

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
        self.console_panel = ConsolePanel()

        self.control_panel_stack.addWidget(self.trace_control_panel)
        self.control_panel_stack.addWidget(self.marker_control_panel)
        self.control_panel_stack.addWidget(self.cursor_control_panel)
        self.control_panel_stack.addWidget(self.measurement_control_panel)
        self.control_panel_stack.addWidget(self.calculation_control_panel)
        self.control_panel_stack.addWidget(self.instrument_control_panel)
        self.control_panel_stack.addWidget(self.display_panel)
        self.control_panel_stack.addWidget(self.console_panel)

        self.control_panel_layout.addWidget(self.control_panel_stack)
        self.control_panel_widget = QWidget()
        self.control_panel_widget.setLayout(self.control_panel_layout)
        self.control_panel_height = 301  # TODO: Move to application state class

        # Adding toggle actions for all panels
        self.add_toolbar_action("Instruments", "pymetr/application/icons/instruments.png", self.instrument_control_panel)
        self.add_toolbar_action("Traces", "pymetr/application/icons/traces.png", self.trace_control_panel)
        self.add_toolbar_action("Markers", "pymetr/application/icons/markers.png", self.marker_control_panel)
        self.add_toolbar_action("Cursors", "pymetr/application/icons/cursors.png", self.cursor_control_panel)
        self.add_toolbar_action("Measurements", "pymetr/application/icons/measurements.png", self.measurement_control_panel)
        self.add_toolbar_action("Calculations", "pymetr/application/icons/calculations.png", self.calculation_control_panel)
        self.add_toolbar_action("Plot Display", "pymetr/application/icons/plot.png", self.display_panel)
        self.add_toolbar_action("Console", "pymetr/application/icons/console.png", self.console_panel)

        # --- Main Area Layout ---
        main_area_layout = QHBoxLayout()

        # --- Control Panel Splitter ---
        self.control_panel_splitter = QSplitter(Qt.Vertical)
        self.control_panel_splitter.addWidget(self.trace_plot)
        self.control_panel_splitter.addWidget(self.control_panel_widget)
        main_area_layout.addWidget(self.control_panel_splitter, stretch=1)
        self.control_panel_splitter.splitterMoved.connect(self.update_control_panel_height)
        handle_width = 6
        self.control_panel_splitter.setHandleWidth(handle_width)

        # --- Instrument Tab Widget ---
        self.instrument_tab_widget = QTabWidget(self)
        self.instrument_tab_widget.setTabPosition(QTabWidget.East)
        self.instrument_tab_widget.setMovable(True)
        self.instrument_tab_widget.setDocumentMode(True)
        self.instrument_tab_widget.setTabBarAutoHide(True)  # Hide the tab bar when only one tab is open
        self.instrument_tab_widget.setTabsClosable(False)  # Disable the close button on tabs
        
        main_area_layout.addWidget(self.instrument_tab_widget, stretch=0)

        self.main_layout.addLayout(main_area_layout, stretch=1)

        self.control_panel_stack.setCurrentWidget(self.instrument_control_panel)
        self.connect_signals()

    def update_control_panel_height(self, pos, index):
        if index == 1:
            self.control_panel_height = self.control_panel_splitter.sizes()[1]

    def add_toolbar_action(self, label, icon_path, panel):
        action = QAction(QIcon(icon_path), label, self)
        action.setCheckable(True)
        action.toggled.connect(lambda checked, p=panel, a=action: self.toggle_panel(p, checked, a))
        self.toolbar.addAction(action)
        self.toggle_actions[label] = action

    def toggle_panel(self, panel, checked, action):
        if checked:
            self.control_panel_stack.setCurrentWidget(panel)
            self.control_panel_widget.show()
            # Uncheck other actions
            for other_label, other_action in self.toggle_actions.items():
                if other_action is not action:
                    other_action.setChecked(False)
            logging.debug(f"Panel {panel} shown, all other panels hidden.")
        else:
            # Check if any action is still checked, if not hide the control panel widget
            if not any(a.isChecked() for a in self.toggle_actions.values()):
                self.control_panel_widget.hide()
                logging.debug("All panels are now hidden.")

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

        self.quick_toolbar.plotModeChanged.connect(self.trace_manager.set_plot_mode)
        self.quick_toolbar.roiPlotToggled.connect(self.trace_plot.on_roi_plot_enabled)
        self.quick_toolbar.roiPlotToggled.connect(self.trace_manager.emit_trace_data)
        self.quick_toolbar.testTraceClicked.connect(self.trace_manager.add_random_trace)
        self.quick_toolbar.screenshotClicked.connect(self.trace_plot.capture_screenshot)

        self.instrument_control_panel.instrument_connected.connect(self.on_instrument_connected)
        self.instrument_control_panel.instrument_disconnected.connect(self.on_instrument_disconnected)
        self.instrument_control_panel.no_instruments_connected.connect(self.hide_instrument_dock)

    def on_instrument_connected(self, unique_id):
        logger.debug(f"Instrument connected with unique ID: {unique_id}")
        instrument = self.instrument_manager.instruments[unique_id]
        instrument['instance'].set_unique_id(unique_id)  # Set the unique ID on the instrument instance

        instrument_panel = InstrumentInterface(self.instrument_manager)
        instrument_panel.setup_interface(instrument, unique_id)

        # Connect the signals
        instrument_panel.continuous_mode_changed.connect(self.trace_plot.set_continuous_mode)
        instrument_panel.plot_update_requested.connect(self.trace_plot.update_plot)
        instrument_panel.traceDataReady.connect(self.trace_manager.add_trace)
        self.quick_toolbar.plotModeChanged.connect(instrument_panel.set_plot_mode)
        self.trace_plot.finished_update.connect(instrument['instance'].set_ready_for_data)

        # Create a new tab and set the widget as the instrument_widget
        self.instrument_tab_widget.addTab(instrument_panel, unique_id)

        # Create a new console tab for the instrument
        self.console_panel.add_instrument_tab(unique_id)
        logger.debug(f"Console tab added for instrument with unique ID: {unique_id}")
 
        # Connect the signals for write and query operations
        self.console_panel.commandIssued.connect(lambda unique_id, command: self.handle_command(unique_id, command))
        self.console_panel.queryIssued.connect(lambda unique_id, query: self.handle_query(unique_id, query))

        # Connect the signals for write and read operations
        instrument['instance'].commandSent.connect(lambda unique_id, command: self.console_panel.display_response(unique_id, f">>{command}"))
        instrument['instance'].responseReceived.connect(lambda unique_id, response: self.console_panel.display_response(unique_id, f"<<{response}"))
        logger.debug(f"Signals connected for instrument with unique ID: {unique_id}")
        
    def on_instrument_disconnected(self, unique_id):
        logger.debug(f"Instrument {unique_id} disconnected.")
        self.instrument_control_panel.remove_instrument_interface(unique_id)

        # Remove the tab for the disconnected instrument
        for i in range(self.instrument_tab_widget.count()):
            if self.instrument_tab_widget.tabText(i) == unique_id:
                # Remove the widget from the tab
                widget = self.instrument_tab_widget.widget(i)
                self.instrument_tab_widget.removeTab(i)
                widget.deleteLater()  # Delete the widget
                break

        if not self.instrument_tab_widget.count():
            self.hide_instrument_dock()

    def handle_command(self, unique_id, command):
        instrument = self.instrument_manager.instruments[unique_id]
        instrument['instance'].write(command)

    def handle_query(self, unique_id, query):
        instrument = self.instrument_manager.instruments[unique_id]
        response = instrument['instance'].query(query)

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
            # Remove all tabs from the QTabWidget
            self.instrument_tab_widget.clear()
            self.instrument_dock.hide()

    def check_instrument_dock(self, unique_id):
        if self.instrument_tab_widget:
            for i in range(self.instrument_tab_widget.count()):
                if self.instrument_tab_widget.tabText(i) == unique_id:
                    self.instrument_tab_widget.removeTab(i)
                    break
            if not self.instrument_tab_widget.count():
                self.hide_instrument_dock()

    def on_continuous_mode_changed(self, enabled):
        if enabled:
            self.trace_manager.traceDataChanged.disconnect(self.trace_panel.update_parameter_tree)
            # Disconnect the traceDataChanged signal when in continuous mode
            # self.trace_manager.traceDataChanged.disconnect(self.trace_plot.update_plot)
        else:
            self.trace_manager.traceDataChanged.connect(self.trace_panel.update_parameter_tree)
            # Reconnect the traceDataChanged signal when not in continuous mode
            # self.trace_manager.traceDataChanged.connect(self.trace_plot.update_plot)

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