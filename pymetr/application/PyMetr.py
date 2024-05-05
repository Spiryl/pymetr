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

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout,QDockWidget, QSplitter, QToolBar
from PySide6.QtWidgets import QWidget, QMainWindow, QTabWidget, QSizePolicy
from PySide6.QtWidgets import QColorDialog, QPushButton, QStatusBar
from PySide6.QtCore import Qt, QFile, QTextStream, QSize
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QColor, QPainter, QPainterPath

from pymetr.application.title_bar import TitleBar
from pymetr.application.trace_plot import TracePlot
from pymetr.application.control_panel import ControlPanel
from pymetr.application.managers.instrument_manager import InstrumentManager
from pymetr.application.factories.instrument_interface import InstrumentInterface
from pymetr.application.managers.trace_manager import TraceManager


class ControlPanelToggleBar(QToolBar):
    actionToggled = Signal(str, bool)  # Signal to indicate toggle state changes

    def __init__(self, parent=None):
        super(ControlPanelToggleBar, self).__init__("Control Toggles", parent)
        self.setOrientation(Qt.Vertical)
        self.setIconSize(QSize(36, 36))
        self.setMovable(False)

        self.toggle_actions = {}  # Stores the toggle actions

    def add_toggle_action(self, text, icon_path, panel_name, is_default=False):
        logging.debug(f"Adding toggle action: {text}")
        logging.debug(f"Icon path: {icon_path}")

        # Prepare icon paths for both active and inactive states
        active_icon_path = icon_path.replace("_g.png", ".png")
        inactive_icon_path = icon_path  # Assuming passed icon path is the inactive (greyed out) icon

        action = QAction(QIcon(inactive_icon_path), text, self)
        action.setCheckable(True)
        action.setChecked(is_default)
        action.toggled.connect(self.handle_action_toggled)

        # Store icon paths in the action for easy switching
        action.setData({'active_icon': active_icon_path, 'inactive_icon': inactive_icon_path, 'panel_name': panel_name})

        self.addAction(action)
        self.toggle_actions[text] = action

        # Emit toggled signal to handle initial state setup
        if is_default:
            # Make sure to use QTimer.singleShot to allow the event loop to process the newly created action completely
            QTimer.singleShot(0, lambda: action.toggle())

    def handle_action_toggled(self, checked):
        action = self.sender()
        icon_path = action.data()['active_icon'] if checked else action.data()['inactive_icon']
        action.setIcon(QIcon(icon_path))

        # Emit signal to notify others of the toggle state
        self.actionToggled.emit(action.text(), checked)

        # Update other actions to ensure only one is active at a time
        if checked:
            for other_action in self.actions():
                if other_action != action and other_action.isChecked():
                    other_action.setChecked(False)

class PyMetrMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(100, 100, 1200, 800)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Custom Title Bar
        self.title_bar = TitleBar(self)
        self.setMenuWidget(self.title_bar)

        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # --- Plot Displays ---
        self.instrument_manager = InstrumentManager()
        self.trace_manager = TraceManager()
        self.trace_plot = TracePlot(self.trace_manager, self)

        # --- Control Panels ---
        self.control_panel = ControlPanel(self.trace_manager, self.instrument_manager, self.trace_plot, self)
        self.control_panel_height = 301

        # Control Panel Toggle Bar
        self.control_panel_toggle_bar = ControlPanelToggleBar(self)
        self.addToolBar(Qt.LeftToolBarArea, self.control_panel_toggle_bar)

        # Add toggle actions
        self.control_panel_toggle_bar.add_toggle_action("Instruments", "pymetr/application/icons/instruments_g.png", "Instrument", is_default=True)
        self.control_panel_toggle_bar.add_toggle_action("Traces", "pymetr/application/icons/traces_g.png", "Trace", False)
        self.control_panel_toggle_bar.add_toggle_action("Markers", "pymetr/application/icons/markers_g.png", "Marker", False)
        self.control_panel_toggle_bar.add_toggle_action("Cursors", "pymetr/application/icons/cursors_g.png", "Cursor", False)
        self.control_panel_toggle_bar.add_toggle_action("Measurements", "pymetr/application/icons/measure_g.png", "Measurement", False)
        self.control_panel_toggle_bar.add_toggle_action("Calculations", "pymetr/application/icons/analytics_g.png", "Calculation", False)
        self.control_panel_toggle_bar.add_toggle_action("Plot Display", "pymetr/application/icons/display_g.png", "PlotDisplay", False)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.control_panel_toggle_bar.addWidget(spacer)
        # self.control_panel_toggle_bar.add_toggle_action("Settings", "pymetr/application/icons/settings_g.png", "Setting", False)
        self.control_panel_toggle_bar.add_toggle_action("Console", "pymetr/application/icons/console_g.png", "Console", False)

        self.control_panel_toggle_bar.actionToggled.connect(self.toggle_control_panel)

        # --- Main Area Layout ---
        main_area_layout = QHBoxLayout()

        # --- Control Panel Splitter ---
        self.control_panel_splitter = QSplitter(Qt.Vertical)
        self.control_panel_splitter.addWidget(self.trace_plot)
        self.control_panel_splitter.addWidget(self.control_panel)
        main_area_layout.addWidget(self.control_panel_splitter, stretch=1)
        self.control_panel_splitter.splitterMoved.connect(self.update_control_panel_height)
        handle_width = 6
        self.control_panel_splitter.setHandleWidth(handle_width)

        # --- Instrument Tab Widget ---
        self.instrument_tab_widget = QTabWidget(self)
        self.instrument_tab_widget.setTabPosition(QTabWidget.East)
        self.instrument_tab_widget.setMovable(True)
        self.instrument_tab_widget.setDocumentMode(True)
        self.instrument_tab_widget.setTabBarAutoHide(True)
        self.instrument_tab_widget.setTabsClosable(False)
        main_area_layout.addWidget(self.instrument_tab_widget, stretch=0)

        self.main_layout.addLayout(main_area_layout, stretch=1)
        self.control_panel.control_panel_stack.setCurrentWidget(self.control_panel.instrument_control_panel)

        # Create and add the status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.color_picker_button = QPushButton()
        self.color_picker_button.setStyleSheet("background-color: #FFAA00; width: 20px; height: 20px;")
        self.color_picker_button.clicked.connect(self.show_color_dialog)
        self.status_bar.addPermanentWidget(self.color_picker_button)

        # Connect signals
        self.title_bar.plotModeChanged.connect(self.trace_manager.set_plot_mode)
        self.title_bar.roiPlotToggled.connect(self.trace_plot.on_roi_plot_enabled)
        self.title_bar.roiPlotToggled.connect(self.trace_manager.emit_trace_data)
        self.title_bar.testTraceClicked.connect(self.trace_manager.add_random_trace)
        self.title_bar.screenshotClicked.connect(self.trace_plot.capture_screenshot)
        self.title_bar.traceModeChanged.connect(self.trace_manager.set_trace_mode)
        self.title_bar.groupTraces.connect(self.trace_manager.group_all_traces)
        self.title_bar.isolateTraces.connect(self.trace_manager.isolate_all_traces)
        self.title_bar.clearTraces.connect(self.trace_manager.clear_traces)
        
        self.title_bar.groupTraces.connect(self.control_panel.trace_control_panel.group_all_traces)
        self.title_bar.isolateTraces.connect(self.control_panel.trace_control_panel.isolate_all_traces)
        self.title_bar.clearTraces.connect(self.control_panel.trace_control_panel.clear_traces)

        self.control_panel.instrument_control_panel.instrument_connected.connect(self.on_instrument_connected)
        self.control_panel.instrument_control_panel.instrument_disconnected.connect(self.on_instrument_disconnected)
        self.control_panel.instrument_control_panel.no_instruments_connected.connect(self.hide_instrument_dock)

        # self.control_panel.display_control_panel.gridToggled.connect(self.trace_plot.toggle_grid)
        # self.control_panel.display_control_panel.xLogScaleToggled.connect(self.trace_plot.toggle_x_log_scale)
        # self.control_panel.display_control_panel.yLogScaleToggled.connect(self.trace_plot.toggle_y_log_scale)
        self.control_panel.display_control_panel.xGridChanged.connect(self.trace_plot.set_x_grid)
        self.control_panel.display_control_panel.yGridChanged.connect(self.trace_plot.set_y_grid)
        self.control_panel.display_control_panel.titleChanged.connect(self.trace_plot.set_title)
        self.control_panel.display_control_panel.titleVisibilityChanged.connect(self.trace_plot.set_title_visibility)
        self.control_panel.display_control_panel.xLabelChanged.connect(self.trace_plot.set_x_label)
        self.control_panel.display_control_panel.xLabelVisibilityChanged.connect(self.trace_plot.set_x_label_visibility)
        self.control_panel.display_control_panel.yLabelChanged.connect(self.trace_plot.set_y_label)
        self.control_panel.display_control_panel.yLabelVisibilityChanged.connect(self.trace_plot.set_y_label_visibility)

    def update_control_panel_height(self, pos, index):
        if index == 1:
            self.control_panel_height = self.control_panel_splitter.sizes()[1]

    def update_control_panel_height(self, pos, index):
        if index == 1:
            self.control_panel_height = self.control_panel_splitter.sizes()[1]

    def toggle_control_panel(self, action_text, checked):
        action = self.control_panel_toggle_bar.toggle_actions.get(action_text)
        logging.debug(f"Calling toggle with: '{action_text}': {checked}")

        if not action:
            logging.warning(f"Invalid action text: {action_text}")
            return

        if checked:
            # Set the control panel to the corresponding panel index
            action_index = list(self.control_panel_toggle_bar.toggle_actions.keys()).index(action_text)
            self.control_panel.control_panel_stack.setCurrentIndex(action_index)
            self.control_panel.show()
        else:
            # If no toggle action is checked, hide the control panel
            if not any(a.isChecked() for a in self.control_panel_toggle_bar.toggle_actions.values()):
                self.control_panel.hide()

    def on_instrument_connected(self, unique_id):
        logger.debug(f"Instrument connected with unique ID: {unique_id}")
        instrument = self.instrument_manager.instruments[unique_id]
        instrument['instance'].set_unique_id(unique_id) 

        instrument_panel = InstrumentInterface(self.instrument_manager)
        instrument_panel.setup_interface(instrument, unique_id)

        # Connect the signals
        instrument_panel.continuous_mode_changed.connect(self.trace_plot.set_continuous_mode)
        instrument_panel.plot_update_requested.connect(self.trace_plot.update_plot)
        instrument_panel.traceDataReady.connect(self.trace_manager.add_trace)
        self.title_bar.plotModeChanged.connect(instrument_panel.set_plot_mode)
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
        painter.end()

    def show_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            new_color = color.name()
            self.color_picker_button.setStyleSheet(f"background-color: {new_color}; width: 20px; height: 20px;")
            self.update_stylesheet(new_color)
            self.trace_manager.set_highlight_color(new_color)
            self.trace_plot.set_highlight_color(new_color)

    def update_stylesheet(self, new_color):
        # Read the current stylesheet
        with open("pymetr/application/styles.qss", "r") as f:
            stylesheet = f.read()

        # Replace the old highlight color with the new color
        old_color = "#FFAA00"
        stylesheet = stylesheet.replace(old_color, new_color)

        # Set the updated stylesheet on the application
        app = pg.mkQApp()  # Get the application instance
        app.setStyleSheet(stylesheet)

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