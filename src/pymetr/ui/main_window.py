import os
from typing import Optional, Dict
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QSize, QTimer
from PySide6.QtGui import QPainter, QPainterPath, QColor, QIcon
from PySide6.QtWidgets import QMainWindow, QWidget, QDockWidget, QApplication

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

# Theme Management
from pymetr.services.theme_service import ThemeService
from pymetr.core.logging import logger


class MainWindow(QMainWindow):
    """
    Main application window with dockable views and tabbed content.
    
    Key behaviors:
    - Manages dockable panels (test explorer, instrument panel)
    - Hosts the TabManager for content display
    - Synchronizes state between UI components
    - Maintains window state between sessions
    - Handles theme and appearance settings
    """
    def __init__(self, state):
        logger.debug("Initializing MainWindow")
        super().__init__()
        self.state = state
        self.state.set_parent(self)
        
        # Initialize theme service
        self.theme_service = ThemeService.get_instance()
        
        # Apply theme to application
        app = QApplication.instance()
        if app:
            self.theme_service.apply_theme(app)
        
        # Configure window appearance
        self._setup_window()
        
        # Create main UI components
        self._setup_title_bar()
        self._setup_quick_tools()  # Create toolbar first
        self._setup_docks()        # Then create docks
        self._setup_tab_manager()  # Then tab manager
        self._setup_status_bar()   # Finally status bar
        
        # Connect signals
        self._connect_signals()
        
        # Restore previous session state
        self._restore_state()

    def _setup_window(self):
        """Configure main window properties."""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1000, 618)
        # self.setDockOptions(
        #     QMainWindow.AnimatedDocks |
        #     QMainWindow.AllowNestedDocks |
        #     QMainWindow.AllowTabbedDocks
        # )

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

    def _setup_status_bar(self):
        """Set up status bar for application messages."""
        self.status_bar = StatusBar(self.state)
        self.setStatusBar(self.status_bar)

    def _connect_signals(self):
        """Connect to ApplicationState signals."""
        # Connect signals for model management
        self.state.model_registered.connect(self._handle_model_registered)
        self.state.model_removed.connect(self._handle_model_removed)
        
        # Connect to theme service signals
        self.theme_service.theme_changed.connect(self._on_theme_changed)
        self.theme_service.accent_color_changed.connect(self._on_accent_color_changed)
        
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
    
    def _on_theme_changed(self, theme_name):
        """Handle theme changes."""
        logger.debug(f"MainWindow: Theme changed to {theme_name}")
        
        # Apply to application
        app = QApplication.instance()
        if app:
            self.theme_service.apply_theme(app)
        
        # Notify state
        self.state.set_info(f"Theme changed to {theme_name}")
    
    def _on_accent_color_changed(self, color):
        """Handle accent color changes."""
        logger.debug(f"MainWindow: Accent color changed to {color.name()}")
        
        # Apply to application
        app = QApplication.instance()
        if app:
            self.theme_service.apply_theme(app)
        
        # Notify state
        self.state.set_info(f"Theme updated: {color.name()}")

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
        bg_color = QColor("#2A2A2A")  # Default color
        
        # Try to get color from theme
        try:
            theme_css = self.theme_service.get_stylesheet()
            if "--bg-primary:" in theme_css:
                bg_color_str = theme_css.split("--bg-primary:")[1].split(";")[0].strip()
                if bg_color_str and QColor(bg_color_str).isValid():
                    bg_color = QColor(bg_color_str)
        except Exception as e:
            logger.warning(f"Failed to parse background color from theme: {e}")
        
        painter.setClipPath(path)
        painter.fillRect(self.rect(), bg_color)