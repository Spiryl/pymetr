import sys
import logging
from datetime import datetime, timedelta
from PySide6 import QtWidgets, QtCore
import pyqtgraph.parametertree as pt
from pyqtgraph.parametertree import Parameter, ParameterItem, registerParameterType

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

class TestStatusWidget(QtWidgets.QWidget):
    """Widget that displays test status and progress"""
    sigRunClicked = QtCore.Signal()
    sigStopClicked = QtCore.Signal()
    sigResetClicked = QtCore.Signal()
    
    STATUS_STYLES = {
        "Not Run": {
            "color": "#505050",
            "icon": "▶",
            "text": "Not Run"
        },
        "Running": {
            "color": "#4A90E2",
            "icon": "⏹",
            "text": "Running"
        },
        "Pass": {
            "color": "#2ECC71",
            "icon": "✓",
            "text": "Pass"
        },
        "Fail": {
            "color": "#E74C3C",
            "icon": "✗",
            "text": "Fail"
        },
        "Error": {
            "color": "#F1C40F",
            "icon": "⚠",
            "text": "Error"
        }
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.status = "Not Run"
        self.elapsed_time = None
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.setLayout(layout)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMaximumHeight(20)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        
        # Control button
        self.control_button = QtWidgets.QPushButton("▶")
        self.control_button.setFixedWidth(30)
        self.control_button.setMaximumHeight(20)
        self.control_button.clicked.connect(self.handle_button_click)

        # Time display
        self.time_label = QtWidgets.QLabel()
        self.time_label.setFixedWidth(70)
        self.time_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        
        layout.addWidget(self.progress_bar, 1)
        layout.addWidget(self.control_button)
        layout.addWidget(self.time_label)

    def set_time(self, seconds):
        """Update the elapsed time display"""
        if seconds is not None:
            elapsed = timedelta(seconds=seconds)
            hours = elapsed.seconds // 3600
            minutes = (elapsed.seconds % 3600) // 60
            seconds = elapsed.seconds % 60
            
            if hours > 0:
                time_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                time_str = f"{minutes:02d}:{seconds:02d}"
                
            self.time_label.setText(time_str)
            self.elapsed_time = elapsed
        else:
            self.time_label.clear()
            self.elapsed_time = None

    def handle_button_click(self):
        if self.status == "Running":
            self.sigStopClicked.emit()
        else:
            self.sigRunClicked.emit()

    def set_status(self, status: str, progress: int = None):
        logging.debug(f"Widget updating - Status: {status}, Progress: {progress}")
        self.status = status
        style = self.STATUS_STYLES.get(status, self.STATUS_STYLES["Not Run"])
        
        if progress is not None:
            self.progress_bar.setValue(progress)
            
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
        
        # Update control button
        self.control_button.setText(style['icon'])
        self.control_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {style['color']};
                color: white;
                border: none;
                border-radius: 2px;
                font-weight: bold;
            }}
        """)

        # Set tooltip with status info
        status_text = f"Status: {style['text']}"
        if self.elapsed_time:
            status_text += f"\nTime: {self.time_label.text()}"
        if progress is not None:
            status_text += f"\nProgress: {progress}%"
        self.setToolTip(status_text)

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)
        
        if self.status == "Running":
            stop_action = menu.addAction("Stop Test")
            stop_action.triggered.connect(self.sigStopClicked.emit)
        else:
            run_action = menu.addAction("Run Test")
            run_action.triggered.connect(self.sigRunClicked.emit)
            
        if self.status not in ["Not Run", "Running"]:
            menu.addSeparator()
            reset_action = menu.addAction("Reset Test")
            reset_action.triggered.connect(self.sigResetClicked.emit)
            
            menu.addSeparator()
            details_action = menu.addAction("Show Details...")
            # This could be connected to show test results, logs, etc.
        
        menu.exec_(event.globalPos())

class TestScriptParameterItem(ParameterItem):
    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.hideWidget = False
        self.widget = None

    def makeWidget(self):
        self.widget = TestStatusWidget()
        self.widget.sigRunClicked.connect(self.start_test)
        self.widget.sigStopClicked.connect(self.stop_test)
        self.widget.sigResetClicked.connect(self.reset_test)
        return self.widget

    def start_test(self):
        """Emit the run signal for external handling"""
        logging.info(f"Run clicked for: {self.param.name()}")
        self.param.sigRunClicked.emit(self.param)

    def stop_test(self):
        """Emit the stop signal for external handling"""
        logging.info(f"Stop clicked for: {self.param.name()}")
        self.param.sigStopClicked.emit(self.param)

    def reset_test(self):
        """Reset test to initial state"""
        logging.info(f"Reset clicked for: {self.param.name()}")
        self.param.sigResetClicked.emit(self.param)

    def valueChanged(self, param, val):
        """Handle progress updates"""
        if self.widget is not None:
            self.widget.set_status(
                self.param.opts.get('status', 'Not Run'), 
                val
            )

    def optsChanged(self, param, opts):
        """Handle status updates"""
        super().optsChanged(param, opts)
        if 'status' in opts and self.widget is not None:
            self.widget.set_status(opts['status'], self.param.value())
        if 'elapsed_time' in opts and self.widget is not None:
            self.widget.set_time(opts['elapsed_time'])

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

class TestRunnerParameter(Parameter):
    """Parameter that can receive run/stop signals and status updates"""
    itemClass = TestScriptParameterItem
    
    # Signals for external connections
    sigRunClicked = QtCore.Signal(object)  # Emits self
    sigStopClicked = QtCore.Signal(object)  # Emits self
    sigResetClicked = QtCore.Signal(object)  # Emits self
    
    def setStatus(self, status):
        """Convenience method to set status"""
        self.setOpts(status=status)

    def setElapsedTime(self, seconds):
        """Convenience method to set elapsed time"""
        self.setOpts(elapsed_time=seconds)

# Register the custom parameter type
registerParameterType("testrunner", TestRunnerParameter)

# ... (previous code remains the same until main()) ...

def main():
    """Demo showing how to use the parameter with external control"""
    app = QtWidgets.QApplication(sys.argv)
    tree = pt.ParameterTree()
    tree.setWindowTitle("Test Runner Example")
    tree.resize(600, 300)

    # Create test parameters
    params = [
        dict(name="Test 1", type="testrunner", value=0),
        dict(name="Test 2", type="testrunner", value=0),
        dict(name="Test 3", type="testrunner", value=0),
    ]

    p = Parameter.create(name="Test Explorer", type="group", children=params)
    tree.setParameters(p, showTop=False)

    # Track start times for running tests
    start_times = {}

    # Demo of how to connect to external signals
    for test in p.children():
        def on_run_clicked(param):
            logging.info(f"Starting {param.name()}")
            start_times[param.name()] = datetime.now()
            param.setOpts(status="Running", elapsed_time=0)
            test_timer.start(100)  # Make sure timer is running
            
        def on_stop_clicked(param):
            logging.info(f"Stopping {param.name()}")
            start_times.pop(param.name(), None)
            param.setOpts(status="Not Run", elapsed_time=None)
            param.setValue(0)

        def on_reset_clicked(param):
            logging.info(f"Resetting {param.name()}")
            start_times.pop(param.name(), None)
            param.setOpts(status="Not Run", elapsed_time=None)
            param.setValue(0)
            
        test.sigRunClicked.connect(on_run_clicked)
        test.sigStopClicked.connect(on_stop_clicked)
        test.sigResetClicked.connect(on_reset_clicked)

    # Simple simulation to show progress updates
    test_timer = QtCore.QTimer()
    def update_running_tests():
        running_tests = False
        for test in p.children():
            if test.opts.get('status') == 'Running':
                running_tests = True
                # Update elapsed time
                if test.name() in start_times:
                    elapsed = (datetime.now() - start_times[test.name()]).total_seconds()
                    test.setElapsedTime(int(elapsed))
                
                # Update progress
                current = test.value()
                if current < 100:
                    test.setValue(current + 2)
                else:
                    test.setOpts(status="Pass")
                    start_times.pop(test.name(), None)  # Clear start time
                    logging.info(f"Test {test.name()} completed")
        
        # Only stop timer if no tests are running
        if not running_tests:
            test_timer.stop()
            logging.debug("All tests complete, stopping timer")
    
    test_timer.timeout.connect(update_running_tests)

    tree.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()