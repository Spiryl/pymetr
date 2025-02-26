from typing import Optional, Any
from PySide6.QtWidgets import QWidget, QProgressBar, QHBoxLayout, QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from pymetr.models import TestStatus, TestScript
from pymetr.core.logging import logger

from .base import ModelParameter, ModelParameterItem, ParameterWidget

class TestProgressWidget(ParameterWidget):
    """Widget showing test progress with status."""
    
    def __init__(self, param, parent=None):
        super().__init__(param, parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(18)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar, 1)
        
        # Define styles for test statuses.
        self.status_styles = {
            TestStatus.READY: {'border': '#02FEE4', 'chunk': '#1e1e1e', 'background': '#1e1e1e'},
            TestStatus.RUNNING: {'border': '#5E57FF', 'chunk': '#5E57FF', 'background': '#1e1e1e'},
            TestStatus.PASS: {'border': '#4BFF36', 'chunk': '#1e1e1e', 'background': '#1e1e1e'},
            TestStatus.FAIL: {'border': '#F23CA6', 'chunk': '#1e1e1e', 'background': '#1e1e1e'},
            TestStatus.ERROR: {'border': '#F23CA6', 'chunk': '#1e1e1e', 'background': '#1e1e1e'},
            TestStatus.COMPLETE: {'border': '#4BFF36', 'chunk': '#1e1e1e', 'background': '#1e1e1e'},
        }
        
        # Initially show "Not Reported" if no progress is set.
        self._apply_style(TestStatus.READY, 0)
    
    def _process_pending_update(self):
        # logger.debug(f"TestProgressWidget._process_pending_update: {self._pending_updates}")
        self._pending_updates.clear()
        
        status_val = self.param.get_model_property("status", "READY")
        progress_val = self.param.get_model_property("progress", 0)
        
        # Handle status value being either a TestStatus enum or a string.
        if isinstance(status_val, TestStatus):
            status = status_val
        elif isinstance(status_val, str):
            try:
                status = TestStatus[status_val.upper()]
            except KeyError:
                logger.error(f"TestProgressWidget: Invalid status string '{status_val}'. Defaulting to ERROR.")
                status = TestStatus.ERROR
        else:
            status = TestStatus.ERROR

        try:
            progress = float(progress_val)
            progress = max(0, min(100, progress))
        except Exception as e:
            logger.error(f"TestProgressWidget: Invalid progress value: {progress_val} - {e}")
            progress = 0
        
        # logger.debug(f"TestProgressWidget updating: status={status.name}, progress={progress}")
        self._apply_style(status, progress)
    
    def _apply_style(self, status: TestStatus, progress: float):
        style = self.status_styles.get(status, self.status_styles[TestStatus.ERROR])
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {style['border']};
                border-radius: 2px;
                background: {style['background']};
                text-align: center;
                padding: 1px;
            }}
            QProgressBar::chunk {{
                background-color: {style['chunk']};
            }}
        """)
        self.progress_bar.setValue(int(progress))
        self.progress_bar.setFormat(f"{status.name} ({progress:.1f}%)")
    
    def contextMenuEvent(self, event):
        """Handle context menu."""
        try:
            menu = QMenu(self)
            status = TestStatus[self.param.get_model_property('status', 'READY').upper()]
            
            if status == TestStatus.RUNNING:
                stop_action = menu.addAction("Stop Test")
                stop_action.triggered.connect(self._handle_stop)
            elif status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR, TestStatus.COMPLETE]:
                run_action = menu.addAction("Run Test")
                run_action.triggered.connect(self._handle_run)
                menu.addSeparator()
                reset_action = menu.addAction("Reset Status")
                reset_action.triggered.connect(self._handle_reset)
            else:  # READY
                run_action = menu.addAction("Run Test")
                run_action.triggered.connect(self._handle_run)
                
            menu.exec_(event.globalPos())
        except Exception as e:
            logger.error(f"Error showing context menu: {e}")
    
    def _handle_run(self):
        """Handle run action."""
        if hasattr(self.param, 'state'):
            self.param.state.engine.run_test_script(self.param.model_id)
    
    def _handle_stop(self):
        """Handle stop action."""
        if hasattr(self.param, 'state'):
            self.param.state.engine.script_runner.stop()
    
    def _handle_reset(self):
        """Handle reset action."""
        if hasattr(self.param, 'state'):
            model = self.param.state.get_model(self.param.model_id)
            if model:
                model.set_property('status', TestStatus.READY)
                model.set_property('progress', 0)

class TestScriptParameterItem(ModelParameterItem):
    """Parameter item for test scripts."""
    
    def makeWidget(self) -> Optional[QWidget]:
        """Create the progress widget."""
        logger.debug(f"Creating widget for parameter {self.param.name()}")
        try:
            self.widget = TestProgressWidget(self.param)
            return self.widget
        except Exception as e:
            logger.error(f"Error creating test widget: {e}")
            return None
    
    def updateWidget(self, **kwargs):
        """Update the widget with new values."""
        if self.widget:
            self.widget.queue_update(**kwargs)
    
    def addCustomContextActions(self, menu: QMenu):
        """Add test-specific context menu actions."""
        if not self._context_icons:
            logger.debug("No context icons available")
            return
            
        # Add Run action
        run_action = menu.addAction(
            self._context_icons.get('run', QIcon()),
            "Run Test"
        )
        run_action.triggered.connect(self._handle_run)
        
        # Add Stop action (enabled only when running)
        stop_action = menu.addAction(
            self._context_icons.get('stop', QIcon()),
            "Stop Test"
        )
        stop_action.triggered.connect(self._handle_stop)
        
        # Add separator before standard actions
        menu.addSeparator()
        
        # Enable/disable based on current status
        model = self.param.state.get_model(self.param.model_id)
        if model:
            status = model.get_property('status', 'READY')
            stop_action.setEnabled(status == 'RUNNING')
            run_action.setEnabled(status != 'RUNNING')
    
    def _handle_run(self):
        """Handle Run Test action."""
        if hasattr(self.param, 'state'):
            self.param.state.engine.run_test_script(self.param.model_id)
    
    def _handle_stop(self):
        """Handle Stop Test action."""
        if hasattr(self.param, 'state'):
            self.param.state.engine.script_runner.stop()

class TestScriptParameter(ModelParameter):
    """Parameter for test scripts."""
    
    itemClass = TestScriptParameterItem
    
    def __init__(self, **opts):
        opts['type'] = 'testscript'
        super().__init__(**opts)
        self.can_export = True
    
    def setupParameters(self, model: Optional[TestScript]):
        """No child parameters needed - only shows model children."""
        pass
    
    def handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        if hasattr(self, 'widget'):
            self.widget.queue_update(**{prop: value})