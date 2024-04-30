# --- display_panel.py ---
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QComboBox, QFrame
from PySide6.QtCore import Signal

class QuickPanel(QWidget):
    plotModeChanged = Signal(str)
    roiPlotToggled = Signal(bool)
    testTraceClicked = Signal()
    screenshotClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QHBoxLayout(self)

        self.plot_mode_combo_box = QComboBox()
        self.plot_mode_combo_box.addItems(["Single", "Stack", "Run"])
        self.plot_mode_combo_box.currentTextChanged.connect(self.on_plot_mode_changed)
        self.layout.addWidget(self.plot_mode_combo_box)

        self.roi_plot_toggle = QPushButton("Region Plot")
        self.roi_plot_toggle.setCheckable(True)
        self.roi_plot_toggle.setChecked(False)
        self.roi_plot_toggle.toggled.connect(self.on_roi_plot_toggled)
        self.layout.addWidget(self.roi_plot_toggle)

        self.screenshot_button = QPushButton("Screenshot")
        self.screenshot_button.clicked.connect(self.on_screenshot_clicked)
        self.layout.addWidget(self.screenshot_button)

        self.test_trace_button = QPushButton("Test Trace")
        self.test_trace_button.clicked.connect(self.on_test_trace_clicked)
        self.layout.addWidget(self.test_trace_button)

    def on_plot_mode_changed(self, plot_mode):
        self.plotModeChanged.emit(plot_mode)

    def on_roi_plot_toggled(self, checked):
        self.roiPlotToggled.emit(checked)

    def on_screenshot_clicked(self):
        self.screenshotClicked.emit()

    def on_test_trace_clicked(self):
        self.testTraceClicked.emit()