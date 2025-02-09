# pymetr/views/main_window.py

import sys
import logging

from PySide6.QtCore import Qt, QSettings, QSize
from PySide6.QtGui import QPainter, QPainterPath, QColor, QIcon, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QDockWidget, QStatusBar,
    QToolBar, QTabWidget
)

from pymetr.views.title_bar import TitleBar
from pymetr.views.tab_manager import TabManager
from pymetr.views.widgets.test_view import ModelTestView
from pymetr.views.widgets.device_view import DeviceView

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, state):
        super().__init__()
        self.state = state
        # If your ApplicationState can store a parent widget:
        self.state.set_parent(self)

        # ----------- Frameless + translucent background -----------
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1200, 800)

        # ----------- 1) Title Bar -----------
        self.title_bar = TitleBar(self, state=self.state)
        self.setMenuWidget(self.title_bar)

        # Connect the TitleBar signals to actual window operations
        self.title_bar.windowMinimizeRequested.connect(self.showMinimized)
        self.title_bar.windowMaximizeRequested.connect(self._toggle_maximize)
        self.title_bar.windowCloseRequested.connect(self.close)

        # ----------- 2) Central area with a TabManager -----------
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_manager = TabManager(self.state, parent=self)
        layout.addWidget(self.tab_manager)
        # Show welcome tab immediately
        self.tab_manager.show_welcome()

        # ----------- 3) Left dock for Test Tree -----------
        self.test_dock = QDockWidget("Test Explorer", self)
        self.test_dock.setObjectName("TestExplorerDock")
        self.test_dock.setMinimumWidth(250)
        self.test_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        self.test_tree_view = ModelTestView(self.state, parent=self.test_dock)
        self.test_dock.setWidget(self.test_tree_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.test_dock)

        # ----------- 4) Right dock for Instruments -----------
        self.instrument_dock = QDockWidget("Instruments", self)
        self.instrument_dock.setObjectName("InstrumentsDock")
        self.instrument_dock.setMinimumWidth(200)
        self.instrument_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        self.device_view = DeviceView(self.state, None, parent=self.instrument_dock)
        self.instrument_dock.setWidget(self.device_view)
        self.instrument_dock.setMinimumWidth(200)
        self.addDockWidget(Qt.RightDockWidgetArea, self.instrument_dock)

        # ----------- 5) Optional left toolbar -----------
        self.left_toolbar = QToolBar("QuickTool", self)
        self.left_toolbar.setOrientation(Qt.Vertical)
        self.left_toolbar.setMovable(False)
        self.addToolBar(Qt.LeftToolBarArea, self.left_toolbar)

        hide_passed_action = QAction(
            QIcon("pymetr/views/icons/display.png"), "ICON1", self
        )
        hide_passed_action.setCheckable(True)
        hide_passed_action.triggered.connect(self.on_hide_passed_toggled)
        self.left_toolbar.addAction(hide_passed_action)

        # ----------- 6) Status Bar -----------
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # ----------- Restore geometry/state -----------
        self._restore_state()

    def paintEvent(self, event):
        """
        Draws a rounded rectangle for the frameless background.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 10, 10)
        painter.setClipPath(path)
        painter.fillRect(self.rect(), QColor("#2A2A2A"))
        painter.end()

    def _toggle_maximize(self):
        """Switch between maximized and normal size."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def on_hide_passed_toggled(self, checked):
        logger.info(f"Hide passed toggled: {checked}")
        self.status_bar.showMessage(f"Hide passed = {checked}", 2000)
        # Example usage: Could filter the test_tree_view

    def _restore_state(self):
        settings = QSettings("PyMetr", "PyMetr")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        win_state = settings.value("windowState")
        if win_state:
            self.restoreState(win_state)

    def closeEvent(self, event):
        # Save geometry & layout states
        settings = QSettings("PyMetr", "PyMetr")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

        super().closeEvent(event)

# ------------------------------------------------------------------------
# If you run main_window.py directly for testing:
# ------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    from pymetr.core.state import ApplicationState

    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    state = ApplicationState()
    main_win = MainWindow(state)
    main_win.show()

    sys.exit(app.exec())
