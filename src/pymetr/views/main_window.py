from typing import Optional, Dict, Type, Tuple
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QSize, QTimer
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QIcon, QAction,
    QPaintEvent, QKeySequence
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QDockWidget,
    QToolBar, QLabel, QApplication, QStyle
)

from pymetr.views.title_bar import TitleBar
from pymetr.views.widgets.test_view import ModelTreeView
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

class MainWindow(QMainWindow):
    """
    Main application window with dockable views and tabbed content.
    
    Key behaviors:
    - Manages dockable test explorer and instrument panels
    - Provides tabbed content area for test results, plots, etc.
    - Synchronizes model selection with visible content
    - Maintains window state between sessions
    """
    def __init__(self, state):
        logger.debug("Initializing MainWindow")
        super().__init__()
        self.state = state
        self.state.set_parent(self)
        
        # Track content views and docks
        self._content_docks: Dict[str, QDockWidget] = {}
        self._content_views: Dict[str, BaseWidget] = {}
        self._welcome_dock: Optional[QDockWidget] = None
        
        # Create inner window for content management
        self.content_window = QMainWindow(self)
        self.content_window.setWindowFlags(Qt.Widget)
        self.content_window.setDockOptions(
            QMainWindow.AnimatedDocks |
            QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks
        )
        self.setCentralWidget(self.content_window)
        
        self._setup_window()
        self._setup_title_bar()
        self._setup_quick_tools()
        self._setup_docks()
        self._setup_status_bar()
        
        self.show_welcome()
        self._connect_signals()
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

    def _setup_quick_tools(self):
        """Set up quick access toolbar with common actions."""
        self.quick_tools = QToolBar("QuickTools")
        self.quick_tools.setMovable(False)
        self.quick_tools.setIconSize(QSize(28, 28))
        
        # File Explorer
        explorer_action = QAction(
            QIcon(str(Path(__file__).parent / 'icons' / 'folder.png')),
            "File Explorer",
            self
        )
        explorer_action.setShortcut(QKeySequence("Ctrl+E"))
        explorer_action.triggered.connect(self._toggle_file_explorer)
        
        # Run Selected Test
        run_test_action = QAction(
            QIcon(str(Path(__file__).parent / 'icons' / 'run.png')),
            "Run Test",
            self
        )
        run_test_action.setShortcut(QKeySequence("F5"))
        run_test_action.triggered.connect(self._on_run_test)
        
        # Stop Test
        stop_test_action = QAction(
            QIcon(str(Path(__file__).parent / 'icons' / 'stop.png')),
            "Stop Test",
            self
        )
        stop_test_action.setShortcut(QKeySequence("F6"))
        stop_test_action.triggered.connect(self._on_stop_test)
        
        # Toggle Instrument Panel
        toggle_instruments_action = QAction(
            QIcon(str(Path(__file__).parent / 'icons' / 'instruments.png')),
            "Instruments",
            self
        )
        toggle_instruments_action.setShortcut(QKeySequence("Ctrl+I"))
        toggle_instruments_action.triggered.connect(
            lambda: self.instrument_dock.setVisible(
                not self.instrument_dock.isVisible()
            )
        )
        
        # New Script
        new_script_action = QAction(
            QIcon(str(Path(__file__).parent / 'icons' / 'new_script.png')),
            "New Script",
            self
        )
        new_script_action.setShortcut(QKeySequence("Ctrl+N"))
        new_script_action.triggered.connect(self._on_new_script)
        
        # Add actions to toolbar
        self.quick_tools.addAction(explorer_action)
        self.quick_tools.addAction(new_script_action)
        self.quick_tools.addSeparator()
        self.quick_tools.addAction(run_test_action)
        self.quick_tools.addAction(stop_test_action)
        self.quick_tools.addSeparator()
        self.quick_tools.addAction(toggle_instruments_action)
        
        self.addToolBar(Qt.TopToolBarArea, self.quick_tools)

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
        self.device_view = DeviceView(self.state, None, parent=self.instrument_dock)
        self.instrument_dock.setWidget(self.device_view)
        self.addDockWidget(Qt.RightDockWidgetArea, self.instrument_dock)

    def _handle_model_registered(self, model_id: str):
        """Handle new model registration."""
        logger.debug(f"Model {model_id} registered")
        # Views are created on-demand when activated

    def _handle_active_model(self, model_id: str):
        """
        Handle model activation by showing appropriate view.
        Views are created on first activation if they don't exist.
        """
        logger.debug(f"Handling activation of model {model_id}")
        
        if model_id:
            if model_id in self._content_docks:
                dock = self._content_docks[model_id]
                if not dock.isVisible():
                    dock.show()
                dock.raise_()
                
                # Handle tabbed docks
                if self.content_window.tabifiedDockWidgets(dock):
                    dock.show()
                    dock.raise_()
            else:
                self.open_content(model_id)
            
            self.hide_welcome()
        else:
            self.show_welcome()

    def open_content(self, model_id: str) -> bool:
        """Open or show content for the given model."""
        model = self.state.get_model(model_id)
        if not model:
            return False

        # Create view if needed
        if model_id not in self._content_views:
            view_class = self._get_view_class(model)
            if not view_class:
                return False
                
            view = view_class(self.state, model_id, self)
            dock = QDockWidget(model.get_property('name', str(model_id)), self.content_window)
            dock.setWidget(view)
            
            self._content_views[model_id] = view
            self._content_docks[model_id] = dock
            
            # Add to content window
            self.content_window.addDockWidget(Qt.RightDockWidgetArea, dock)
            
            # Tabify with existing content
            existing_docks = [d for mid, d in self._content_docks.items() if mid != model_id]
            if existing_docks:
                self.content_window.tabifyDockWidget(existing_docks[-1], dock)
                
        dock = self._content_docks[model_id]
        dock.show()
        dock.raise_()
        
        return True

    def _on_run_test(self):
        """Run the currently selected test."""
        active_model = self.state.get_active_model()
        if isinstance(active_model, TestScript):
            logger.debug(f"Running test: {active_model.get_property('name')}")
            self.state.engine.run_test(active_model.id)

    def _on_stop_test(self):
        """Stop the currently running test."""
        active_model = self.state.get_active_model()
        if isinstance(active_model, TestScript):
            logger.debug(f"Stopping test: {active_model.get_property('name')}")
            self.state.engine.stop_test(active_model.id)

    def _connect_signals(self):
        """Connect to ApplicationState signals."""
        self.state.model_registered.connect(self._handle_model_registered)
        self.state.active_model_changed.connect(self._handle_active_model)
        self.state.model_changed.connect(self._handle_model_changed)
        self.state.model_removed.connect(self._handle_model_removed)
        
    def _setup_title_bar(self):
        """Set up custom frameless window title bar."""
        self.title_bar = TitleBar(self, state=self.state)
        self.setMenuWidget(self.title_bar)
        self.title_bar.windowMinimizeRequested.connect(self.showMinimized)
        self.title_bar.windowMaximizeRequested.connect(self._toggle_maximize)
        self.title_bar.windowCloseRequested.connect(self.close)

    def _setup_status_bar(self):
        """Set up status bar for application messages."""
        self.status_bar = StatusBar(self.state)
        self.setStatusBar(self.status_bar)

    def show_welcome(self):
        """Show welcome screen when no content is open."""
        if self._welcome_dock is None:
            welcome = WelcomeWidget(self.state, self)
            self._welcome_dock = QDockWidget("Welcome", self.content_window)
            self._welcome_dock.setWidget(welcome)
            self._welcome_dock.setFeatures(
                QDockWidget.DockWidgetMovable | 
                QDockWidget.DockWidgetFloatable
            )
            self.content_window.addDockWidget(Qt.RightDockWidgetArea, self._welcome_dock)
        else:
            self._welcome_dock.show()
            self._welcome_dock.raise_()

    def hide_welcome(self):
        """Hide welcome screen when content is shown."""
        if self._welcome_dock is not None:
            self._welcome_dock.hide()

    def _get_view_class(self, model) -> Optional[Type[BaseWidget]]:
        """Get the appropriate view class for a given model type."""
        model_type = type(model).__name__
        return {
            'TestScript': ScriptTab,
            'TestResult': ResultTab,
            'Plot': PlotTab,
            'DataTable': TableTab
        }.get(model_type)

    def _handle_model_changed(self, model_id: str, prop: str, value: object):
        """Update dock title when model name changes."""
        if prop == 'name' and model_id in self._content_docks:
            self._content_docks[model_id].setWindowTitle(str(value))

    def _handle_model_removed(self, model_id: str):
        """Clean up views and docks when a model is removed."""
        if model_id in self._content_docks:
            dock = self._content_docks.pop(model_id)
            view = self._content_views.pop(model_id, None)
            
            # Clean up view if it has a cleanup method
            if view and hasattr(view, 'cleanup'):
                view.cleanup()
            
            dock.setParent(None)
            dock.deleteLater()
            
            # Show welcome if no content remains
            if not self._content_docks:
                self.show_welcome()

    def _toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _toggle_file_explorer(self):
        """Toggle file explorer visibility."""
        pass  # TODO: Implement file explorer toggle

    def _on_new_script(self):
        """Handle new script creation."""
        pass  # TODO: Implement new script creation

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
            
        # Restore content window state
        content_state = settings.value("contentState")
        if content_state:
            self.content_window.restoreState(content_state)

    def paintEvent(self, event: QPaintEvent):
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
        settings.setValue("contentState", self.content_window.saveState())
        
        # Clean up all views
        for view in self._content_views.values():
            if hasattr(view, 'cleanup'):
                view.cleanup()
                
        super().closeEvent(event)

class WelcomeWidget(QWidget):
    """Welcome screen shown when no content is open."""
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up welcome screen UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        welcome_text = (
            "<h1>Welcome to PyMetr</h1>"
            "<p>Start by opening a script or connecting an instrument.</p>"
            "<p>Use the ribbon actions above to get started.</p>"
        )
        
        label = QLabel(welcome_text)
        label.setStyleSheet("""
            QLabel {
                color: #CCCCCC;
                font-size: 14px;
            }
            h1 {
                color: #FFFFFF;
                margin-bottom: 20px;
            }
        """)
        
        layout.addWidget(label)