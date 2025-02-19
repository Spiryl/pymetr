from typing import Optional, Any
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QMenu, QProgressBar
from PySide6.QtCore import Qt

from .base import ModelParameter, ModelParameterItem, ParameterWidget
from pymetr.core.logging import logger
from pymetr.models import TestResult, ResultStatus


class ResultStatusWidget(ParameterWidget):
    """
    Enhanced widget displaying result status and progress.
    """
    def __init__(self, param, parent=None):
        super().__init__(param, parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(18)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar, 1)  # Give progress bar most of the space
        
        # Status Label
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumWidth(60)  # Ensure status is always visible
        layout.addWidget(self.status_label)
        
        # Status styles with progress bar colors
        self.status_styles = {
            ResultStatus.PASS: {
                'text': '#dddddd',
                'background': '#1e1e1e',
                'border': '#2ECC71',
                'chunk': '#2ECC71'
            },
            ResultStatus.FAIL: {
                'text': '#dddddd',
                'background': '#1e1e1e',
                'border': '#E74C3C',
                'chunk': '#E74C3C'
            },
            ResultStatus.ERROR: {
                'text': '#dddddd',
                'background': '#1e1e1e',
                'border': '#F1C40F',
                'chunk': '#F1C40F'
            }
        }
        
        # Apply initial style
        self._apply_style(ResultStatus.PASS, 0)
    
    def _process_pending_update(self):
        """Process status and progress updates."""
        updates = self._pending_updates
        self._pending_updates = {}
        
        status = None
        progress = None
        
        if 'status' in updates:
            status_val = updates['status']
            if isinstance(status_val, str):
                try:
                    status = ResultStatus[status_val.upper()]
                except KeyError:
                    logger.error(f"Invalid status value: {status_val}")
                    return
            else:
                status = status_val
                
        if 'progress' in updates:
            try:
                progress = float(updates['progress'])
                progress = max(0, min(100, progress))  # Clamp to 0-100
            except (TypeError, ValueError) as e:
                logger.error(f"Invalid progress value: {updates['progress']}")
                return
        
        # Apply updates
        current_status = status or ResultStatus[self.status_label.text()]
        current_progress = progress if progress is not None else self.progress_bar.value()
        
        self._apply_style(current_status, current_progress)
    
    def _apply_style(self, status: ResultStatus, progress: float):
        """Apply status-specific styling with progress."""
        style = self.status_styles.get(status, self.status_styles[ResultStatus.ERROR])
        
        # Style progress bar
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
        
        # Style status label
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {style['text']};
                background: {style['background']};
                border: 1px solid {style['border']};
                border-radius: 2px;
                padding: 2px 8px;
                font-weight: 500;
            }}
        """)
        
        # Update values
        self.progress_bar.setValue(int(progress))
        if progress > 0:
            self.progress_bar.setFormat(f"{progress:.1f}%")
        else:
            self.progress_bar.setFormat("")
        self.status_label.setText(status.name)
    
    def contextMenuEvent(self, event):
        """Handle context menu."""
        try:
            menu = QMenu(self)
            current_status = ResultStatus[self.status_label.text()]
            
            # Progress presets submenu
            progress_menu = menu.addMenu("Set Progress")
            for value in [0, 25, 50, 75, 100]:
                action = progress_menu.addAction(f"{value}%")
                action.triggered.connect(lambda checked, v=value: self._handle_progress_change(v))
            
            menu.addSeparator()
            
            # Status options
            for status in ResultStatus:
                if status != current_status:
                    action = menu.addAction(f"Set {status.name}")
                    action.triggered.connect(lambda checked, s=status: self._handle_status_change(s))
            
            menu.exec_(event.globalPos())
        except Exception as e:
            logger.error(f"Error showing context menu: {e}")
    
    def _handle_status_change(self, status: ResultStatus):
        """Handle status change from context menu."""
        if hasattr(self.param, 'state') and hasattr(self.param, 'model_id'):
            model = self.param.state.get_model(self.param.model_id)
            if model:
                model.set_property('status', status.name)
    
    def _handle_progress_change(self, value: float):
        """Handle progress change from context menu."""
        if hasattr(self.param, 'state') and hasattr(self.param, 'model_id'):
            model = self.param.state.get_model(self.param.model_id)
            if model:
                model.set_property('progress', value)

class TestResultParameterItem(ModelParameterItem):
    """Parameter item for test results."""
    
    def makeWidget(self) -> Optional[QWidget]:
        """Create the status widget."""
        try:
            self.widget = ResultStatusWidget(self.param)
            return self.widget
        except Exception as e:
            logger.error(f"Error creating result widget: {e}")
            return None
    
    def updateWidget(self, **kwargs):
        """Update the widget with new values."""
        if self.widget:
            self.widget.queue_update(**kwargs)
    
    def addCustomContextActions(self, menu: QMenu):
        """Add result-specific context actions."""
        pass  # Status changes handled by widget context menu

class TestResultParameter(ModelParameter):
    """
    Parameter for test results. Shows status and contains child models
    (plots, tables, etc.) representing the actual test data.
    """
    
    itemClass = TestResultParameterItem
    
    def __init__(self, **opts):
        opts['type'] = 'testresult'
        super().__init__(**opts)
        self.can_export = True  # Results can be exported
        
        # Set up initial parameter structure
        model = self.state.get_model(self.model_id) if self.state and self.model_id else None
        self.setupParameters(model)
    
    def setupParameters(self, model: Optional[TestResult]):
        """Set up any child parameters needed."""
        # Currently no child parameters needed - results show their status
        # through the widget and contain data models as children in the tree
        pass
    
    def handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        if hasattr(self, 'widget'):
            self.widget.queue_update(**{prop: value})