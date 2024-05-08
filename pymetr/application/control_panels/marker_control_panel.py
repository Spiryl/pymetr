# --- marker_control_panel.py ---

import logging
logger = logging.getLogger(__name__)

from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QListWidget, QListWidgetItem, QGroupBox, QToolButton
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QComboBox, QColorDialog, QLabel, QSpinBox, QDoubleSpinBox
from PySide6.QtGui import QColor, QPixmap, QIcon
from PySide6.QtCore import Signal, Qt

from pymetr.core.marker import Marker

class MarkerControlPanel(QWidget):
    markerAdded = Signal(Marker)
    markerRemoved = Signal(str)

    def __init__(self, marker_manager, parent=None):
        super().__init__(parent)
        self.marker_manager = marker_manager

        layout = QVBoxLayout()

        self.marker_list_group_box = QGroupBox("Markers")
        marker_list_layout = QVBoxLayout()

        self.marker_list = QListWidget()
        marker_list_layout.addWidget(self.marker_list)
        self.marker_list_group_box.setLayout(marker_list_layout)
        layout.addWidget(self.marker_list_group_box)

        self.add_button = QPushButton("Add Marker")
        self.add_button.clicked.connect(self.add_marker)
        layout.addWidget(self.add_button)

        self.setLayout(layout)

        # self.marker_manager.markerAdded.connect(self.add_marker)
        # self.marker_manager.markerRemoved.connect(self.remove_marker)
        # self.marker_manager.markersCleared.connect(self.clear_markers)
        # self.marker_manager.markerSizeChanged.connect(self.on_marker_size_changed)
        # self.marker_manager.markerPlacementModeChanged.connect(self.on_marker_placement_mode_changed)
        # self.marker_manager.markerPositionChanged.connect(self.on_marker_position_changed)

    def add_marker(self):

        # Generate a unique label for the new marker
        marker_count = len(self.marker_manager.markers)
        marker_label = f"Marker_{marker_count + 1}"

        # Create a new marker with default properties
        marker = Marker(label=marker_label, color="#888888", shape="Circle", position=0.0)

        # Create a MarkerListItem for the new marker
        item = MarkerListItem(marker, self.marker_manager, self)
        list_item = QListWidgetItem()
        list_item.setSizeHint(item.sizeHint())
        self.marker_list.addItem(list_item)
        self.marker_list.setItemWidget(list_item, item)

        item.visibilityChanged.connect(self.marker_manager.set_marker_visibility)
        item.labelChanged.connect(self.marker_manager.set_marker_label)
        item.colorChanged.connect(self.marker_manager.set_marker_color)
        item.shapeChanged.connect(self.marker_manager.set_marker_shape)
        item.markerRemoved.connect(self.marker_manager.remove_marker)
        item.positionChanged.connect(self.marker_manager.set_marker_position)
        item.markerRemoved.connect(self.remove_marker)

        self.markerAdded.emit(marker)

    def remove_marker(self, marker_label):
        for i in range(self.marker_list.count()):
            list_item = self.marker_list.item(i)
            item_widget = self.marker_list.itemWidget(list_item)
            if item_widget.marker.label == marker_label:
                self.marker_list.takeItem(i)
                break

    def on_marker_size_changed(self, marker_label, size):
        for i in range(self.marker_list.count()):
            list_item = self.marker_list.item(i)
            item_widget = self.marker_list.itemWidget(list_item)
            if item_widget.marker.label == marker_label:
                item_widget.size_spinbox.setValue(size)
                break

    def on_marker_placement_mode_changed(self, marker_label, mode):
        for i in range(self.marker_list.count()):
            list_item = self.marker_list.item(i)
            item_widget = self.marker_list.itemWidget(list_item)
            if item_widget.marker.label == marker_label:
                item_widget.placement_mode_combo.setCurrentText(mode)
                break

    def on_marker_position_changed(self, marker_label, position):
        for i in range(self.marker_list.count()):
            list_item = self.marker_list.item(i)
            item_widget = self.marker_list.itemWidget(list_item)
            if item_widget.marker.label == marker_label:
                item_widget.position_spinbox.setValue(position)
                break

    def clear_markers(self):
        self.marker_list.clear()

class MarkerListItem(QWidget):
    visibilityChanged = Signal(str, bool)
    labelChanged = Signal(str, str)
    colorChanged = Signal(str, str)
    shapeChanged = Signal(str, str)
    markerRemoved = Signal(str)
    positionChanged = Signal(str, float)

    def __init__(self, marker, marker_manager, parent=None):
        super().__init__(parent)
        self.marker = marker
        self.marker_manager = marker_manager
        layout = QHBoxLayout()

        self.visible_button = QToolButton()
        self.visible_button.setIcon(QIcon("pymetr/application/icons/visibility_on.png"))
        self.visible_button.setCheckable(True)
        self.visible_button.setChecked(marker.visible)
        self.visible_button.toggled.connect(self.toggle_visibility)
        self.visible_button.setFixedSize(24, 24)
        layout.addWidget(self.visible_button)

        self.label_icon = QLabel()
        self.label_icon.setPixmap(QPixmap("pymetr/application/icons/label.png").scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(self.label_icon)

        self.label = QLineEdit(marker.label)
        self.label.editingFinished.connect(self.update_label)
        self.label.setMinimumWidth(120)
        layout.addWidget(self.label)

        self.position_spinbox = QDoubleSpinBox()
        self.position_spinbox.setRange(-9999999.0, 9999999.0)
        self.position_spinbox.setDecimals(6)
        self.position_spinbox.setValue(marker.position if marker.position is not None else 0.0)
        self.position_spinbox.valueChanged.connect(self.update_position)
        layout.addWidget(self.position_spinbox)

        self.color_button = QPushButton()
        self.color_button.setStyleSheet(f"background-color: {marker.color}")
        self.color_button.clicked.connect(self.select_color)
        self.color_button.setMinimumWidth(80)
        layout.addWidget(self.color_button)

        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["Circle", "Square", "Diamond", "Triangle"])
        self.shape_combo.setCurrentText(marker.shape)
        self.shape_combo.currentTextChanged.connect(self.update_shape)
        self.shape_combo.setMinimumWidth(80)
        layout.addWidget(self.shape_combo)

        self.size_spinbox = QSpinBox()
        self.size_spinbox.setRange(1, 50)
        self.size_spinbox.setValue(marker.size)
        self.size_spinbox.valueChanged.connect(self.update_size)
        layout.addWidget(self.size_spinbox)

        self.placement_mode_combo = QComboBox()
        self.placement_mode_combo.addItems(["Nearest", "Interpolate"])
        self.placement_mode_combo.setCurrentText(marker.placement_mode.capitalize())
        self.placement_mode_combo.currentTextChanged.connect(self.update_placement_mode)
        layout.addWidget(self.placement_mode_combo)

        self.delete_button = QToolButton()
        self.delete_button.setIcon(QIcon("pymetr/application/icons/delete.png"))
        self.delete_button.clicked.connect(self.delete_marker)
        self.delete_button.setFixedSize(24, 24)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

    def toggle_visibility(self, checked):
        logger.debug(f"Toggling visibility for marker '{self.marker.label}' to {bool(checked)}")
        icon = QIcon("pymetr/application/icons/visibility_on.png") if checked else QIcon("pymetr/application/icons/visibility_off.png")
        self.visible_button.setIcon(icon)
        self.marker_manager.set_marker_visibility(self.marker.label, checked)

    def update_label(self):
        text = self.label.text()
        logger.debug(f"Updating label for marker '{self.marker.label}' to '{text}'")
        self.marker_manager.set_marker_label(self.marker.label, text)

    def select_color(self):
        color = QColorDialog.getColor(QColor(self.marker.color), self)
        if color.isValid():
            logger.debug(f"Updating color for marker '{self.marker.label}' to '{color.name()}'")
            self.colorChanged.emit(self.marker.label, color.name())
            self.color_button.setStyleSheet(f"background-color: {color.name()}")
            self.marker_manager.set_marker_color(self.marker.label, color.name())

    def update_shape(self, shape):
        logger.debug(f"Updating shape for marker '{self.marker.label}' to '{shape}'")
        self.marker_manager.set_marker_shape(self.marker.label, shape)

    def update_size(self, size):
        self.marker_manager.set_marker_size(self.marker.label, size)

    def update_placement_mode(self, mode):
        self.marker_manager.set_marker_placement_mode(self.marker.label, mode.lower())

    def delete_marker(self):
        logger.debug(f"Deleting marker '{self.marker.label}'")
        self.marker_manager.remove_marker(self.marker.label)
        self.markerRemoved.emit(self.marker.label)

    def update_position(self, position):
        logger.debug(f"Updating position for marker '{self.marker.label}' to '{position}'")
        self.positionChanged.emit(self.marker.label, position)
        self.marker_manager.set_marker_position(self.marker.label, position)
