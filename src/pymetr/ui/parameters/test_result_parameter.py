from typing import Optional, Any
from PySide6.QtWidgets import QWidget, QHBoxLayout, QMenu, QProgressBar
from PySide6.QtCore import Qt, QTimer
from pymetr.core.logging import logger
from pymetr.models import TestResult, ResultStatus
from .base import ModelParameter, ModelParameterItem, ParameterWidget

class ResultStatusWidget(ParameterWidget):
    """
    A widget that displays the test result's status and progress in a single QProgressBar.
    Debug logging is added to trace the update chain, and for testing the QTimer, we force
    an immediate update call.
    """
    def __init__(self, param, parent=None):
        super().__init__(param, parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(18)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Define styles for statuses
        self.status_styles = {
            ResultStatus.PASS: {'border': '#4BFF36', 'chunk': '#1e1e1e', 'background': '#1e1e1e'},
            ResultStatus.FAIL: {'border': '#E74C3C', 'chunk': '#1e1e1e', 'background': '#1e1e1e'},
            ResultStatus.ERROR: {'border': '#F23CA6', 'chunk': '#1e1e1e', 'background': '#1e1e1e'},
            None:             {'border': '#5E57FF', 'chunk': '#5E57FF', 'background': '#1e1e1e'}  # Blue for not reported
        }
        
        # Set initial style (none reported)
        self._apply_style(None, 0)
    
    def queue_update(self, **kwargs):
        # Add our debug log here
        # logger.debug(f"ResultStatusWidget.queue_update called with: {kwargs}")
        super().queue_update(**kwargs)
        # For debugging: force an immediate processing call.
        # Remove or comment this line once you confirm the update chain works.
        self._process_pending_update()
    
    def _process_pending_update(self):
        # logger.debug(f"ResultStatusWidget._process_pending_update: {self._pending_updates}")
        self._pending_updates.clear()
        
        # Read current values from the model
        status_val = self.param.get_model_property("status", None)
        progress_val = self.param.get_model_property("progress", 0)
        
        if status_val is None or str(status_val).strip() == "":
            status = None
        else:
            try:
                status = ResultStatus[status_val.upper()]
            except KeyError:
                logger.error(f"Invalid status from model: {status_val}")
                status = None

        try:
            progress = float(progress_val)
            progress = max(0, min(100, progress))
        except Exception as e:
            logger.error(f"Invalid progress value: {progress_val} - {e}")
            progress = 0
        
        # logger.debug(f"Updating widget: status={status if status else 'None'}, progress={progress}")
        self._apply_style(status, progress)
    
    def _apply_style(self, status: Optional[ResultStatus], progress: float):
        # If status is None, show "Not Reported" with blue style.
        if status is None:
            style = self.status_styles[None]
            text = "Not Reported"
        else:
            style = self.status_styles.get(status, self.status_styles[ResultStatus.ERROR])
            text = f"{status.name}" if progress == 0 else f"{status.name} ({progress:.1f}%)"
        
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
        self.progress_bar.setFormat(text)
    
    def contextMenuEvent(self, event):
        try:
            menu = QMenu(self)
            try:
                current_status = ResultStatus[self.param.get_model_property("status", "PASS").upper()]
            except Exception:
                current_status = ResultStatus.PASS
            
            progress_menu = menu.addMenu("Set Progress")
            for value in [0, 25, 50, 75, 100]:
                action = progress_menu.addAction(f"{value}%")
                action.triggered.connect(lambda checked, v=value: self._handle_progress_change(v))
            
            menu.addSeparator()
            for status in ResultStatus:
                if status != current_status:
                    action = menu.addAction(f"Set {status.name}")
                    action.triggered.connect(lambda checked, s=status: self._handle_status_change(s))
            
            menu.exec_(event.globalPos())
        except Exception as e:
            logger.error(f"ResultStatusWidget: Error showing context menu: {e}")
    
    def _handle_status_change(self, status: ResultStatus):
        if hasattr(self.param, 'state') and hasattr(self.param, 'model_id'):
            model = self.param.state.get_model(self.param.model_id)
            if model:
                logger.debug(f"ResultStatusWidget: Changing status to {status.name}")
                model.set_property('status', status.name)
    
    def _handle_progress_change(self, value: float):
        if hasattr(self.param, 'state') and hasattr(self.param, 'model_id'):
            model = self.param.state.get_model(self.param.model_id)
            if model:
                logger.debug(f"ResultStatusWidget: Changing progress to {value}")
                model.set_property('progress', value)

class TestResultParameterItem(ModelParameterItem):
    def makeWidget(self) -> Optional[QWidget]:
        try:
            self.widget = ResultStatusWidget(self.param)
            return self.widget
        except Exception as e:
            logger.error(f"TestResultParameterItem: Error creating widget: {e}")
            return None
    
    def updateWidget(self, **kwargs):
        if self.widget:
            logger.debug(f"TestResultParameterItem.updateWidget called with: {kwargs}")
            self.widget.queue_update(**kwargs)
    
    def addCustomContextActions(self, menu: QMenu):
        pass  # Context menu is handled in the widget

class TestResultParameter(ModelParameter):
    itemClass = TestResultParameterItem
    
    def __init__(self, **opts):
        opts['type'] = 'testresult'
        super().__init__(**opts)
        self.can_export = True
        model = self.state.get_model(self.model_id) if self.state and self.model_id else None
        self.setupParameters(model)
    
    def setupParameters(self, model: Optional[TestResult]):
        # No child parameters needed.
        pass
    
    def handle_property_update(self, prop: str, value: Any):
        # logger.debug(f"TestResultParameter: handle_property_update prop: {prop}, value: {value}, widget: {getattr(self, 'widget', None)}")
        # If the widget isn't attached directly to self, try the one on self.param
        widget = getattr(self, 'widget', None) or getattr(self, 'widget', None)
        if widget is not None:
            widget.queue_update(**{prop: value})
        else:
            logger.warning("TestResultParameter: widget is not set for parameter " + self.title())
