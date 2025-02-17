from PySide6.QtWidgets import QWidget, QProgressBar, QHBoxLayout, QMenu
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon

from .base import ModelParameter, ModelParameterItem
from pymetr.core.logging import logger

class ScriptStatus:
    """Status for test script execution - controlled by engine."""
    NOT_RUN = "Not Run"
    RUNNING = "Running"
    COMPLETE = "Complete" 
    ERROR = "Error"
    
    STYLES = {
        NOT_RUN: {
            "color": "#dddddd",
            "border": "#95A5A6",
            "chunk": "#95A5A6"
        },
        RUNNING: {
            "color": "#dddddd",
            "border": "#3498DB",
            "chunk": "#3498DB"
        },
        COMPLETE: {
            "color": "#dddddd",
            "border": "#2ECC71",
            "chunk": "#2ECC71"
        },
        ERROR: {
            "color": "#dddddd",
            "border": "#F1C40F",
            "chunk": "#F1C40F"
        }
    }

class TestScriptStatusWidget(QWidget):
    """Widget showing test script status and progress."""
    
    # Signals for actions
    run_clicked = Signal()
    stop_clicked = Signal()
    reset_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = ScriptStatus.NOT_RUN
        self._setup_ui()
        
    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.setLayout(layout)
        
        # Progress bar with status display
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(18)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar, 1)
        
        # Set initial status
        self.update_status(self._status)
            
    def update_status(self, status: str, progress: float = None):
        """Update display with status and optional progress."""
        if not self.progress_bar:
            logger.debug("Progress bar no longer exists")
            return
            
        try:
            self._status = status
            style = ScriptStatus.STYLES.get(status, ScriptStatus.STYLES[ScriptStatus.NOT_RUN])
            
            if status == ScriptStatus.RUNNING and progress is not None:
                # Show progress during run
                self.progress_bar.setValue(int(progress))
                self.progress_bar.setFormat(f"{progress:.1f}%")
            else:
                # Show status and set appropriate value
                value = 100 if status == ScriptStatus.COMPLETE else 0
                self.progress_bar.setValue(value)
                self.progress_bar.setFormat(status)
            
            # Update progress bar styling
            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid {style['border']};
                    border-radius: 2px;
                    background: #1e1e1e;
                    color: {style['color']};
                    text-align: center;
                    padding: 1px;
                }}
                QProgressBar::chunk {{
                    background-color: {style['chunk']};
                }}
            """)
            
            self.progress_bar.setTextVisible(True)
            
        except Exception as e:
            logger.error(f"Error updating script status widget: {e}")
        
    def contextMenuEvent(self, event):
        """Show context menu based on current status."""
        try:
            menu = QMenu(self)
            
            if self._status == ScriptStatus.RUNNING:
                stop_action = menu.addAction("Stop Test")
                stop_action.triggered.connect(self.stop_clicked.emit)
            else:
                run_action = menu.addAction("Run Test")
                run_action.triggered.connect(self.run_clicked.emit)
                
                if self._status in [ScriptStatus.COMPLETE, ScriptStatus.ERROR]:
                    menu.addSeparator()
                    reset_action = menu.addAction("Reset Status")
                    reset_action.triggered.connect(self.reset_clicked.emit)
            
            menu.exec_(event.globalPos())
            
        except Exception as e:
            logger.error(f"Error showing context menu: {e}")

class TestScriptParameterItem(ModelParameterItem):
    """Parameter item for test script in tree."""
    
    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.hideWidget = False
        self.widget = None
        
    def makeWidget(self):
        """Create the status widget."""
        logger.debug("TestScriptParameterItem: Making widget")
        self.widget = TestScriptStatusWidget()
        self.widget.run_clicked.connect(self._handle_run)
        self.widget.stop_clicked.connect(self._handle_stop)
        self.widget.reset_clicked.connect(self._handle_reset)
        return self.widget
        
    def valueChanged(self, param, val):
        """Handle progress updates."""
        if self.widget:
            self.widget.update_status(param.status(), val)
            
    def optsChanged(self, param, opts):
        """Handle status updates."""
        super().optsChanged(param, opts)
        if 'status' in opts and self.widget:
            self.widget.update_status(opts['status'], param.value())
            
    def treeWidgetChanged(self):
        """Called when this item is added or removed from a tree."""
        super().treeWidgetChanged()
        logger.debug("TestScriptParameterItem: Tree widget changed")
        
        if self.widget is None:
            self.widget = self.makeWidget()
            
        tree = self.treeWidget()
        if tree is not None:
            logger.debug("TestScriptParameterItem: Setting widget in column 1")
            tree.setItemWidget(self, 1, self.widget)
            
    def _handle_run(self):
        """Handle run button click."""
        try:
            state = self.param.state
            if state and self.param.model_id:
                state.engine.run_test_script(self.param.model_id)
        except Exception as e:
            logger.error(f"Error running script: {e}")
            
    def _handle_stop(self):
        """Handle stop button click."""
        try:
            state = self.param.state
            if state and state.engine and state.engine.script_runner:
                state.engine.script_runner.stop()
        except Exception as e:
            logger.error(f"Error stopping script: {e}")
            
    def _handle_reset(self):
        """Handle reset button click."""
        try:
            state = self.param.state
            if state and self.param.model_id:
                script = state.get_model(self.param.model_id)
                if script:
                    script.set_property('status', ScriptStatus.NOT_RUN)
                    script.set_property('progress', 0)
        except Exception as e:
            logger.error(f"Error resetting script: {e}")

    def cleanup(self):
        """Clean up widget resources."""
        try:
            if self.widget:
                self.widget.deleteLater()
                self.widget = None
        except Exception as e:
            logger.error(f"Error cleaning up TestScriptParameterItem: {e}")
        super().cleanup()
    def _handle_run(self):
        try:
            state = self.param.state
            if state and self.param.model_id:
                state.engine.run_test_script(self.param.model_id)
        except Exception as e:
            logger.error(f"Error running script: {e}")
            
    def _handle_stop(self):
        try:
            state = self.param.state
            if state and state.engine and state.engine.script_runner:
                state.engine.script_runner.stop()
        except Exception as e:
            logger.error(f"Error stopping script: {e}")
            
    def _handle_reset(self):
        try:
            state = self.param.state
            if state and self.param.model_id:
                script = state.get_model(self.param.model_id)
                if script:
                    script.status = ScriptStatus.NOT_RUN
                    script.set_property('progress', 0)
        except Exception as e:
            logger.error(f"Error resetting script: {e}")

    def add_context_menu_actions(self, menu):
        """Add test script specific menu actions"""
        if self.widget:  # Our ScriptStatusWidget
            if self.widget._status == ScriptStatus.RUNNING:
                stop_action = menu.addAction("Stop Test")
                stop_action.triggered.connect(self.widget.stop_clicked.emit)
            else:
                run_action = menu.addAction("Run Test")
                run_action.triggered.connect(self.widget.run_clicked.emit)
                
                if self.widget._status in [ScriptStatus.PASS, ScriptStatus.FAIL, ScriptStatus.ERROR, ScriptStatus.COMPLETE]:
                    menu.addSeparator()
                    reset_action = menu.addAction("Reset Status")
                    reset_action.triggered.connect(self.widget.reset_clicked.emit)
                    

class TestScriptParameter(ModelParameter):
    """Parameter for test script control."""
    itemClass = TestScriptParameterItem
    
    def __init__(self, **opts):
        opts['type'] = 'testscript'
        opts.setdefault('status', ScriptStatus.NOT_RUN)
        super().__init__(**opts)
        self._status = opts['status']
        self._progress = 0
        
    def status(self) -> str:
        """Get current status."""
        if self.state and self.model_id:
            model = self.state.get_model(self.model_id)
            if model:
                self._status = model.get_property('status', ScriptStatus.NOT_RUN)
        return self._status
        
    def value(self):
        """Get current progress value."""
        if self.state and self.model_id:
            model = self.state.get_model(self.model_id)
            if model:
                self._progress = model.get_property('progress', 0)
        return self._progress
        
    def setValue(self, value):
        """Set progress value."""
        try:
            self._progress = float(value)
            super().setValue(self._progress)
        except (TypeError, ValueError) as e:
            logger.error(f"Invalid progress value: {value}. Error: {e}")
        
    def setStatus(self, status: str):
        """Update script status."""
        if status not in ScriptStatus.STYLES:
            logger.warning(f"Invalid status '{status}' - must be one of: {', '.join(ScriptStatus.STYLES.keys())}")
            return
            
        self._status = status
        self.setOpts(status=status)