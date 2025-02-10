from PySide6.QtWidgets import (
    QWidget, QProgressBar, QPushButton, QLabel, QHBoxLayout,
    QMenu
)
from PySide6.QtCore import Signal, Qt, Slot
from pyqtgraph.parametertree import Parameter, ParameterItem, registerParameterType
from datetime import datetime, timedelta

from .base import ModelParameter, ModelParameterItem
from pymetr.core.logging import logger

# Import the global state accessor.
from pymetr.core.state import get_global_state

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
            "color": "#505050",
            "status_icon": "☢️",
            "action_icon": "▶️",
            "text": "Not Run"
        },
        RUNNING: {
            "color": "#4A90E2",
            "status_icon": "🔄",
            "action_icon": "⏹️",
            "text": "Running"
        },
        PASS: {
            "color": "#2ECC71",
            "status_icon": "✅",
            "action_icon": "🔄",
            "text": "Pass"
        },
        FAIL: {
            "color": "#E74C3C",
            "status_icon": "❌",
            "action_icon": "🔄",
            "text": "Fail"
        },
        ERROR: {
            "color": "#F1C40F",
            "status_icon": "⚠️",
            "action_icon": "🔄",
            "text": "Error"
        },
        COMPLETE: {
            "color": "#2ECC71",
            "status_icon": "✅",
            "action_icon": "🔄",
            "text": "Complete"
        }
    }

class TestStatusWidget(QWidget):
    """Widget showing test status, progress, and controls."""
    
    # Signals
    run_clicked = Signal()
    stop_clicked = Signal()
    rerun_clicked = Signal()
    reset_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status = TestStatus.NOT_RUN
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.setLayout(layout)
        
        # Status icon
        self.status_label = QLabel()
        self.status_label.setFixedWidth(25)
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(13)
        self.progress_bar.setRange(0, 100)
        
        # Control button
        self.control_button = QPushButton()
        self.control_button.setFixedWidth(30)
        self.control_button.setMaximumHeight(24)
        self.control_button.clicked.connect(self._handle_button_click)
        
        # Time display
        self.time_label = QLabel()
        self.time_label.setFixedWidth(40)
        self.time_label.setAlignment(Qt.AlignRight)
        
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar, 1)
        layout.addWidget(self.control_button)
        layout.addWidget(self.time_label)
        
    def update_elapsed_time(self, seconds: int):
        """Update elapsed time display."""
        if seconds is not None:
            elapsed = timedelta(seconds=seconds)
            hours = elapsed.seconds // 3600
            minutes = (elapsed.seconds % 3600) // 60
            secs = elapsed.seconds % 60
            
            if hours > 0:
                time_str = f"{hours}:{minutes:02d}:{secs:02d}"
            else:
                time_str = f"{minutes:02d}:{secs:02d}"
            
            self.time_label.setText(time_str)
        else:
            self.time_label.clear()
            
    def update_status(self, status: str, progress: float = None):
        """Update display status and progress."""
        self.status = status
        style = TestStatus.STYLES.get(status, TestStatus.STYLES[TestStatus.NOT_RUN])
        
        if progress is not None:
            self.progress_bar.setValue(int(progress))
            
        # Update components
        self.status_label.setText(style['status_icon'])
        self.control_button.setText(style['action_icon'])
        
        # Update progress bar style
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {style['color']};
                border-radius: 2px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {style['color']};
            }}
        """)
        
        # Update tooltip
        tooltip = f"Status: {style['text']}"
        if progress is not None:
            tooltip += f"\nProgress: {progress}%"
        self.setToolTip(tooltip)
        
    def _handle_button_click(self):
        """Handle control button clicks."""
        if self.status == TestStatus.RUNNING:
            self.stop_clicked.emit()
        elif self.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR, TestStatus.COMPLETE]:
            self.rerun_clicked.emit()
        else:
            self.run_clicked.emit()
            
    def contextMenuEvent(self, event):
        """Show context menu."""
        menu = QMenu(self)
        style = TestStatus.STYLES.get(self.status, TestStatus.STYLES[TestStatus.NOT_RUN])
        
        if self.status == TestStatus.RUNNING:
            stop_action = menu.addAction(f"{style['action_icon']} Stop Test")
            stop_action.triggered.connect(self.stop_clicked.emit)
        else:
            if self.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR, TestStatus.COMPLETE]:
                rerun_action = menu.addAction(f"{style['action_icon']} Rerun Test")
                rerun_action.triggered.connect(self.rerun_clicked.emit)
                
                menu.addSeparator()
                reset_action = menu.addAction("Reset Status")
                reset_action.triggered.connect(self.reset_clicked.emit)
            else:
                run_action = menu.addAction(f"{style['action_icon']} Run Test")
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
        self.widget.rerun_clicked.connect(self._handle_rerun)
        self.widget.reset_clicked.connect(self._handle_reset)
        return self.widget

    def add_context_menu_actions(self, menu):
        """Add test script specific actions"""
        menu.addSeparator()
        
        run_action = menu.addAction("Run")
        run_action.triggered.connect(self._handle_run)
        
        stop_action = menu.addAction("Stop")
        stop_action.triggered.connect(self._handle_stop)
        
        reset_action = menu.addAction("Reset")
        reset_action.triggered.connect(self._handle_reset)

    def _handle_run(self):
        """Start test execution using the specific script model ID."""
        try:
            # Get state from the parameter
            state = self.param.state
            if state is None:
                logger.error(f"TestScriptParameterItem: No state found on the parameter. Param type: {type(self.param)}")
                return
            
            script_id = self.param.model_id
            if not script_id:
                logger.error(f"TestScriptParameterItem: No model ID found on the parameter. Param type: {type(self.param)}")
                return
            
            logger.debug(f"TestScriptParameterItem: Running script with id {script_id}")
            state.engine.run_test_script(script_id)
        except Exception as e:
            logger.error(f"TestScriptParameterItem: Error running script: {e}", exc_info=True)
            
    def _handle_stop(self):
        """Stop test execution."""
        try:
            state = self.param.state
            if state is None:
                logger.error("TestScriptParameterItem: No state found on the parameter.")
                return
                
            engine = state.engine
            if engine and engine.script_runner is not None:
                logger.debug("TestScriptParameterItem: Stopping script")
                engine.script_runner.stop()
                script = state.get_model(self.param.model_id)
                if script:
                    script.status = TestStatus.NOT_RUN
        except Exception as e:
            logger.error(f"TestScriptParameterItem: Error stopping script: {e}", exc_info=True)

    def _handle_rerun(self):
        """Restart test execution."""
        self._handle_run()
        
    def _handle_reset(self):
        """Reset test status."""
        try:
            state = self.param.state if hasattr(self.param, 'state') and self.param.state is not None else get_global_state()
            script = state.get_model(self.param.model_id)
            if script:
                script.status = TestStatus.NOT_RUN
                script.set_property('progress', 0)
        except Exception as e:
            logger.error(f"TestScriptParameterItem: Error resetting script status: {e}", exc_info=True)
            
    def valueChanged(self, param, val):
        """Handle progress updates."""
        if self.widget is not None:
            self.widget.update_status(param.getStatus(), val)
            
    def optsChanged(self, param, opts):
        """Handle status and time updates."""
        super().optsChanged(param, opts)
        if 'status' in opts and self.widget is not None:
            self.widget.update_status(opts['status'], self.param.value())
        if 'elapsed_time' in opts and self.widget is not None:
            self.widget.update_elapsed_time(opts['elapsed_time'])
            
    def treeWidgetChanged(self):
        """Called when this item is added or removed from a tree."""
        super().treeWidgetChanged()
        
        if self.widget is None:
            self.widget = self.makeWidget()
            
        tree = self.treeWidget()
        if tree is not None:
            tree.setItemWidget(self, 1, self.widget)
            
        if self.param.hasValue():
            self.valueChanged(self.param, self.param.value())

class TestScriptParameter(ModelParameter):
    """Parameter for test script control."""
    itemClass = TestScriptParameterItem
    
    def __init__(self, **opts):
        # Set default type
        opts['type'] = 'testscript'
        opts.setdefault('status', TestStatus.NOT_RUN)
        
        # Initialize parent with all options including state
        super().__init__(**opts)
        
        # Store status after parent init
        self.status = opts['status']
        
        if not self.state:
            logger.error("TestScriptParameter: No state provided")
    
    def setStatus(self, status: str):
        """Update test status."""
        self.status = status
        self.setOpts(status=status)
        
    def getStatus(self) -> str:
        """Get current status."""
        return self.status

