from typing import Optional, Any
from PySide6.QtWidgets import QWidget, QProgressBar, QHBoxLayout, QMenu
from PySide6.QtCore import Qt
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
        
        # Define status styles
        self.status_styles = {
            TestStatus.READY: {
                'color': '#aaaaaa',
                'background': '#1e1e1e',
                'chunk': '#1e1e1e',
                'border': '#95A5A6'
            },
            TestStatus.RUNNING: {
                'color': '#aaaaaa',
                'background': '#1e1e1e',
                'chunk': '#3498DB',
                'border': '#3498DB'
            },
            TestStatus.PASS: {
                'color': '#aaaaaa',
                'background': '#1e1e1e',
                'chunk': '#1e1e1e',
                'border': '#2ECC71'
            },
            TestStatus.FAIL: {
                'color': '#aaaaaa',
                'background': '#1e1e1e',
                'chunk': '#1e1e1e',
                'border': '#E74C3C'
            },
            TestStatus.ERROR: {
                'color': '#aaaaaa',
                'background': '#1e1e1e',
                'chunk': '#1e1e1e',
                'border': '#F1C40F'
            },
            TestStatus.COMPLETE: {
                'color': '#aaaaaa',
                'background': '#1e1e1e',
                'chunk': '#1e1e1e',
                'border': '#2ECC71'
            }
        }
        
        # Set initial style to READY with 0 progress
        self._apply_style(TestStatus.READY, 0)
    
    def _apply_style(self, status: TestStatus, progress: float):
        """Apply status-specific styling with progress."""
        style = self.status_styles.get(status, self.status_styles[TestStatus.READY])
        
        # Apply style to progress bar
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
        if status == TestStatus.RUNNING and progress is not None:
            self.progress_bar.setFormat(f"{progress:.1f}%")
        else:
            value = 100 if status in [TestStatus.PASS, TestStatus.COMPLETE] else 0
            self.progress_bar.setValue(value)
            self.progress_bar.setFormat(status.name)
    
    def _process_pending_update(self):
        """Process queued updates."""
        updates = self._pending_updates
        self._pending_updates = {}
        
        status = updates.get('status')
        progress = updates.get('progress')
        
        if status is not None:
            # Convert string to enum if needed
            if isinstance(status, str):
                status = TestStatus[status.upper()]
            current_status = status
        else:
            current_status = TestStatus.READY
        
        if progress is not None:
            try:
                current_progress = float(progress)
                current_progress = max(0, min(100, current_progress))
            except (TypeError, ValueError):
                current_progress = 0
        else:
            current_progress = self.progress_bar.value()
        
        self._apply_style(current_status, current_progress)
    
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
        """Add test-specific context actions."""
        # No additional actions needed - handled by widget's context menu
        pass

class TestScriptParameter(ModelParameter):
    """
    Parameter for test scripts. Only shows children (results, plots, etc.)
    and provides progress tracking.
    """
    
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
