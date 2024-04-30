# pymetr/application/control_dock.py
import logging
logger = logging.getLogger(__name__)

from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QListWidget, QListWidgetItem, QGroupBox
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QComboBox, QColorDialog,  QDoubleSpinBox, QLabel
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal

class TraceControlPanel(QWidget):
    groupTraces = Signal()
    isolateTraces = Signal()
    clearTraces = Signal()

    def __init__(self, trace_manager, parent=None):
        super().__init__(parent)
        self.trace_manager = trace_manager

        layout = QVBoxLayout()

        self.trace_list_group_box = QGroupBox("Traces")
        trace_list_layout = QVBoxLayout()

        # column_label_layout = QHBoxLayout()
        # visible_label = QLabel("Visible")
        # visible_label.setMinimumWidth(20)
        # column_label_layout.addWidget(visible_label)

        # label_label = QLabel("Label")
        # label_label.setMinimumWidth(120)
        # column_label_layout.addWidget(label_label)
        # column_label_layout.addStretch(1)  # This will make the "Label" column expand

        # color_label = QLabel("Color")
        # color_label.setMinimumWidth(80)
        # column_label_layout.addWidget(color_label)

        # mode_label = QLabel("Mode")
        # mode_label.setMinimumWidth(80)
        # column_label_layout.addWidget(mode_label)

        # thickness_label = QLabel("Thickness")
        # thickness_label.setMinimumWidth(80)
        # column_label_layout.addWidget(thickness_label)

        # style_label = QLabel("Style")
        # style_label.setMinimumWidth(100)
        # column_label_layout.addWidget(style_label)

        # delete_label = QLabel("Delete")
        # delete_label.setMinimumWidth(100)
        # column_label_layout.addWidget(delete_label)

        # trace_list_layout.addLayout(column_label_layout)

        self.trace_list = QListWidget()
        trace_list_layout.addWidget(self.trace_list)
        self.trace_list_group_box.setLayout(trace_list_layout)
        layout.addWidget(self.trace_list_group_box)

        button_layout = QHBoxLayout()

        self.trace_mode_combo = QComboBox()
        self.trace_mode_combo.addItems(["Group", "Isolate"])
        self.trace_mode_combo.currentTextChanged.connect(self.trace_manager.set_trace_mode)
        button_layout.addWidget(self.trace_mode_combo)

        self.group_all_button = QPushButton("Group All")
        self.group_all_button.clicked.connect(self.group_all_traces)
        button_layout.addWidget(self.group_all_button)

        self.isolate_all_button = QPushButton("Isolate All")
        self.isolate_all_button.clicked.connect(self.isolate_all_traces)
        button_layout.addWidget(self.isolate_all_button)

        self.clear_traces_button = QPushButton("Clear Traces")
        self.clear_traces_button.clicked.connect(self.clear_traces)
        button_layout.addWidget(self.clear_traces_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.trace_manager.traceAdded.connect(self.add_trace)

    def add_trace(self, trace):
        item = TraceListItem(trace, self.trace_manager, self)
        list_item = QListWidgetItem()
        list_item.setSizeHint(item.sizeHint())
        self.trace_list.addItem(list_item)
        self.trace_list.setItemWidget(list_item, item)

    def remove_trace(self, trace_id):
        for i in range(self.trace_list.count()):
            list_item = self.trace_list.item(i)
            item_widget = self.trace_list.itemWidget(list_item)
            if item_widget.trace.label == trace_id:
                self.trace_list.takeItem(i)
                break

    def clear_traces(self):
        self.trace_list.clear()
        self.clearTraces.emit()
        self.trace_manager.clear_traces()

    def group_all_traces(self):
        for i in range(self.trace_list.count()):
            list_item = self.trace_list.item(i)
            item_widget = self.trace_list.itemWidget(list_item)
            item_widget.mode_combo.setCurrentText("Group")
        self.groupTraces.emit()
        self.trace_manager.group_all_traces()

    def isolate_all_traces(self):
        for i in range(self.trace_list.count()):
            list_item = self.trace_list.item(i)
            item_widget = self.trace_list.itemWidget(list_item)
            item_widget.mode_combo.setCurrentText("Isolate")
        self.isolateTraces.emit()
        self.trace_manager.isolate_all_traces()

class TraceListItem(QWidget):
    visibilityChanged = Signal(str, bool)
    labelChanged = Signal(str, str)
    colorChanged = Signal(str, str)
    modeChanged = Signal(str, str)
    lineThicknessChanged = Signal(str, float)
    lineStyleChanged = Signal(str, str)
    traceRemoved = Signal(str)

    def __init__(self, trace, trace_manager, parent=None):
        super().__init__(parent)
        self.trace = trace
        self.trace_manager = trace_manager
        layout = QHBoxLayout()

        self.visible_checkbox = QCheckBox()
        self.visible_checkbox.setChecked(trace.visible)
        self.visible_checkbox.stateChanged.connect(self.toggle_visibility)
        self.visible_checkbox.setMinimumWidth(20)
        layout.addWidget(self.visible_checkbox)

        self.label = QLineEdit(trace.label)
        self.label.textChanged.connect(self.update_label)
        self.label.setMinimumWidth(120)
        layout.addWidget(self.label)

        self.color_button = QPushButton()
        self.color_button.setStyleSheet(f"background-color: {trace.color}")
        self.color_button.clicked.connect(self.select_color)
        self.color_button.setMinimumWidth(80)
        layout.addWidget(self.color_button)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Group", "Isolate"])
        self.mode_combo.setCurrentText(trace.mode)
        self.mode_combo.currentTextChanged.connect(self.update_mode)
        self.mode_combo.setMinimumWidth(80)
        layout.addWidget(self.mode_combo)

        self.line_width_spinbox = QDoubleSpinBox()
        self.line_width_spinbox.setRange(1, 10.0)
        self.line_width_spinbox.setSingleStep(1)
        self.line_width_spinbox.setValue(trace.line_thickness)
        self.line_width_spinbox.valueChanged.connect(self.update_line_width)
        self.line_width_spinbox.setMinimumWidth(80)
        layout.addWidget(self.line_width_spinbox)

        self.line_style_combo = QComboBox()
        self.line_style_combo.addItems(["Solid", "Dash", "Dot", "Dash-Dot"])
        self.line_style_combo.setCurrentText(trace.line_style)
        self.line_style_combo.currentTextChanged.connect(self.update_line_style)
        self.line_style_combo.setMinimumWidth(80)
        layout.addWidget(self.line_style_combo)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_trace)
        self.delete_button.setMinimumWidth(120)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

    def toggle_visibility(self, state):
        logger.debug(f"Toggling visibility for trace '{self.trace.label}' to {bool(state)}")
        self.visibilityChanged.emit(self.trace.label, bool(state))

    def update_label(self, text):
        logger.debug(f"Updating label for trace '{self.trace.label}' to '{text}'")
        self.labelChanged.emit(self.trace.label, text)

    def select_color(self):
        color = QColorDialog.getColor(QColor(self.trace.color), self)
        if color.isValid():
            logger.debug(f"Updating color for trace '{self.trace.label}' to '{color.name()}'")
            self.colorChanged.emit(self.trace.label, color.name())
            self.color_button.setStyleSheet(f"background-color: {color.name()}")

    def update_mode(self, mode):
        logger.debug(f"Updating mode for trace '{self.trace.label}' to '{mode}'")
        self.modeChanged.emit(self.trace.label, mode)

    def update_line_width(self, width):
        logger.debug(f"Updating line width for trace '{self.trace.label}' to '{width}'")
        self.lineThicknessChanged.emit(self.trace.label, width)

    def update_line_style(self, style):
        logger.debug(f"Updating line style for trace '{self.trace.label}' to '{style}'")
        self.lineStyleChanged.emit(self.trace.label, style)

    def delete_trace(self):
        logger.debug(f"Deleting trace '{self.trace.label}'")
        self.trace_manager.remove_trace(self.trace.label)