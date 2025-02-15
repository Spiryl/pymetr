# pymetr/views/main_window.py
import sys
import logging
from typing import Optional, Dict, Type, Tuple
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QSize, QMetaObject, Q_ARG, QEvent, QTimer, Slot
from PySide6.QtGui import QPainter, QPainterPath, QColor, QIcon, QAction, QPaintEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QDockWidget, QToolBar, QLabel, QApplication
)

from pymetr.views.title_bar import TitleBar
from pymetr.views.widgets.test_view import ModelTestView
from pymetr.views.widgets.device_view import DeviceView
from pymetr.views.widgets.base import BaseWidget
from pymetr.views.widgets.status_bar import StatusBar
from pymetr.models.test import TestScript
from pymetr.models.plot import Plot
from pymetr.views.tabs.script_tab import ScriptTab
from pymetr.views.tabs.plot_tab import PlotTab
from pymetr.views.tabs.result_tab import ResultTab
from pymetr.views.tabs.table_tab import TableTab
from pymetr.core.logging import logger

###############################################################################
# Custom QDockWidget subclass for active-model synchronization
###############################################################################
class ActiveDockWidget(QDockWidget):
    """
    A custom QDockWidget that notifies the ApplicationState when it is clicked or
    receives focus. Also, when the user clicks the close button, we override
    the default behavior to simply hide the dock.
    """
    def __init__(self, model_id: str, state, title: str, parent: Optional[QWidget] = None):
        logger.debug(f"Initializing ActiveDockWidget for model_id: {model_id} with title: {title}")
        super().__init__(title, parent)
        self._model_id = model_id
        self.state = state
        self._is_active = False
        # Ensure the dock widget accepts focus
        self.setFocusPolicy(Qt.StrongFocus)

    def showEvent(self, event):
        """Handle show events to ensure proper activation."""
        super().showEvent(event)
        logger.debug(f"Show event for dock {self._model_id}")
        self._ensure_active()

    def _ensure_active(self):
        """Ensure this dock is active and visible."""
        logger.debug(f"Ensuring dock {self._model_id} is active")
        # First, make sure we're visible
        self.show()
        self.raise_()
        
        # If we're in a tabbed dock area, we need to make sure we're the active tab
        if self.parent():
            tabbed_docks = self.parent().findChildren(QDockWidget)
            if len(tabbed_docks) > 1:
                logger.debug("Dock is tabbed, ensuring it's the active tab")
                # This will make us the active tab
                self.show()
                self.raise_()
        
        # Force focus after a short delay to ensure Qt has processed all events
        QTimer.singleShot(0, self._delayed_focus)

    def _delayed_focus(self):
        """Apply focus after Qt has processed all events."""
        if self.isVisible():
            self.setFocus(Qt.OtherFocusReason)
            if self.widget():
                self.widget().setFocus(Qt.OtherFocusReason)

    def mousePressEvent(self, event):
        logger.debug(f"ActiveDockWidget (model_id: {self._model_id}) mousePressEvent triggered")
        super().mousePressEvent(event)
        self._ensure_active()
        self.state.set_active_model(self._model_id)

    def focusInEvent(self, event):
        if not self._is_active:
            logger.debug(f"ActiveDockWidget (model_id: {self._model_id}) focusInEvent triggered")
            super().focusInEvent(event)
            self._is_active = True
            self.state.set_active_model(self._model_id)
            QTimer.singleShot(100, self._reset_active_state)

    def _reset_active_state(self):
        """Reset the active state after a short delay."""
        self._is_active = False

    def closeEvent(self, event):
        # Override closeEvent so that the dock is hidden rather than destroyed.
        logger.debug(f"ActiveDockWidget (model_id: {self._model_id}) closeEvent triggered; hiding dock instead")
        self.hide()
        event.ignore()

###############################################################################
# End of ActiveDockWidget subclass
###############################################################################

class WelcomeWidget(QWidget):
    """Welcome widget shown when no content is open."""
    def __init__(self, state, parent=None):
        logger.debug("Initializing WelcomeWidget")
        super().__init__(parent)
        self.state = state
        self._setup_ui()
        
    def _setup_ui(self):
        logger.debug("Setting up UI for WelcomeWidget")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        welcome_text = (
            "<h1>Welcome to PyMetr</h1>"
            "<p>Start by opening a script or connecting an instrument.</p>"
            "<p>Use the ribbon actions above to get started.</p>"
        )
        layout.addWidget(QLabel(welcome_text))

class MainWindow(QMainWindow):
    """
    Main application window that uses a nested QMainWindow as its central widget.
    The inner QMainWindow (self.content_window) manages content docks (including the welcome dock).
    Outer docks (like Test Explorer and Instruments) remain attached to the outer main window.
    """
    def __init__(self, state):
        logger.debug("Initializing MainWindow")
        super().__init__()
        self.state = state
        self.state.set_parent(self)
        
        # Dictionaries to track content docks and views (keyed by model ID)
        self._content_docks: Dict[str, ActiveDockWidget] = {}
        self._content_views: Dict[str, BaseWidget] = {}
        # Store welcome dock separately
        self._welcome_dock: Optional[ActiveDockWidget] = None
        
        # Create an inner QMainWindow to serve as the central area for content docks
        logger.debug("Creating inner content window")
        self.content_window = QMainWindow(self)
        self.content_window.setWindowFlags(Qt.Widget)
        self.content_window.setDockOptions(
            QMainWindow.AnimatedDocks |
            QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks
        )
        self.setCentralWidget(self.content_window)
        
        # Outer docks remain on the outer main window.
        self._setup_window()
        self._setup_title_bar()
        self._setup_quick_tools()
        self._setup_docks()
        self._setup_status_bar()
        
        # Initially show the welcome dock in the inner content window.
        self.show_welcome()
        
        self._connect_signals()
        self._restore_state()
    
    def _setup_window(self):
        """Configure window properties."""
        logger.debug("Setting up window properties")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1200, 800)
        self.setDockOptions(
            QMainWindow.AnimatedDocks |
            QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks
        )

    def _setup_title_bar(self):
        """Set up custom title bar."""
        logger.debug("Setting up title bar")
        self.title_bar = TitleBar(self, state=self.state)
        self.setMenuWidget(self.title_bar)
        self.title_bar.windowMinimizeRequested.connect(self.showMinimized)
        self.title_bar.windowMaximizeRequested.connect(self._toggle_maximize)
        self.title_bar.windowCloseRequested.connect(self.close)

    def _setup_quick_tools(self):
        """Set up quick access toolbar."""
        logger.debug("Setting up quick tools toolbar")
        self.quick_tools = QToolBar("QuickTools")
        self.quick_tools.setMovable(False)
        icon_path = str(Path(__file__).parent / "icons/display.png")
        logger.debug(f"Quick tool icon path: {icon_path}")
        hide_passed_action = QAction(QIcon(icon_path), "Hide Passed Tests", self)
        hide_passed_action.setCheckable(True)
        hide_passed_action.triggered.connect(self._on_hide_passed_toggled)
        self.quick_tools.addAction(hide_passed_action)
        self.addToolBar(Qt.TopToolBarArea, self.quick_tools)

    def _setup_docks(self):
        """Set up outer dock widgets."""
        logger.debug("Setting up outer docks")
        # Outer dock: Test Explorer
        self.test_dock = QDockWidget("Test Explorer", self)
        self.test_dock.setObjectName("TestExplorerDock")
        self.test_dock.setMinimumWidth(250)
        self.test_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.test_tree_view = ModelTestView(self.state, parent=self.test_dock)
        self.test_dock.setWidget(self.test_tree_view)
        logger.debug("Adding Test Explorer dock to MainWindow")
        self.addDockWidget(Qt.LeftDockWidgetArea, self.test_dock)
        
        # Outer dock: Instruments
        self.instrument_dock = QDockWidget("Instruments", self)
        self.instrument_dock.setObjectName("InstrumentsDock")
        self.instrument_dock.setMinimumWidth(200)
        self.instrument_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.device_view = DeviceView(self.state, None, parent=self.instrument_dock)
        self.instrument_dock.setWidget(self.device_view)
        logger.debug("Adding Instruments dock to MainWindow")
        self.addDockWidget(Qt.RightDockWidgetArea, self.instrument_dock)

    def _setup_status_bar(self):
        """Set up status bar."""
        logger.debug("Setting up status bar")
        self.status_bar = StatusBar(self.state)
        self.setStatusBar(self.status_bar)

    def _connect_signals(self):
        """Connect to state signals."""
        logger.debug("Connecting state signals")
        self.state.model_registered.connect(self._handle_model_registered)
        self.state.active_model_changed.connect(self._handle_active_model)
        self.state.model_changed.connect(self._handle_model_changed)
        self.state.model_removed.connect(self._handle_model_removed)

    def _restore_state(self):
        """Restore window and dock states."""
        logger.debug("Restoring window state from QSettings")
        settings = QSettings("PyMetr", "PyMetr")
        geometry = settings.value("geometry")
        if geometry:
            logger.debug("Restoring geometry")
            self.restoreGeometry(geometry)
        state_value = settings.value("windowState")
        if state_value:
            logger.debug("Restoring window state")
            self.restoreState(state_value)

    def show_welcome(self):
        """
        Show welcome widget as a dock in the inner content window.
        This dock is only visible when no other content docks are open.
        """
        logger.debug("Attempting to show welcome dock")
        if self._welcome_dock is None:
            logger.debug("Creating new welcome dock")
            welcome = WelcomeWidget(self.state, self)
            self._welcome_dock = ActiveDockWidget("welcome", self.state, "Welcome", self.content_window)
            self._welcome_dock.setWidget(welcome)
            # Do not allow closing the welcome dock.
            self._welcome_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
            self.content_window.addDockWidget(Qt.RightDockWidgetArea, self._welcome_dock)
            logger.debug("Welcome dock created and added to content window")
        else:
            logger.debug("Welcome dock already exists; showing it")
            self._welcome_dock.show()
            self._welcome_dock.raise_()

    def hide_welcome(self):
        """Hide the welcome dock if it is shown."""
        logger.debug("Hiding welcome dock")
        if self._welcome_dock is not None:
            self._welcome_dock.hide()

    def _get_view_class(self, model) -> Optional[Type[BaseWidget]]:
        """Get appropriate view class for the given model type."""
        model_type = type(model).__name__
        logger.debug(f"Retrieving view class for model type: {model_type}")
        
        view_map = {
            'TestScript': ScriptTab,
            'TestResult': ResultTab,
            'Plot': PlotTab,
            'DataTable': TableTab
        }
        return view_map.get(model_type)

    def _create_content_view(self, model_id: str) -> Optional[Tuple[BaseWidget, ActiveDockWidget]]:
        """Create a view and dock widget for the given model ID."""
        logger.debug(f"Creating content view for model_id: {model_id}")
        model = self.state.get_model(model_id)
        if not model:
            logger.error(f"Model with id {model_id} not found in state")
            return None

        try:
            view_class = self._get_view_class(model)
            if not view_class:
                logger.warning(f"No view class found for model type: {type(model).__name__}")
                return None
            view = view_class(self.state, model_id, self)
            dock_title = model.get_property('name', str(model_id))
            logger.debug(f"Creating dock with title: {dock_title}")
            dock = ActiveDockWidget(model_id, self.state, dock_title, self.content_window)
            dock.setWidget(view)
            dock.setFeatures(
                QDockWidget.DockWidgetMovable |
                QDockWidget.DockWidgetFloatable |
                QDockWidget.DockWidgetClosable
            )
            # Do not automatically hide the dock on visibility change; let the closeEvent handle it.
            logger.debug(f"Content view for model_id {model_id} created successfully")
            return view, dock
        except Exception as e:
            logger.error(f"Error creating view for {model_id}: {e}")
            return None

    def open_content(self, model_id: str) -> bool:
        """
        Open content in a new dock (inside the inner content_window) or re-show it if hidden.
        The dock is not deleted when closed; it is simply hidden.
        """
        logger.debug(f"open_content called for model_id: {model_id}")
        # If a content dock already exists, show it.
        if model_id in self._content_docks:
            logger.debug(f"Content dock for model_id {model_id} already exists; re-showing it")
            dock = self._content_docks[model_id]
            dock.show()
            dock.raise_()
            # Update active model from dock activation
            self.state.set_active_model(model_id)
            # Hide the welcome dock when content is shown.
            self.hide_welcome()
            return True

        result = self._create_content_view(model_id)
        if not result:
            logger.error(f"Failed to create content view for model_id {model_id}")
            return False

        view, dock = result

        # Hide welcome dock if it's visible.
        self.hide_welcome()

        self._content_views[model_id] = view
        self._content_docks[model_id] = dock

        logger.debug(f"Adding content dock for model_id {model_id} to content window")
        self.content_window.addDockWidget(Qt.RightDockWidgetArea, dock)

        # Optionally, tabify with any existing content docks.
        existing_docks = [d for mid, d in self._content_docks.items() if mid != model_id]
        if existing_docks:
            logger.debug(f"Tabifying content dock for model_id {model_id} with an existing dock")
            self.content_window.tabifyDockWidget(existing_docks[-1], dock)

        dock.raise_()
        # Set active model since new dock was just opened
        self.state.set_active_model(model_id)
        logger.debug(f"Content dock for model_id {model_id} opened successfully")
        return True

    def _handle_model_registered(self, model_id: str):
        """
        Handle new model registration.
        We don't create tabs here anymore - they'll be created on-demand when activated.
        """
        logger.debug(f"Model {model_id} registered")

    def _handle_active_model(self, model_id: str):
        """Handle model activation by creating/showing appropriate view."""
        logger.debug(f"_handle_active_model triggered for model_id: {model_id}")
        
        if model_id:
            # If we already have a dock for this model, show it
            if model_id in self._content_docks:
                dock = self._content_docks[model_id]
                logger.debug(f"Found existing dock for model {model_id}")
                if not dock.isVisible():
                    logger.debug(f"Showing dock for model {model_id}")
                    dock.show()
                dock.raise_()
                dock.setFocus(Qt.OtherFocusReason)  # Force focus
                
                # Ensure the tab is active if it's in a tabbed dock area
                tabbed_dock = self.content_window.tabifiedDockWidgets(dock)
                if tabbed_dock:
                    logger.debug("Dock is tabbed, ensuring it's the active tab")
                    dock.show()
                    dock.raise_()
                    
                # Use a timer to ensure focus after Qt has processed all events
                QTimer.singleShot(0, lambda: self._ensure_dock_focus(dock))
            else:
                # Create new content view on-demand
                logger.debug(f"Creating new content view for model {model_id}")
                self.open_content(model_id)
                
            # Hide welcome screen when showing content
            self.hide_welcome()
        else:
            # No active model, show welcome screen
            logger.debug("No active model, showing welcome screen")
            self.show_welcome()
            
    def _ensure_dock_focus(self, dock):
        """Ensure a dock widget has focus and is visible."""
        logger.debug(f"Ensuring focus for dock: {dock.windowTitle()}")
        if dock.isVisible():
            dock.raise_()
            dock.setFocus(Qt.OtherFocusReason)
            # If the dock has a widget, focus it too
            if dock.widget():
                dock.widget().setFocus(Qt.OtherFocusReason)

    def _handle_model_changed(self, model_id: str, prop: str, value: object):
        """Update dock title if the model’s name changes."""
        # logger.debug(f"Model {model_id} changed property '{prop}' to '{value}'")
        if prop == 'name' and model_id in self._content_docks:
            self._content_docks[model_id].setWindowTitle(str(value))
            logger.debug(f"Updated dock title for model_id {model_id} to '{value}'")

    def _handle_dock_visibility_changed(self, model_id: str, visible: bool):
        logger.debug(f"Dock visibility changed for model_id {model_id}: visible={visible}")
        # If all content docks are hidden, show the welcome dock.
        if not any(d.isVisible() for mid, d in self._content_docks.items()):
            logger.debug("No content docks visible; showing welcome dock")
            self.show_welcome()

    @Slot(str)
    def _handle_model_removed(self, model_id: str):
        if model_id in self._content_docks:
            dock = self._content_docks.pop(model_id)
            dock.close()  # Close the tab/dock view
            logger.debug(f"Closed content dock for removed model {model_id}")

    def _on_hide_passed_toggled(self, checked: bool):
        """Handle toggle for hiding passed tests."""
        logger.info(f"Hide passed toggled: {checked}")
        self.state.set_status(f"Hide passed = {checked}")

    def _toggle_maximize(self):
        """Toggle window maximize state."""
        if self.isMaximized():
            logger.debug("Window is maximized; switching to normal mode")
            self.showNormal()
        else:
            logger.debug("Window is in normal mode; switching to maximized mode")
            self.showMaximized()

    def paintEvent(self, event: QPaintEvent):
        """Custom paint event for rounded window frame."""
        # logger.debug("paintEvent triggered for MainWindow")
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 10, 10)
        painter.setClipPath(path)
        painter.fillRect(self.rect(), QColor("#2A2A2A"))

    def closeEvent(self, event):
        """Save state before closing."""
        logger.debug("closeEvent triggered; saving window geometry and state")
        settings = QSettings("PyMetr", "PyMetr")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        super().closeEvent(event)

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from pymetr.core.state import ApplicationState

    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    state = ApplicationState()
    main_win = MainWindow(state)
    main_win.show()

    sys.exit(app.exec())
