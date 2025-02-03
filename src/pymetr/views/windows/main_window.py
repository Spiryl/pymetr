from typing import Optional, TYPE_CHECKING
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QDockWidget,
    QVBoxLayout, QApplication, QMessageBox
)
from PySide6.QtCore import Qt, QSize

from ..widgets.tree_view import ModelTreeView
from ..widgets.tab_manager import TabManager
from ..widgets.instrument_dock import InstrumentDock
from ..ribbon.manager import RibbonManager

if TYPE_CHECKING:
    from pymetr.state import ApplicationState

class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self, state: 'ApplicationState'):
        super().__init__()
        self.state = state
        
        self._setup_ui()
        self._setup_actions()
        
        # Set window properties
        self.setWindowTitle("pymetr")
        self.setMinimumSize(QSize(1200, 800))
    
    def _setup_ui(self) -> None:
        """Setup the main window UI layout"""
        # Create ribbon
        self.ribbon = RibbonManager(self.state)
        self.ribbon.setMaximumHeight(120)
        self.setMenuWidget(self.ribbon)  # Ensure ribbon spans the entire top
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        layout.setSpacing(0)  # Remove any layout spacing
        
        # Create tab manager
        self.tab_manager = TabManager(self.state)
        layout.addWidget(self.tab_manager)
        
        # 1) Create the Models dock
        tree_dock = QDockWidget("Models", self)
        tree_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        # tree_dock.setMinimumWidth(300)
        self.tree_view = ModelTreeView(self.state)
        tree_dock.setWidget(self.tree_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, tree_dock)

        # 2) Create the InstrumentDock on the right
        self.instrument_dock = InstrumentDock(self.state, parent=self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.instrument_dock)
    
    def _setup_actions(self) -> None:
        """Connect actions to handlers"""
        self.ribbon.action_triggered.connect(self._handle_action)
    
    def _handle_action(self, action_id: str) -> None:
        """Handle ribbon action triggered"""
        try:
            # Execute action through action manager
            result = self.state.actions.execute(action_id)
            
            if not result.success:
                QMessageBox.warning(
                    self,
                    "Action Failed",
                    f"Failed to execute action: {result.error}"
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred: {str(e)}"
            )

# status_bar_manager.py (or inside main_window.py)
class StatusObserver:
    def __init__(self, state, status_bar):
        self.state = state
        self.status_bar = status_bar
        
        state.signals.connect("instruments_discovered", self.on_instruments_discovered)
        state.signals.connect("instrument_connected", self.on_instrument_connected)
        state.signals.connect("error", self.on_error)

    def on_instruments_discovered(self, discovered):
        msg = f"Discovered {len(discovered)} instruments"
        self.status_bar.showMessage(msg)

    def on_instrument_connected(self, instrument_id):
        msg = f"Instrument connected: {instrument_id}"
        self.status_bar.showMessage(msg)

    def on_error(self, error_msg):
        self.status_bar.showMessage(f"Error: {error_msg}", 5000)


def create_application(state: 'ApplicationState') -> tuple[QApplication, MainWindow]:
    """Create and setup the application and main window"""
    app = QApplication([])
    
    # Set application properties
    app.setApplicationName("pymetr")
    app.setApplicationVersion("0.1.0")
    
    # Create main window
    window = MainWindow(state)
    window.show()
    
    return app, window
