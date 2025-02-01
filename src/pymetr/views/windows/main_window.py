# src/pymetr/views/windows/main_window.py
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QDockWidget, 
    QVBoxLayout, QApplication, QMessageBox
)
from PySide6.QtCore import Qt, QSize

from ..widgets.tree_view import ModelTreeView
from ..widgets.tab_manager import TabManager
from ..ribbon.manager import RibbonManager

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
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create ribbon
        self.ribbon = RibbonManager(self.state)
        layout.addWidget(self.ribbon)
        
        # Create tab manager
        self.tab_manager = TabManager(self.state)
        layout.addWidget(self.tab_manager)
        
        # Create model tree dock
        tree_dock = QDockWidget("Models", self)
        tree_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.tree_view = ModelTreeView(self.state)
        tree_dock.setWidget(self.tree_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, tree_dock)
        
        # No margins for main layout
        layout.setContentsMargins(0, 0, 0, 0)
        
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