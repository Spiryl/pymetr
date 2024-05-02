import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)
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

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout,QDockWidget, QSplitter, QToolBar, QToolButton
from PySide6.QtWidgets import QWidget, QMainWindow, QTabWidget, QLabel, QSpacerItem, QSizePolicy
from PySide6.QtWidgets import QMenuBar, QColorDialog, QComboBox, QPushButton, QStatusBar
from PySide6.QtCore import Qt, QFile, QTextStream, QSize
from PySide6.QtCore import Signal, Qt, QRectF, QPoint
from PySide6.QtGui import QAction, QIcon, QColor, QPainter, QPainterPath, QBrush, QPen

from pymetr.application.trace_plot import TracePlot
from pymetr.application.control_panel import ControlPanel
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
        super(QuickToolbar, self).__init__(parent)
        self.setMovable(False)  # Ensure toolbar cannot be moved
        self.setIconSize(QSize(20, 20))  # Set a suitable icon size
        self.color_palette = ['#5E57FF', '#4BFF36', '#F23CA6', '#FF9535', '#02FEE4', '#2F46FA', '#FFFE13', '#55FC77']

        spacer = QWidget()
        spacer.setFixedSize(10, 10)  # Set the desired spacing (width, height)
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

        self.roi_plot_action = self.addAction(QIcon("pymetr/application/icons/zoom_in_g.png"), "Region Plot")
        self.roi_plot_action.setCheckable(True)
        self.roi_plot_action.toggled.connect(self.on_roi_plot_toggled)

        self.screenshot_action = self.addAction(QIcon("pymetr/application/icons/capture_g.png"), "Screenshot")
        self.screenshot_action.triggered.connect(self.on_screenshot_clicked)

        self.test_trace_action = self.addAction(QIcon("pymetr/application/icons/lab_g.png"), "Test Trace")
        self.test_trace_action.triggered.connect(self.on_test_trace_clicked)

    def on_plot_mode_changed(self, plot_mode):
        self.plotModeChanged.emit(plot_mode)

    def on_roi_plot_toggled(self, checked):
        if checked:
            self.roi_plot_action.setIcon(QIcon("pymetr/application/icons/zoom_in.png"))
        else:
            self.roi_plot_action.setIcon(QIcon("pymetr/application/icons/zoom_in_g.png"))
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
            self.highlightColorChanged.emit(new_color)

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

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super(TitleBar, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 0, 5, 0)
        self.layout.setSpacing(10)

        # Standard label
        self.title_label = QLabel("PyMetr - Instrument Control")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Tool buttons for additional functionalities
        self.settings_button = QToolButton()
        self.settings_button.setText("Settings")  # Example button
        self.settings_button.clicked.connect(self.on_settings_clicked)

        # Spacer that pushes the control buttons to the right
        spacer = QSpacerItem(40, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Window control buttons
        self.minimize_button = QToolButton()
        self.minimize_button.setText("V")
        self.maximize_button = QToolButton()
        self.maximize_button.setText("[]")
        self.close_button = QToolButton()
        self.close_button.setText("X")

        self.minimize_button.clicked.connect(parent.showMinimized)
        self.maximize_button.clicked.connect(parent.showMaximized)
        self.close_button.clicked.connect(parent.close)

        # Adding widgets to the layout
        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.settings_button)  # Add your tool button
        self.layout.addSpacerItem(spacer)
        self.layout.addWidget(self.minimize_button)
        self.layout.addWidget(self.maximize_button)
        self.layout.addWidget(self.close_button)

        self.setLayout(self.layout)

    def on_settings_clicked(self):
        print("Settings button clicked")  # Placeholder for settings action

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start = self.mapToGlobal(event.position().toPoint())
            self.pressing = True

    def mouseMoveEvent(self, event):
        if self.pressing and event.buttons() & Qt.LeftButton:
            end = self.mapToGlobal(event.position().toPoint())
            movement = end - self.start
            self.parent().move(self.parent().pos() + movement)
            self.start = end

    def mouseReleaseEvent(self, event):
        self.pressing = False

class PyMetrMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(100, 100, 1200, 800)
        self.setAttribute(Qt.WA_TranslucentBackground)  # Enable transparency

        # Custom Title Bar
        self.title_bar = TitleBar(self)
        self.setMenuWidget(self.title_bar)  # Adding custom title bar as the menu widget

        # Quick Toolbar Setup
        self.quick_toolbar = QuickToolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self.quick_toolbar)
        self.quick_toolbar.setGeometry(0, self.title_bar.height(), self.width(), 50)


        # Create the toolbar
        self.control_panel_tool_bar = QToolBar("Control Toggles", self)
        self.control_panel_tool_bar.setOrientation(Qt.Vertical)
        self.control_panel_tool_bar.setIconSize(QSize(32, 32))  # Set the icon size for all actions in the toolbar
        self.control_panel_tool_bar.setMovable(False)  # Make the toolbar fixed

        self.addToolBar(Qt.LeftToolBarArea, self.control_panel_tool_bar)

        spacer = QWidget()
        spacer.setFixedSize(10, 10)  # Set the desired spacing (width, height)
        self.control_panel_tool_bar.addWidget(spacer)

        # Initialize the dictionary to track toggle actions
        self.toggle_actions = {}

        self.central_widget = QWidget()
        self.central_widget.setStyleSheet("background-color: #1E1E1E;")  
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # --- Plot Displays ---
        self.instrument_manager = InstrumentManager()
        self.trace_manager = TraceManager()
        self.trace_plot = TracePlot(self.trace_manager, self)

        # --- Control Panels ---
        self.control_panel_layout = QVBoxLayout()
        self.control_panel = ControlPanel(self.trace_manager, self.instrument_manager, self.trace_plot, self)
        self.control_panel_widget = QWidget()
        self.control_panel_widget.setLayout(self.control_panel.control_panel_layout)
        self.control_panel_height = 301  # TODO: Move to application state class


        # Adding toggle actions for all panels
        self.add_toolbar_action("Instruments", "pymetr/application/icons/instruments.png", self.control_panel.instrument_control_panel)
        self.add_toolbar_action("Traces", "pymetr/application/icons/traces.png", self.control_panel.trace_control_panel)
        self.add_toolbar_action("Markers", "pymetr/application/icons/markers.png", self.control_panel.marker_control_panel)
        self.add_toolbar_action("Cursors", "pymetr/application/icons/cursors.png", self.control_panel.cursor_control_panel)
        self.add_toolbar_action("Measurements", "pymetr/application/icons/measurements.png", self.control_panel.measurement_control_panel)
        self.add_toolbar_action("Calculations", "pymetr/application/icons/calculations.png", self.control_panel.calculation_control_panel)
        self.add_toolbar_action("Plot Display", "pymetr/application/icons/plot.png", self.control_panel.display_control_panel)
        self.add_toolbar_action("Console", "pymetr/application/icons/console.png", self.control_panel.console_control_panel)

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
        self.control_panel.control_panel_stack.setCurrentWidget(self.control_panel.instrument_control_panel)

        # Create and add the status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.quick_toolbar.plotModeChanged.connect(self.trace_manager.set_plot_mode)
        self.quick_toolbar.roiPlotToggled.connect(self.trace_plot.on_roi_plot_enabled)
        self.quick_toolbar.roiPlotToggled.connect(self.trace_manager.emit_trace_data)
        self.quick_toolbar.testTraceClicked.connect(self.trace_manager.add_random_trace)
        self.quick_toolbar.screenshotClicked.connect(self.trace_plot.capture_screenshot)
        self.quick_toolbar.highlightColorChanged.connect(self.trace_manager.set_highlight_color)
        self.quick_toolbar.highlightColorChanged.connect(self.trace_plot.set_highlight_color)

        self.control_panel.instrument_control_panel.instrument_connected.connect(self.on_instrument_connected)
        self.control_panel.instrument_control_panel.instrument_disconnected.connect(self.on_instrument_disconnected)
        self.control_panel.instrument_control_panel.no_instruments_connected.connect(self.hide_instrument_dock)

    def update_control_panel_height(self, pos, index):
        if index == 1:
            self.control_panel_height = self.control_panel_splitter.sizes()[1]

    def add_toolbar_action(self, label, icon_path, panel):
        action = QAction(QIcon(icon_path), label, self)
        action.setCheckable(True)
        action.toggled.connect(lambda checked, p=panel, a=action: self.toggle_panel(p, checked, a))
        self.control_panel_tool_bar.addAction(action)
        self.toggle_actions[label] = action

    def toggle_panel(self, panel, checked, action):
        if checked:
            self.control_panel.control_panel_stack.setCurrentWidget(panel)
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
        self.control_panel.console_control_panel.add_instrument_tab(unique_id)
        logger.debug(f"Console tab added for instrument with unique ID: {unique_id}")
 
        # Connect the signals for write and query operations
        self.control_panel.console_control_panel.commandIssued.connect(lambda unique_id, command: self.handle_command(unique_id, command))
        self.control_panel.console_control_panel.queryIssued.connect(lambda unique_id, query: self.handle_query(unique_id, query))

        # Connect the signals for write and read operations
        instrument['instance'].commandSent.connect(lambda unique_id, command: self.control_panel.console_control_panel.display_response(unique_id, f">>{command}"))
        instrument['instance'].responseReceived.connect(lambda unique_id, response: self.control_panel.console_control_panel.display_response(unique_id, f"<<{response}"))
        logger.debug(f"Signals connected for instrument with unique ID: {unique_id}")
        self.status_bar.showMessage(f"Instrument {unique_id} connected", 3000)
        
    def on_instrument_disconnected(self, unique_id):
        logger.debug(f"Instrument {unique_id} disconnected.")
        self.control_panel.instrument_control_panel.remove_instrument_interface(unique_id)

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

        instrument_interface = self.control_panel.instrument_control_panel.add_instrument_interface(unique_id)
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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 10, 10)  # Rounded corners with a radius of 10 pixels
        painter.setClipPath(path)
        painter.fillRect(self.rect(), QColor("#2A2A2A"))  # Fill the window with the main background color


    # def mousePressEvent(self, event):
    #     pos = event.position().toPoint()  # Updated for deprecation
    #     if event.button() == Qt.LeftButton and self.title_bar_rect().contains(pos):
    #         self.dragging = True
    #         self.drag_position = event.globalPosition().toPoint() - self.pos()
    #         event.accept()

    # def mouseMoveEvent(self, event):
    #     if event.buttons() & Qt.LeftButton and self.dragging:
    #         self.move(event.globalPosition().toPoint() - self.drag_position)
    #         event.accept()

    # def mouseReleaseEvent(self, event):
    #     if event.button() == Qt.LeftButton:
    #         self.dragging = False

    # def mouseDoubleClickEvent(self, event):
    #     if event.button() == Qt.LeftButton and self.close_button_rect().contains(event.pos()):
    #         self.close()

    # def title_bar_rect(self):
    #     return QRectF(0, 0, self.width(), self.title_bar_height)

    # def close_button_rect(self):
    #     return QRectF(self.width() - 30, 0, 30, self.title_bar_height)

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