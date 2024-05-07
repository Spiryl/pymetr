# --- marker_manager.py ---

import logging
logger = logging.getLogger(__name__)

from PySide6.QtCore import QObject, Signal
from pymetr.core.marker import Marker

class MarkerManager(QObject):
    markerAdded = Signal(Marker)
    markerRemoved = Signal(str)
    markerVisibilityChanged = Signal(str, bool)
    markerLabelChanged = Signal(str, str)
    markerColorChanged = Signal(str, str)
    markerShapeChanged = Signal(str, str)
    markersCleared = Signal()
    markerSizeChanged = Signal(str, int)
    markerPlacementModeChanged = Signal(str, str)
    markerPositionChanged = Signal(str, float)

    def __init__(self):
        super().__init__()
        self.markers = []

    def add_marker(self, marker):
        self.markers.append(marker)
        self.markerAdded.emit(marker)

    def remove_marker(self, marker_label):
        for marker in self.markers:
            if marker.label == marker_label:
                self.markers.remove(marker)
                self.markerRemoved.emit(marker_label)
                break

    def set_marker_visibility(self, marker_label, visible):
        for marker in self.markers:
            if marker.label == marker_label:
                marker.visible = visible
                self.markerVisibilityChanged.emit(marker_label, visible)
                break

    def set_marker_label(self, old_label, new_label):
        for marker in self.markers:
            if marker.label == old_label:
                marker.label = new_label
                self.markerLabelChanged.emit(old_label, new_label)
                break

    def set_marker_color(self, marker_label, color):
        for marker in self.markers:
            if marker.label == marker_label:
                marker.color = color
                self.markerColorChanged.emit(marker_label, color)
                break

    def get_marker_by_label(self, marker_label):
        for marker in self.markers:
            if marker.label == marker_label:
                return marker
        return None
    
    def set_marker_shape(self, marker_label, shape):
        for marker in self.markers:
            if marker.label == marker_label:
                marker.shape = shape
                self.markerShapeChanged.emit(marker_label, shape)
                break

    def set_marker_size(self, marker_label, size):
        for marker in self.markers:
            if marker.label == marker_label:
                marker.size = size
                self.markerSizeChanged.emit(marker_label, size)
                break

    def set_marker_placement_mode(self, marker_label, mode):
        for marker in self.markers:
            if marker.label == marker_label:
                marker.placement_mode = mode
                self.markerPlacementModeChanged.emit(marker_label, mode)
                break

    def clear_markers(self):
        self.markers.clear()
        self.markersCleared.emit()

    def set_marker_position(self, marker_label, position):
        for marker in self.markers:
            if marker.label == marker_label:
                marker.position = position
                self.markerPositionChanged.emit(marker_label, position)
                break