from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QMenu
)
from PySide6.QtGui import QIcon

from .base import ModelParameter, ModelParameterItem
from pymetr.core.logging import logger

class TestStatus:
    """Constants and styling for test result status."""
    NOT_RUN = "Not Run"
    RUNNING = "Running"
    PASS = "Pass"
    FAIL = "Fail"
    ERROR = "Error"
    
    STYLES = {
        NOT_RUN: {
            "color": "#95A5A6",
            "background": "#95A5A622",
            "border": "#95A5A6"
        },
        RUNNING: {
            "color": "#3498DB",
            "background": "#3498DB22",
            "border": "#3498DB"
        },
        PASS: {
            "color": "#2ECC71",
            "background": "#2ECC7122",
            "border": "#2ECC71"
        },
        FAIL: {
            "color": "#E74C3C",
            "background": "#E74C3C22",
            "border": "#E74C3C"
        },
        ERROR: {
            "color": "#F1C40F",
            "background": "#F1C40F22",
            "border": "#F1C40F"
        }
    }

class TestStatusWidget(QWidget):
    """Widget displaying test result status and info."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._status = TestStatus.NOT_RUN
        
    def setup_ui(self):
        """Initialize the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Status label with styling
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                border-radius: 2px;
                font-weight: 500;
            }
        """)
        layout.addWidget(self.status_label)
        
        
    def update_status(self, status: str):
        """Update the status display with appropriate styling."""
        self._status = status
        style = TestStatus.STYLES.get(status, TestStatus.STYLES[TestStatus.NOT_RUN])
        
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {style['color']};
                background: {style['background']};
                border: 1px solid {style['border']};
                padding: 2px 8px;
                border-radius: 2px;
                font-weight: 500;
            }}
        """)
        self.status_label.setText(status)
        
    def update_summary(self, passed: int, total: int):
        """Update the measurements summary."""
        if total > 0:
            self.summary_label.setText(f"{passed}/{total} passed")
            self.summary_label.setVisible(True)
        else:
            self.summary_label.setVisible(False)

class TestResultParameterItem(ModelParameterItem):
    """Parameter item for test results in tree."""
    
    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.hideWidget = False
        self.widget = None
        
    def makeWidget(self):
        """Create the status widget."""
        logger.debug("TestResultParameterItem: Making widget")
        self.widget = TestStatusWidget()
        return self.widget
        
    def valueChanged(self, param, val):
        """Handle value updates."""
        if self.widget is not None:
            self.widget.update_status(param.status(), val)
            
    def optsChanged(self, param, opts):
        """Handle status updates."""
        super().optsChanged(param, opts)
        if 'status' in opts and self.widget is not None:
            self.widget.update_status(opts['status'], param.value())
            
    def treeWidgetChanged(self):
        """Called when this item is added or removed from a tree."""
        super().treeWidgetChanged()
        logger.debug("TestResultParameterItem: Tree widget changed")
        
        if self.widget is None:
            self.widget = self.makeWidget()
            
        tree = self.treeWidget()
        if tree is not None:
            logger.debug("TestResultParameterItem: Setting widget in column 1")
            tree.setItemWidget(self, 1, self.widget)
            
    def add_context_menu_actions(self, menu):
        """Add test result specific menu actions"""
        if self.widget:
            if self.widget._status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR]:
                export_action = menu.addAction(QIcon(":/icons/material/download.svg"), "Export Results")
                export_action.triggered.connect(self._handle_export)

class TestResultParameter(ModelParameter):
    """Parameter for test result display."""
    itemClass = TestResultParameterItem
    
    def __init__(self, **opts):
        opts['type'] = 'testresult'
        opts.setdefault('status', TestStatus.NOT_RUN)
        super().__init__(**opts)
        self._status = opts['status']
        self._progress = 0
        
    def status(self) -> str:
        """Get current status."""
        if self.state and self.model_id:
            model = self.state.get_model(self.model_id)
            if model:
                self._status = model.get_property('status', TestStatus.NOT_RUN)
        return self._status
        
    def value(self):
        """Get current progress value."""
        return self._progress
        
    def setValue(self, value):
        """Update progress value."""
        self._progress = value
        self.sigValueChanged.emit(self, value)
        
    def setStatus(self, status: str):
        """Update test status."""
        self._status = status
        self.setOpts(status=status)

    def add_context_actions(self, menu: QMenu) -> None:
        """Add parameter-specific menu actions."""
        pass