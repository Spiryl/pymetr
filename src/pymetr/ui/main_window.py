from typing import Optional, Dict
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QSize, QTimer
from PySide6.QtGui import QPainter, QPainterPath, QColor
from PySide6.QtWidgets import QMainWindow, QWidget, QDockWidget

# Toolbars and UI Components
from pymetr.ui.title_bar import TitleBar
from pymetr.ui.status_bar import StatusBar
from pymetr.ui.quick_toolbar import QuickToolBar

# Content Management
from pymetr.ui.tab_manager import TabManager
from pymetr.ui.factories.tab_factory import TabFactory

# Docks
from pymetr.ui.docks.model_tree_view import ModelTreeView
from pymetr.ui.docks.device_tree_view import DeviceTreeView

from pymetr.core.logging import logger

class MainWindow(QMainWindow):
    """
    Main application window with dockable views and tabbed content.
    
    Key behaviors:
    - Manages dockable panels (test explorer, instrument panel)
    - Hosts the TabManager for content display
    - Synchronizes state between UI components
    - Maintains window state between sessions
    """
    def __init__(self, state):
        logger.debug("Initializing MainWindow")
        super().__init__()
        self.state = state
        self.state.set_parent(self)
        
        # Configure window appearance
        self._setup_window()
        
        # Create main UI components
        self._setup_title_bar()
        self._setup_quick_tools()  # Create toolbar first
        self._setup_docks()        # Then create docks
        self._setup_tab_manager()  # Then tab manager
        self._setup_status_bar()   # Finally status bar
        
        # Connect the instrument dock to the toolbar after both are created
        if hasattr(self, 'quick_tools') and hasattr(self, 'instrument_dock'):
            self.quick_tools.set_instruments_dock(self.instrument_dock)
        
        # Connect signals
        self._connect_signals()
        
        # Restore previous session state
        self._restore_state()

    def _setup_window(self):
        """Configure main window properties."""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1200, 800)
        self.setDockOptions(
            QMainWindow.AnimatedDocks |
            QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks
        )

    def _setup_title_bar(self):
        """Set up custom frameless window title bar."""
        self.title_bar = TitleBar(self, state=self.state)
        self.setMenuWidget(self.title_bar)
        self.title_bar.windowMinimizeRequested.connect(self.showMinimized)
        self.title_bar.windowMaximizeRequested.connect(self._toggle_maximize)
        self.title_bar.windowCloseRequested.connect(self.close)

    def _setup_quick_tools(self):
        """Set up quick access toolbar with common actions."""
        self.quick_tools = QuickToolBar(self.state, self)
        
        # Add the toolbar to the main window
        self.addToolBar(Qt.TopToolBarArea, self.quick_tools)

    def _setup_tab_manager(self):
        """Set up the central tab manager."""
        self.tab_manager = TabManager(self.state, self)
        self.setCentralWidget(self.tab_manager)

    def _setup_docks(self):
        """Set up test explorer and instrument docks."""
        # Test Explorer
        self.test_dock = QDockWidget("Test Explorer", self)
        self.test_dock.setObjectName("TestExplorerDock")
        self.test_dock.setMinimumWidth(250)
        self.test_dock.setFeatures(
            QDockWidget.DockWidgetMovable | 
            QDockWidget.DockWidgetFloatable
        )
        self.test_tree_view = ModelTreeView(self.state, parent=self.test_dock)
        self.test_dock.setWidget(self.test_tree_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.test_dock)
        
        # Instruments
        self.instrument_dock = QDockWidget("Instruments", self)
        self.instrument_dock.setObjectName("InstrumentsDock")
        self.instrument_dock.setMinimumWidth(200)
        self.instrument_dock.setFeatures(
            QDockWidget.DockWidgetMovable | 
            QDockWidget.DockWidgetFloatable
        )
        self.device_view = DeviceTreeView(self.state, None, parent=self.instrument_dock)
        self.instrument_dock.setWidget(self.device_view)
        self.addDockWidget(Qt.RightDockWidgetArea, self.instrument_dock)
        
        # Connect dock to QuickToolBar for toggling
        if hasattr(self, 'quick_tools'):
            self.quick_tools.set_instruments_dock(self.instrument_dock)

    def _setup_status_bar(self):
        """Set up status bar for application messages."""
        self.status_bar = StatusBar(self.state)
        self.setStatusBar(self.status_bar)

    def _connect_signals(self):
        """Connect to ApplicationState signals."""
        # Connect signals for model management
        self.state.model_registered.connect(self._handle_model_registered)
        self.state.model_removed.connect(self._handle_model_removed)
        
    def _handle_model_registered(self, model_id: str):
        """Handle new model registration."""
        logger.debug(f"Model {model_id} registered")
        # Views are created on-demand by the TabManager

    def _handle_model_removed(self, model_id: str):
        """Handle model removal."""
        logger.debug(f"Model {model_id} removed")
        # TabManager handles cleanup

    def _toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # Action-related methods have been moved to QuickToolBar class

    def _restore_state(self):
        """Restore window geometry and dock states from settings."""
        settings = QSettings("PyMetr", "PyMetr")
        
        # Restore window geometry
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
        # Restore dock and toolbar states
        state = settings.value("windowState")
        if state:
            self.restoreState(state)

    def paintEvent(self, event):
        """Custom paint for rounded window corners."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create rounded rect path
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 10, 10)
        
        # Clip to path and fill
        painter.setClipPath(path)
        painter.fillRect(self.rect(), QColor("#2A2A2A"))

    def closeEvent(self, event):
        """Save window state before closing."""
        settings = QSettings("PyMetr", "PyMetr")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        
        super().closeEvent(event)