# app/models/marker.py

from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal
import logging
from .base import BaseModel

logger = logging.getLogger(__name__)

class Marker(BaseModel, QObject):
    """
    A vertical marker line with label.
    
    Signals:
        position_changed(str, float): Emitted when position changes (marker_id, new_position)
        style_changed(str, str, Any): Emitted when style property changes (marker_id, property_name, value)
        visibility_changed(str, bool): Emitted when visibility changes (marker_id, is_visible)
    """
    
    position_changed = Signal(str, float)  # marker_id, new_position
    style_changed = Signal(str, str, Any)  # marker_id, property_name, value
    visibility_changed = Signal(str, bool)  # marker_id, is_visible

    def __init__(
        self,
        plot_id: str,
        label: str,
        position: float = 0.0,
        color: str = "#FF0000",
        visible: bool = True,
        id: Optional[str] = None
    ):
        BaseModel.__init__(self, id)
        QObject.__init__(self)
        
        self.plot_id = plot_id
        self.label = label
        self._position = position
        self._color = color
        self._visible = visible

        logger.debug(f"Created Marker '{self.label}' with ID: {self.id}")

    @property
    def position(self) -> float:
        return self._position

    @position.setter
    def position(self, value: float):
        old_position = self._position
        self._position = value
        logger.debug(f"Marker ID={self.id}: Position changed from {old_position} to {value}.")
        self.position_changed.emit(self.id, value)

    @property
    def color(self) -> str:
        return self._color

    @color.setter
    def color(self, value: str):
        old_color = self._color
        self._color = value
        logger.debug(f"Marker ID={self.id}: Color changed from {old_color} to {value}.")
        self.style_changed.emit(self.id, "color", value)

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        old_visibility = self._visible
        self._visible = value
        logger.debug(f"Marker ID={self.id}: Visibility changed from {old_visibility} to {value}.")
        self.visibility_changed.emit(self.id, value)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the Marker to a dictionary."""
        return {
            "id": self.id,
            "plot_id": self.plot_id,
            "label": self.label,
            "position": self.position,
            "color": self.color,
            "visible": self.visible
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Marker':
        """Deserialize a Marker from a dictionary."""
        marker = Marker(
            plot_id=data["plot_id"],
            label=data["label"],
            position=data.get("position", 0.0),
            color=data.get("color", "#FF0000"),
            visible=data.get("visible", True),
            id=data.get("id")
        )
        logger.debug(f"Marker.from_dict: Deserialized Marker ID={marker.id}")
        return marker