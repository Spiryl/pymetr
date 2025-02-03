import logging
from datetime import datetime, timedelta
from PySide6 import QtWidgets, QtCore
from pyqtgraph.parametertree import Parameter, ParameterItem, registerParameterType

class TestStatus:
    """Constants for test status"""
    NOT_RUN = "Not Run"
    RUNNING = "Running"
    PASS = "Pass"
    FAIL = "Fail"
    ERROR = "Error"
    
    # Styling for each status
    STYLES = {
        NOT_RUN: {
            "color": "#505050",
            "status_icon": "☢️",  # Keep unicode for status
            "action_icon": "▶️",
            "text": "Not Run"
        },
        RUNNING: {
            "color": "#4A90E2",
            "status_icon": "🚬",  # Keep unicode for status
            "action_icon": "⏹️",
            "text": "Running"
        },
        PASS: {
            "color": "#2ECC71",
            "status_icon": "✅",  # Keep unicode for status
            "action_icon": "🔃",
            "text": "Pass"
        },
        FAIL: {
            "color": "#E74C3C",
            "status_icon": "❌",  # Keep unicode for status
            "action_icon": "🔃",
            "text": "Fail"
        },
        ERROR: {
            "color": "#F1C40F",
            "status_icon": "⚠️",  # Keep unicode for status
            "action_icon": "🔃",
            "text": "Error"
        }
    }

class TestStatusWidget(QtWidgets.QWidget):
    """Widget that displays test status, progress, and elapsed time"""
    sigRunClicked = QtCore.Signal()
    sigStopClicked = QtCore.Signal()
    sigRerunClicked = QtCore.Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status = TestStatus.NOT_RUN
        self.elapsed_time = None
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.setLayout(layout)

        # Status icon label
        self.status_label = QtWidgets.QLabel()
        self.status_label.setFixedWidth(25)
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMaximumHeight(13)  # Reduced height
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setContentsMargins(0, 2, 0, 2)  # Add some vertical padding
        
        # Control button
        self.control_button = QtWidgets.QPushButton()
        self.control_button.setFixedWidth(30)
        self.control_button.setMaximumHeight(24)  # Match progress bar height
        self.control_button.clicked.connect(self.handle_button_click)

        # Time display
        self.time_label = QtWidgets.QLabel()
        self.time_label.setFixedWidth(70)
        self.time_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        
        layout.addWidget(self.status_label)
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
        if self.status == TestStatus.RUNNING:
            self.sigStopClicked.emit()
        elif self.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR]:
            self.sigRerunClicked.emit()
        else:
            self.sigRunClicked.emit()

    def set_status(self, status: str, progress: int = None):
        """Update the display status and progress"""
        self.status = status
        style = TestStatus.STYLES.get(status, TestStatus.STYLES[TestStatus.NOT_RUN])
        
        if progress is not None:
            self.progress_bar.setValue(progress)
            
        # Update status icon
        self.status_label.setText(style['status_icon'])
        
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
        
        # Update control button - using default button style, just setting the icon
        self.control_button.setText(style['action_icon'])

        # Set tooltip with status info
        status_text = f"Status: {style['text']}"
        if self.elapsed_time:
            status_text += f"\nTime: {self.time_label.text()}"
        if progress is not None:
            status_text += f"\nProgress: {progress}%"
        self.setToolTip(status_text)

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)
        style = TestStatus.STYLES.get(self.status, TestStatus.STYLES[TestStatus.NOT_RUN])
        
        if self.status == TestStatus.RUNNING:
            stop_action = menu.addAction(f"{style['action_icon']} Stop Test")
            stop_action.triggered.connect(self.sigStopClicked.emit)
        else:
            if self.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR]:
                rerun_action = menu.addAction(f"{style['action_icon']} Rerun Test")
                rerun_action.triggered.connect(self.sigRerunClicked.emit)
                
                menu.addSeparator()
                reset_action = menu.addAction("Reset Status")
                reset_action.triggered.connect(lambda: self.set_status(TestStatus.NOT_RUN, 0))
            else:
                run_action = menu.addAction(f"{style['action_icon']} Run Test")
                run_action.triggered.connect(self.sigRunClicked.emit)
            
            # View results option for completed tests
            if self.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR]:
                menu.addSeparator()
                menu.addAction("View Results...")  # Placeholder for result viewer
        
        menu.exec_(event.globalPos())

class TestRunnerParameterItem(ParameterItem):
    """ParameterItem for displaying test status in tree"""
    
    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.hideWidget = False
        self.widget = None

    def makeWidget(self):
        self.widget = TestStatusWidget()
        self.widget.sigRunClicked.connect(self.start_test)
        self.widget.sigStopClicked.connect(self.stop_test)
        self.widget.sigRerunClicked.connect(self.rerun_test)
        return self.widget

    def start_test(self):
        """Emit the run signal for external handling"""
        self.param.sigRunClicked.emit(self.param)

    def stop_test(self):
        """Emit the stop signal for external handling"""
        self.param.sigStopClicked.emit(self.param)

    def rerun_test(self):
        """Emit the rerun signal for external handling"""
        self.param.sigRerunClicked.emit(self.param)

    def valueChanged(self, param, val):
        """Handle progress updates"""
        if self.widget is not None:
            self.widget.set_status(
                param.opts.get('status', TestStatus.NOT_RUN), 
                val
            )

    def optsChanged(self, param, opts):
        """Handle status and time updates"""
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
    """Parameter for test script status display and control"""
    itemClass = TestRunnerParameterItem
    
    # Signals for external connections
    sigRunClicked = QtCore.Signal(object)    # Emits self when run requested
    sigStopClicked = QtCore.Signal(object)   # Emits self when stop requested
    sigRerunClicked = QtCore.Signal(object)  # Emits self when rerun requested
    
    def setStatus(self, status):
        """Set the test status"""
        self.setOpts(status=status)

    def getStatus(self):
        """Get the current test status"""
        return self.opts.get('status', TestStatus.NOT_RUN)

    def setElapsedTime(self, seconds):
        """Set the elapsed test time in seconds"""
        self.setOpts(elapsed_time=seconds)

    def getElapsedTime(self):
        """Get the current elapsed time in seconds"""
        return self.opts.get('elapsed_time', None)

    def reset(self):
        """Reset the test to initial state"""
        self.setValue(0)
        self.setOpts(status=TestStatus.NOT_RUN, elapsed_time=None)

# Register the custom parameter type
registerParameterType("testrunner", TestRunnerParameter)


if __name__ == "__main__":
    """Test harness for parameter development"""
    import sys
    from PySide6 import QtWidgets
    import pyqtgraph.parametertree as pt
    
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
    
    app = QtWidgets.QApplication(sys.argv)
    
    # Create main window to handle layout
    main_window = QtWidgets.QMainWindow()
    main_window.setWindowTitle("Test Runner Parameter Demo")
    main_window.resize(800, 500)
    
    # Create central widget and layout
    central_widget = QtWidgets.QWidget()
    main_window.setCentralWidget(central_widget)
    layout = QtWidgets.QVBoxLayout(central_widget)
    layout.setContentsMargins(0, 0, 0, 0)
    
    # Create and configure the parameter tree
    tree = pt.ParameterTree()
    tree.setAlternatingRowColors(False)
    tree.header().setStretchLastSection(False)  # Don't auto-stretch last column
    tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Interactive)  # Name column
    tree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)  # Value column
    tree.header().setMinimumSectionSize(100)  # Minimum column width
    
    # Add tree to layout
    layout.addWidget(tree)
    
    # Create test parameters
    params = [
        dict(name="Test 1", type="testrunner", value=0),
        dict(name="Test 2", type="testrunner", value=0),
        dict(name="Test 3", type="testrunner", value=0),
    ]

    p = Parameter.create(name="Test Explorer", type="group", children=params)
    tree.setParameters(p, showTop=False)

    # Track start times for demo
    start_times = {}

    # Demo signal handlers
    def on_run_clicked(param):
        logging.info(f"Starting {param.name()}")
        start_times[param.name()] = datetime.now()
        param.setOpts(status=TestStatus.RUNNING, elapsed_time=0)
        test_timer.start(100)
        
    def on_stop_clicked(param):
        logging.info(f"Stopping {param.name()}")
        start_times.pop(param.name(), None)
        param.reset()

    def on_rerun_clicked(param):
        logging.info(f"Rerunning {param.name()}")
        start_times[param.name()] = datetime.now()
        param.setValue(0)
        param.setOpts(status=TestStatus.RUNNING, elapsed_time=0)
        test_timer.start(100)

    # Connect signals for each test
    for test in p.children():
        test.sigRunClicked.connect(on_run_clicked)
        test.sigStopClicked.connect(on_stop_clicked)
        test.sigRerunClicked.connect(on_rerun_clicked)

    # Demo progress simulation
    test_timer = QtCore.QTimer()
    def update_running_tests():
        running_tests = False
        for test in p.children():
            if test.getStatus() == TestStatus.RUNNING:
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
                    # Randomly select a completion status
                    import random
                    completion_status = random.choice([
                        TestStatus.PASS,
                        TestStatus.FAIL,
                        TestStatus.ERROR
                    ])
                    test.setStatus(completion_status)
                    start_times.pop(test.name(), None)
                    logging.info(f"Test {test.name()} completed with status: {completion_status}")
        
        # Stop timer if no tests running
        if not running_tests:
            test_timer.stop()
            logging.debug("All tests complete, stopping timer")
    
    test_timer.timeout.connect(update_running_tests)

    # Show the main window instead of just the tree
    main_window.show()
    sys.exit(app.exec_())