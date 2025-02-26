from pathlib import Path
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QAction, QKeySequence
from PySide6.QtWidgets import QToolBar, QMessageBox, QWidget

# Import necessary services and actions
from pymetr.core.actions import STANDARD_ACTIONS, FileActions, RunActions, InstrumentActions
from pymetr.core.logging import logger

class QuickToolBar(QToolBar):
    """
    Quick access toolbar with common application actions.
    Provides buttons for common operations like file management, test execution, etc.
    
    The toolbar handles its own action logic rather than delegating to MainWindow,
    following a more decoupled design pattern.
    """
    
    def __init__(self, state, parent=None):
        super().__init__("QuickTools", parent)
        self.state = state
        self.setMovable(False)
        self.setIconSize(QSize(28, 28))
        self._setup_actions()
        
    def _setup_actions(self):
        """Set up toolbar actions and connect signals."""
        icons_path = Path(__file__).parent / 'icons'
        
        # ===== Top Group: File Operations =====
        # New Suite
        self.new_suite_action = QAction(
            QIcon(str(icons_path / 'new_suite.png')),
            "New Suite",
            self
        )
        self.new_suite_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        self.new_suite_action.triggered.connect(self._on_new_suite)
        
        # Open Suite
        self.open_suite_action = QAction(
            QIcon(str(icons_path / 'open_suite.png')),
            "Open Suite",
            self
        )
        self.open_suite_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        self.open_suite_action.triggered.connect(self._on_open_suite)
        
        # New Script
        self.new_script_action = QAction(
            QIcon(str(icons_path / 'new_script.png')),
            "New Script",
            self
        )
        self.new_script_action.setShortcut(QKeySequence("Ctrl+N"))
        self.new_script_action.triggered.connect(self._on_new_script)
        
        # Open Script
        self.open_script_action = QAction(
            QIcon(str(icons_path / 'open_script.png')),
            "Open Script",
            self
        )
        self.open_script_action.setShortcut(QKeySequence("Ctrl+O"))
        self.open_script_action.triggered.connect(self._on_open_script)
        
        # ===== Middle Group: Test Actions =====
        # Run Selected Test
        self.run_test_action = QAction(
            QIcon(str(icons_path / 'run.png')),
            "Run Test",
            self
        )
        self.run_test_action.setShortcut(QKeySequence("F5"))
        self.run_test_action.triggered.connect(self._on_run_test)
        
        # Stop Test
        self.stop_test_action = QAction(
            QIcon(str(icons_path / 'stop.png')),
            "Stop Test",
            self
        )
        self.stop_test_action.setShortcut(QKeySequence("F6"))
        self.stop_test_action.triggered.connect(self._on_stop_test)
        
        # Toggle Instrument Panel
        self.discover_instruments_action = QAction(
            QIcon(str(icons_path / 'instruments.png')),
            "Discover Instruments",
            self
        )
        self.discover_instruments_action.setShortcut(QKeySequence("Ctrl+I"))
        self.discover_instruments_action.triggered.connect(self._on_discover_instruments)
        
        # ===== Bottom Group: Utility Actions =====
        # Clear All
        self.clear_all_action = QAction(
            QIcon(str(icons_path / 'clear.png')),
            "Clear All",
            self
        )
        self.clear_all_action.triggered.connect(self._on_clear_all)
        
        # Add actions to toolbar in groups
        # Top group - File operations
        self.addAction(self.new_suite_action)
        self.addAction(self.open_suite_action)
        self.addAction(self.new_script_action)
        self.addAction(self.open_script_action)
        
        
        # Middle group - Test operations
        self.addAction(self.run_test_action)
        self.addAction(self.stop_test_action)
        self.addAction(self.discover_instruments_action)
        
        self.addSeparator()
        
        # Bottom group - Utility operations
        self.addAction(self.clear_all_action)
        
    # ===== Action Handlers =====
    def _on_new_suite(self):
        """Create a new test suite."""
        try:
            self._trigger_action('new_suite')
        except Exception as e:
            self._show_error(f"Failed to create new suite: {str(e)}")
            
    def _on_open_suite(self):
        """Open an existing test suite."""
        try:
            self._trigger_action('open_suite')
        except Exception as e:
            self._show_error(f"Failed to open suite: {str(e)}")
            
    def _on_new_script(self):
        """Create a new script."""
        try:
            self._trigger_action('new_script')
        except Exception as e:
            self._show_error(f"Failed to create new script: {str(e)}")
            
    def _on_open_script(self):
        """Open an existing script."""
        try:
            self._trigger_action('open_script')
        except Exception as e:
            self._show_error(f"Failed to open script: {str(e)}")
            
    def _on_run_test(self):
        """Run the selected test."""
        try:
            self._trigger_action('run_script')
        except Exception as e:
            self._show_error(f"Failed to run test: {str(e)}")
            
    def _on_stop_test(self):
        """Stop the running test."""
        try:
            self._trigger_action('stop_script')
        except Exception as e:
            self._show_error(f"Failed to stop test: {str(e)}")
            
    def _on_discover_instruments(self):
        """Open instrument discovery."""
        try:
            self._trigger_action('discover_instruments')
        except Exception as e:
            self._show_error(f"Failed to start instrument discovery: {str(e)}")
            
    def _on_clear_all(self):
        """Clear all models from the state."""
        try:
            # Get confirmation before proceeding
            parent = self.parent()
            if isinstance(parent, QWidget):
                result = QMessageBox.question(
                    parent,
                    "Clear All Models",
                    "Are you sure you want to clear all models? This action cannot be undone.",
                    QMessageBox.Yes | QMessageBox.No
                )
                if result == QMessageBox.No:
                    return
                    
            # Get all model IDs
            model_ids = list(self.state._models.keys())
            
            # Remove each model
            for model_id in model_ids:
                self.state.remove_model(model_id)
                
            logger.info("QuickToolBar: All models cleared")
            
        except Exception as e:
            self._show_error(f"Failed to clear models: {str(e)}")
            
    def _trigger_action(self, action_id: str):
        """Trigger a standard action if available and executable."""
        action_obj = STANDARD_ACTIONS.get(action_id)
        if not action_obj:
            logger.warning(f"QuickToolBar: No STANDARD_ACTIONS entry for '{action_id}'")
            return

        if not action_obj.can_execute(self.state):
            logger.warning(f"QuickToolBar: Action '{action_id}' cannot execute in current state.")
            return

        logger.debug(f"QuickToolBar: calling handler for '{action_id}'")
        action_obj.handler(self.state)
        
    def _show_error(self, message: str):
        """Show error message to user."""
        logger.error(f"QuickToolBar error: {message}")
        parent = self.parent()
        if isinstance(parent, QWidget):
            QMessageBox.critical(parent, "Error", message)