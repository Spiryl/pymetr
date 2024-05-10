# --- cursor_control_panel.py ---

import logging
logger = logging.getLogger(__name__)

from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QListWidget, QListWidgetItem, QGroupBox, QToolButton
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QComboBox, QColorDialog, QDoubleSpinBox, QLabel
from PySide6.QtGui import QColor, QPixmap, QIcon
from PySide6.QtCore import Signal, Qt

from pymetr.core.cursor import Cursor

class CursorControlPanel(QWidget):
    cursorAdded = Signal(Cursor)
    cursorRemoved = Signal(str)

    def __init__(self, cursor_manager, parent=None):
        super().__init__(parent)
        self.cursor_manager = cursor_manager

        layout = QVBoxLayout()

        self.cursor_list_group_box = QGroupBox("Cursors")
        cursor_list_layout = QVBoxLayout()

        self.cursor_list = QListWidget()
        cursor_list_layout.addWidget(self.cursor_list)
        self.cursor_list_group_box.setLayout(cursor_list_layout)
        layout.addWidget(self.cursor_list_group_box)

        self.add_button = QPushButton("Add Cursor")
        self.add_button.clicked.connect(self.add_cursor)
        layout.addWidget(self.add_button)

        self.setLayout(layout)

        # self.cursor_manager.cursorAdded.connect(self.add_cursor)
        # self.cursor_manager.cursorRemoved.connect(self.remove_cursor)
        # self.cursor_manager.cursorsCleared.connect(self.clear_cursors)
        # self.cursor_manager.cursorPositionChanged.connect(self.update_cursor_position)

    def add_cursor(self):
        # Generate a unique label for the new cursor
        logger.debug("Adding new cursor")
        cursor_count = len(self.cursor_manager.cursors)
        cursor_label = f"Cursor_{cursor_count + 1}"

        # Create a new cursor with default properties
        cursor = Cursor(label=cursor_label, color="#888888", line_style="Dot", line_thickness=1.0, position=0.0, orientation="x")

        # Create a CursorListItem for the new cursor
        item = CursorListItem(cursor, self.cursor_manager, self)
        list_item = QListWidgetItem()
        list_item.setSizeHint(item.sizeHint())
        self.cursor_list.addItem(list_item)
        self.cursor_list.setItemWidget(list_item, item)
        self.cursorAdded.emit(cursor)

    def remove_cursor(self, cursor_label):
        logger.debug(f"Removing cursor: {cursor_label}")
        for i in range(self.cursor_list.count()):
            list_item = self.cursor_list.item(i)
            item_widget = self.cursor_list.itemWidget(list_item)
            if item_widget.cursor.label == cursor_label:
                self.cursor_list.takeItem(i)
                break
        self.cursorRemoved.emit(cursor_label)

    def clear_cursors(self):
        self.cursor_list.clear()

    def update_cursor_position(self, cursor_label, position):
        logger.debug(f"Updating cursor position in control panel: {cursor_label}, {position}")
        for i in range(self.cursor_list.count()):
            list_item = self.cursor_list.item(i)
            item_widget = self.cursor_list.itemWidget(list_item)
            if item_widget.cursor.label == cursor_label:
                item_widget.position_spinbox.blockSignals(True)
                item_widget.position_spinbox.setValue(position)
                item_widget.position_spinbox.blockSignals(False)
                break

class CursorListItem(QWidget):
    visibilityChanged = Signal(str, bool)
    labelChanged = Signal(str, str)
    colorChanged = Signal(str, str)
    lineStyleChanged = Signal(str, str)
    lineThicknessChanged = Signal(str, float)
    cursorRemoved = Signal(str)
    positionChanged = Signal(str, float)

    def __init__(self, cursor, cursor_manager, parent=None):
        super().__init__(parent)
        self.cursor = cursor
        self.cursor_manager = cursor_manager
        layout = QHBoxLayout()

        self.visible_button = QToolButton()
        self.visible_button.setIcon(QIcon("pymetr/application/icons/visibility_on.png"))
        self.visible_button.setCheckable(True)
        self.visible_button.setChecked(cursor.visible)
        self.visible_button.toggled.connect(self.toggle_visibility)
        self.visible_button.setFixedSize(24, 24)
        layout.addWidget(self.visible_button)

        self.label_icon = QLabel()
        self.label_icon.setPixmap(QPixmap("pymetr/application/icons/label.png").scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(self.label_icon)

        self.label = QLineEdit(cursor.label)
        self.label.editingFinished.connect(self.update_label)
        self.label.setMinimumWidth(120)
        layout.addWidget(self.label)

        self.position_spinbox = QDoubleSpinBox()
        self.position_spinbox.setRange(-1e9, 1e9)  # Adjust the range as needed
        self.position_spinbox.setValue(cursor.position)
        self.position_spinbox.valueChanged.connect(self.update_position)
        layout.addWidget(self.position_spinbox)

        self.color_button = QPushButton()
        self.color_button.setStyleSheet(f"background-color: {cursor.color}")
        self.color_button.clicked.connect(self.select_color)
        self.color_button.setMinimumWidth(80)
        layout.addWidget(self.color_button)

        self.line_style_combo = QComboBox()
        self.line_style_combo.addItems(["Solid", "Dash", "Dot", "Dash-Dot"])
        self.line_style_combo.setCurrentText(cursor.line_style)
        self.line_style_combo.currentTextChanged.connect(self.update_line_style)
        self.line_style_combo.setMinimumWidth(80)
        layout.addWidget(self.line_style_combo)

        self.line_thickness_spinbox = QDoubleSpinBox()
        self.line_thickness_spinbox.setRange(0.5, 5.0)
        self.line_thickness_spinbox.setSingleStep(0.5)
        self.line_thickness_spinbox.setValue(cursor.line_thickness)
        self.line_thickness_spinbox.valueChanged.connect(self.update_line_thickness)
        self.line_thickness_spinbox.setMinimumWidth(80)
        layout.addWidget(self.line_thickness_spinbox)

        self.delete_button = QToolButton()
        self.delete_button.setIcon(QIcon("pymetr/application/icons/delete.png"))
        self.delete_button.clicked.connect(self.delete_cursor)
        self.delete_button.setFixedSize(24, 24)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

    def toggle_visibility(self, checked):
        logger.debug(f"Toggling visibility for cursor '{self.cursor.label}' to {bool(checked)}")
        icon = QIcon("pymetr/application/icons/visibility_on.png") if checked else QIcon("pymetr/application/icons/visibility_off.png")
        self.visible_button.setIcon(icon)
        self.cursor_manager.set_cursor_visibility(self.cursor.label, checked)

    def update_label(self):
        text = self.label.text()
        logger.debug(f"Updating label for cursor '{self.cursor.label}' to '{text}'")
        self.cursor_manager.set_cursor_label(self.cursor.label, text)

    def select_color(self):
        color = QColorDialog.getColor(QColor(self.cursor.color), self)
        if color.isValid():
            logger.debug(f"Updating color for cursor '{self.cursor.label}' to '{color.name()}'")
            self.colorChanged.emit(self.cursor.label, color.name())
            self.color_button.setStyleSheet(f"background-color: {color.name()}")
            self.cursor_manager.set_cursor_color(self.cursor.label, color.name())

    def update_line_style(self, style):
        logger.debug(f"Updating line style for cursor '{self.cursor.label}' to '{style}'")
        self.cursor_manager.set_cursor_line_style(self.cursor.label, style)

    def update_line_thickness(self, thickness):
        logger.debug(f"Updating line thickness for cursor '{self.cursor.label}' to '{thickness}'")
        self.cursor_manager.set_cursor_line_thickness(self.cursor.label, thickness)

    def delete_cursor(self):
        logger.debug(f"Deleting cursor '{self.cursor.label}'")
        self.cursor_manager.remove_cursor(self.cursor.label)

    def update_position(self, position):
        logger.debug(f"Updating cursor position from control panel: {self.cursor.label}, {position}")
        self.positionChanged.emit(self.cursor.label, position)