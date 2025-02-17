from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QMenu
from PySide6.QtGui import QIcon
from .base import ModelParameter, ModelParameterItem
from pymetr.core.logging import logger

class ResultStatus:
    """Status constants for test results."""
    NOT_REPORTED = "Not Reported"
    PASS = "Pass"
    FAIL = "Fail"
    ERROR = "Error"
    
    STYLES = {
        NOT_REPORTED: {
            "color": "#dddddd",
            "background": "#1e1e1e",
            "border": "#95A5A6"
        },
        PASS: {
            "color": "#dddddd",
            "background": "#1e1e1e",
            "border": "#2ECC71"
        },
        FAIL: {
            "color": "#dddddd",
            "background": "#1e1e1e",
            "border": "#E74C3C"
        },
        ERROR: {
            "color": "#dddddd",
            "background": "#1e1e1e",
            "border": "#F1C40F"
        }
    }

class TestResultStatusWidget(QWidget):
    """Widget displaying test result status."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = ResultStatus.NOT_REPORTED
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                border-radius: 2px;
                font-weight: 500;
                text-align: center;
            }
        """)
        layout.addWidget(self.status_label)
        
        self.update_status(self._status)
        
    def update_status(self, status: str):
        """Update the status display with appropriate styling."""
        try:
            # First check if our label still exists
            if not hasattr(self, 'status_label') or not self.status_label:
                return
                
            # Store the status even if we can't display it
            self._status = status
            style = ResultStatus.STYLES.get(status, ResultStatus.STYLES[ResultStatus.NOT_REPORTED])
            
            try:
                # Attempt to update the label - this will fail if widget is destroyed
                self.status_label.setStyleSheet(f"""
                    QLabel {{
                        color: {style['color']};
                        background: {style['background']};
                        border: 1px solid {style['border']};
                        padding: 2px 8px;
                        border-radius: 2px;
                        text-align: center;
                        font-weight: 500;
                    }}
                """)
                self.status_label.setText(status)
            except RuntimeError:
                # Widget was destroyed, we'll just ignore it
                pass
                
        except Exception as e:
            logger.error(f"Error updating status widget: {e}")

class TestResultParameterItem(ModelParameterItem):
    """Parameter item for test results in tree."""
    
    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.hideWidget = False
        self.widget = None
        
    def makeWidget(self):
        """Create the status widget."""
        self.widget = TestResultStatusWidget()
        return self.widget
        
    def valueChanged(self, param, val):
        """Handle value updates."""
        if hasattr(self, 'widget') and self.widget:
            self.widget.update_status(param.status())
            
    def optsChanged(self, param, opts):
        """Handle status updates."""
        super().optsChanged(param, opts)
        if 'status' in opts and hasattr(self, 'widget') and self.widget:
            self.widget.update_status(opts['status'])
            
    def treeWidgetChanged(self):
        """Called when this item is added or removed from a tree."""
        super().treeWidgetChanged()
        
        if not hasattr(self, 'widget') or not self.widget:
            self.widget = self.makeWidget()
            
        tree = self.treeWidget()
        if tree is not None:
            tree.setItemWidget(self, 1, self.widget)

    def cleanup(self):
        """Clean up widget resources."""
        try:
            if hasattr(self, 'widget') and self.widget:
                self.widget.deleteLater()
                self.widget = None
        except Exception as e:
            logger.error(f"Error cleaning up TestResultParameterItem: {e}")

class TestResultParameter(ModelParameter):
    """Parameter for test result display."""
    itemClass = TestResultParameterItem
    
    def __init__(self, **opts):
        opts['type'] = 'testresult'
        opts.setdefault('status', ResultStatus.NOT_REPORTED)
        
        # Ensure model_id is stored in the parameter name
        if 'model_id' in opts:
            opts['name'] = opts['model_id']
            
        super().__init__(**opts)
        self._status = opts['status']
        
    def status(self) -> str:
        """Get current status."""
        if self.state and hasattr(self, 'model_id'):
            model = self.state.get_model(self.model_id)
            if model:
                self._status = model.get_property('status', ResultStatus.NOT_REPORTED)
        return self._status
        
    def setStatus(self, status: str):
        """Update test status."""
        if status not in ResultStatus.STYLES:
            logger.warning(f"Invalid status '{status}' - must be one of: {', '.join(ResultStatus.STYLES.keys())}")
            return
            
        self._status = status
        self.setOpts(status=status)

    def add_context_actions(self, menu: QMenu) -> None:
        """Add parameter-specific menu actions."""
        pass