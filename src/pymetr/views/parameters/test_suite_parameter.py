from typing import Optional, Any
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from pyqtgraph.parametertree import Parameter

from .base import ModelParameter, ModelParameterItem, ParameterWidget
from pymetr.core.logging import logger
from pymetr.models.test import TestSuite, TestStatus

class TestSuiteStatusWidget(ParameterWidget):
    """Widget showing suite status and aggregated info."""
    def __init__(self, param, parent=None):
        super().__init__(param, parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                border-radius: 2px;
                font-weight: 500;
                min-width: 60px;
            }
        """)
        
        layout.addWidget(self.status_label)
        layout.addStretch()
        
        # Set initial state
        self._update_ui_state(TestStatus.READY)
    
    def _update_ui_state(self, status: TestStatus):
        """Update UI based on status."""
        styles = {
            TestStatus.READY: {"border": "#95A5A6", "bg": "#2A2A2A"},
            TestStatus.RUNNING: {"border": "#3498DB", "bg": "#2A2A2A"},
            TestStatus.PASS: {"border": "#2ECC71", "bg": "#2A2A2A"},
            TestStatus.FAIL: {"border": "#E74C3C", "bg": "#2A2A2A"},
            TestStatus.ERROR: {"border": "#F1C40F", "bg": "#2A2A2A"},
            TestStatus.COMPLETE: {"border": "#2ECC71", "bg": "#2A2A2A"}
        }
        
        style = styles.get(status, styles[TestStatus.READY])
        self.status_label.setStyleSheet(self.status_label.styleSheet() + f"""
            border: 1px solid {style['border']};
            background: {style['bg']};
        """)
        self.status_label.setText(status.name)
    
    def _process_pending_update(self):
        """Process status updates."""
        updates = self._pending_updates
        self._pending_updates = {}
        
        if 'status' in updates:
            status = updates['status']
            if isinstance(status, str):
                try:
                    status = TestStatus[status.upper()]
                except KeyError:
                    status = TestStatus.ERROR
            self._update_ui_state(status)

class TestSuiteParameterItem(ModelParameterItem):
    """Parameter item for test suites."""
    
    def makeWidget(self) -> Optional[QWidget]:
        """Create the status widget."""
        try:
            self.widget = TestSuiteStatusWidget(self.param)
            return self.widget
        except Exception as e:
            logger.error(f"Error creating suite widget: {e}")
            return None
    
    def updateWidget(self, **kwargs):
        """Update the widget with new values."""
        if self.widget:
            self.widget.queue_update(**kwargs)
    
    def addCustomContextActions(self, menu: QMenu):
        """Add suite-specific context actions."""
        # Add Run Suite action
        if self._context_icons:
            run_action = menu.addAction(
                self._context_icons.get('run', QIcon()),
                "Run Suite"
            )
            run_action.triggered.connect(self._handle_run_suite)
            
            # Add Stop Suite action (enabled only when running)
            stop_action = menu.addAction(
                self._context_icons.get('stop', QIcon()),
                "Stop Suite"
            )
            stop_action.triggered.connect(self._handle_stop_suite)
            
            # Enable/disable based on current status
            model = self.param.state.get_model(self.param.model_id)
            if model:
                status = model.get_property('status', 'READY')
                stop_action.setEnabled(status == 'RUNNING')
                run_action.setEnabled(status != 'RUNNING')
    
    def _handle_run_suite(self):
        """Handle Run Suite action."""
        if hasattr(self.param, 'state'):
            self.param.state.engine.run_suite(self.param.model_id)
    
    def _handle_stop_suite(self):
        """Handle Stop Suite action."""
        if hasattr(self.param, 'state'):
            self.param.state.engine.stop_suite()

class TestSuiteParameter(ModelParameter):
    """Parameter for test suites."""
    
    itemClass = TestSuiteParameterItem
    
    def __init__(self, **opts):
        opts['type'] = 'testsuite'
        super().__init__(**opts)
        self.can_export = True
        
        model = self.state.get_model(self.model_id) if self.state and self.model_id else None
        self.setupParameters(model)
    
    def setupParameters(self, model: Optional[TestSuite]):
        """Set up suite configuration parameters."""
        if not model:
            return
            
        # Add parameters for run configurations
        configs = [config.get_property('name') for config in model.get_run_configs()]
        if configs:
            config_param = Parameter.create(
                name='run_config',
                type='list',
                value=configs[0],
                limits=configs
            )
            self.addChild(config_param)
    
    def handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        if hasattr(self, 'widget'):
            self.widget.queue_update(**{prop: value})