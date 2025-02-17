from PySide6.QtWidgets import (
    QWidget, QProgressBar, QLabel, QHBoxLayout, QMenu
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon

from .base import ModelParameter, ModelParameterItem
from pymetr.core.logging import logger

class TestStatus:
    """Constants and styling for test status."""
    NOT_RUN = "Not Run"
    RUNNING = "Running"
    PASS = "Pass"
    FAIL = "Fail"
    ERROR = "Error"
    COMPLETE = "Complete"
    
    STYLES = {
        NOT_RUN: {
            "color": "#aaaaaa",
            "background": "#1e1e1e",
            "border": "#95A5A6"
        },
        RUNNING: {
            "color": "#aaaaaa",
            "background": "#1e1e1e",
            "chunk": "#3498DB",
            "border": "#3498DB"
        },
        PASS: {
            "color": "#aaaaaa",
            "background": "#1e1e1e",
            "chunk": "#1e1e1e",
            "border": "#2ECC71"
        },
        FAIL: {
            "color": "#aaaaaa",
            "background": "#1e1e1e",
            "chunk": "#1e1e1e",
            "border": "#E74C3C"
        },
        ERROR: {
            "color": "#aaaaaa",
            "background": "#1e1e1e",
            "chunk": "#1e1e1e",
            "border": "F1C40F"
        },
        COMPLETE: {
            "color": "#aaaaaa",
            "background": "#1e1e1e",
            "chunk": "#1e1e1e",
            "border": "#2ECC71"
        }
    }

class TestStatusWidget(QWidget):
    """Widget showing test status OR progress."""
    
    # Signals for actions
    run_clicked = Signal()
    stop_clicked = Signal()
    reset_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = TestStatus.NOT_RUN
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.setLayout(layout)
        
        # Just the progress bar - no status label
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(18)  # Made slightly taller for better text visibility
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar, 1)
            
    def update_status(self, status: str, progress: float = None):
        """Update display with either progress or status."""
        self._status = status
        style = TestStatus.STYLES.get(status, TestStatus.STYLES[TestStatus.NOT_RUN])
        
        if status == TestStatus.RUNNING:
            # Show progress percentage during run
            if progress is not None:
                self.progress_bar.setValue(int(progress))
                self.progress_bar.setFormat(f"{progress:.1f}%")
        else:
            # For non-running states, set value to 0 or 100 based on completion
            value = 100 if status in [TestStatus.PASS, TestStatus.COMPLETE] else 0
            self.progress_bar.setValue(value)
            
            # Just show the status text
            self.progress_bar.setFormat(status)
        
        # Update progress bar style
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
        
        # Always show the text
        self.progress_bar.setTextVisible(True)
        
    def contextMenuEvent(self, event):
        """Show context menu."""
        menu = QMenu(self)
        
        if self._status == TestStatus.RUNNING:
            stop_action = menu.addAction("Stop Test")
            stop_action.triggered.connect(self.stop_clicked.emit)
        elif self._status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR, TestStatus.COMPLETE]:
            run_action = menu.addAction("Run Test")
            run_action.triggered.connect(self.run_clicked.emit)
            
            menu.addSeparator()
            reset_action = menu.addAction("Reset Status")
            reset_action.triggered.connect(self.reset_clicked.emit)
        else:
            run_action = menu.addAction("Run Test")
            run_action.triggered.connect(self.run_clicked.emit)
        
        menu.exec_(event.globalPos())

class TestScriptParameterItem(ModelParameterItem):
    """Parameter item for test script in tree."""
    
    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.hideWidget = False
        self.widget = None
        
    def makeWidget(self):
        """Create the status widget."""
        self.widget = TestStatusWidget()
        self.widget.run_clicked.connect(self._handle_run)
        self.widget.stop_clicked.connect(self._handle_stop)
        self.widget.reset_clicked.connect(self._handle_reset)
        return self.widget
        
    def valueChanged(self, param, val):
        """Handle progress updates."""
        if self.widget is not None:
            self.widget.update_status(param.status(), val)
            
    def optsChanged(self, param, opts):
        """Handle status and time updates."""
        super().optsChanged(param, opts)
        if 'status' in opts and self.widget is not None:
            self.widget.update_status(opts['status'], param.value())
            
    def treeWidgetChanged(self):
        """Called when this item is added or removed from a tree."""
        super().treeWidgetChanged()
        if self.widget is None:
            self.widget = self.makeWidget()
        tree = self.treeWidget()
        if tree is not None:
            tree.setItemWidget(self, 1, self.widget)
            
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
                    script.status = TestStatus.NOT_RUN
                    script.set_property('progress', 0)
        except Exception as e:
            logger.error(f"Error resetting script: {e}")

    def add_context_menu_actions(self, menu):
        """Add test script specific menu actions"""
        if self.widget:  # Our TestStatusWidget
            if self.widget._status == TestStatus.RUNNING:
                stop_action = menu.addAction("Stop Test")
                stop_action.triggered.connect(self.widget.stop_clicked.emit)
            else:
                run_action = menu.addAction("Run Test")
                run_action.triggered.connect(self.widget.run_clicked.emit)
                
                if self.widget._status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR, TestStatus.COMPLETE]:
                    menu.addSeparator()
                    reset_action = menu.addAction("Reset Status")
                    reset_action.triggered.connect(self.widget.reset_clicked.emit)

class TestScriptParameter(ModelParameter):
    """Parameter for test script control."""
    itemClass = TestScriptParameterItem
    
    def __init__(self, **opts):
        opts['type'] = 'testscript'
        opts.setdefault('status', TestStatus.NOT_RUN)
        super().__init__(**opts)
        self._status = opts['status']
        self._progress = 0
        
    def status(self) -> str:
        """Get current status."""
        # Make sure we're getting the current model status
        if self.state and self.model_id:
            model = self.state.get_model(self.model_id)
            if model:
                self._status = model.get_property('status', TestStatus.NOT_RUN)
        return self._status
        
    def value(self):
        """Get current progress value."""
        # Make sure we're getting the current model progress
        if self.state and self.model_id:
            model = self.state.get_model(self.model_id)
            if model:
                self._progress = model.get_property('progress', 0)
        return self._progress
        
    def setValue(self, value):
        """Override setValue to handle integer values."""
        if isinstance(value, (int, float)):
            value = float(value)  # Convert to float to avoid weak reference issues
        super().setValue(value)
        
    def setStatus(self, status: str):
        """Update test status."""
        self._status = status
        self.setOpts(status=status)

    def add_context_actions(self, menu: QMenu) -> None:
        """Add parameter-specific menu actions."""
        # We can add any parameter-level actions here if needed
        pass