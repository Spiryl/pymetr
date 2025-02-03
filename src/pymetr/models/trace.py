# app/models/trace.py

from typing import Dict, List, Optional, Any
import numpy as np
from .base import BaseModel
from PySide6.QtCore import QObject, Signal

import logging

logger = logging.getLogger(__name__)

class Trace(BaseModel, QObject):
    """
    A single data trace on a plot.
    
    Signals:
        data_changed(str): Emitted when x_data or y_data changes (trace_id)
        style_changed(str, str, Any): Emitted when any style property changes (trace_id, property_name, value)
        visibility_changed(str, bool): Emitted when visibility changes (trace_id, is_visible)
        mode_changed(str, str): Emitted when mode changes (trace_id, new_mode)
    """
    
    # Define signals
    data_changed = Signal(str)  # trace_id
    style_changed = Signal(str, str, Any)  # trace_id, property_name, new_value
    visibility_changed = Signal(str, bool)  # trace_id, is_visible
    mode_changed = Signal(str, str)  # trace_id, new_mode

    def __init__(
        self,
        plot_id: str,
        name: str,
        x_data: Optional[np.ndarray] = None,
        y_data: Optional[np.ndarray] = None,
        id: Optional[str] = None,
        **style_kwargs
    ):
        BaseModel.__init__(self, id)
        QObject.__init__(self)
        
        self.plot_id = plot_id
        self.name = name
        
        # Data arrays
        self._x_data = self._ensure_numpy_array(x_data) if x_data is not None else np.array([])
        self._y_data = self._ensure_numpy_array(y_data) if y_data is not None else np.array([])

        # Style properties with defaults
        self._color = style_kwargs.get("color", "#000000")
        self._width = style_kwargs.get("width", 1.0)
        self._style = style_kwargs.get("style", "solid")  # solid, dash, dot, dash-dot
        self._opacity = style_kwargs.get("opacity", 1.0)
        self._mode = style_kwargs.get("mode", "Group")  # "Group" or "Isolate"
        self._visible = style_kwargs.get("visible", True)

        logger.debug(f"Created Trace '{self.name}' with ID: {self.id}")

    def _ensure_numpy_array(self, data: Any) -> np.ndarray:
        """Ensure data is a numpy array."""
        if not isinstance(data, np.ndarray):
            return np.array(data)
        return data

    # Data Methods
    def set_data(self, x: np.ndarray, y: np.ndarray):
        """Set both x_data and y_data atomically."""
        if len(x) != len(y):
            logger.error(f"Trace ID={self.id}: x_data length {len(x)} does not match y_data length {len(y)}.")
            raise ValueError("x_data and y_data must be of the same length.")
            
        self._x_data = self._ensure_numpy_array(x)
        self._y_data = self._ensure_numpy_array(y)
        
        logger.debug(f"Trace ID={self.id}: Data set with {len(x)} points each for x and y.")
        self.data_changed.emit(self.id)

    # Property Definitions
    @property
    def x_data(self) -> np.ndarray:
        return self._x_data

    @x_data.setter
    def x_data(self, value: np.ndarray):
        if len(value) != len(self._y_data):
            logger.error(f"Trace ID={self.id}: x_data length {len(value)} does not match y_data length {len(self._y_data)}.")
            raise ValueError("x_data and y_data must be of the same length.")
        self._x_data = self._ensure_numpy_array(value)
        logger.debug(f"Trace ID={self.id}: x_data updated with {len(value)} points.")
        self.data_changed.emit(self.id)

    @property
    def y_data(self) -> np.ndarray:
        return self._y_data

    @y_data.setter
    def y_data(self, value: np.ndarray):
        if len(value) != len(self._x_data):
            logger.error(f"Trace ID={self.id}: y_data length {len(value)} does not match x_data length {len(self._x_data)}.")
            raise ValueError("y_data and x_data must be of the same length.")
        self._y_data = self._ensure_numpy_array(value)
        logger.debug(f"Trace ID={self.id}: y_data updated with {len(value)} points.")
        self.data_changed.emit(self.id)

    @property
    def color(self) -> str:
        return self._color

    @color.setter
    def color(self, value: str):
        self._color = value
        logger.debug(f"Trace ID={self.id}: Color set to {value}.")
        self.style_changed.emit(self.id, "color", value)

    @property
    def width(self) -> float:
        return self._width

    @width.setter
    def width(self, value: float):
        self._width = value
        logger.debug(f"Trace ID={self.id}: Width set to {value}.")
        self.style_changed.emit(self.id, "width", value)

    @property
    def style(self) -> str:
        return self._style

    @style.setter
    def style(self, value: str):
        if value not in {"solid", "dash", "dot", "dash-dot"}:
            logger.warning(f"Trace ID={self.id}: Invalid style '{value}'. Keeping existing style '{self._style}'.")
            return
        self._style = value
        logger.debug(f"Trace ID={self.id}: Style set to {value}.")
        self.style_changed.emit(self.id, "style", value)

    @property
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, value: float):
        self._opacity = value
        logger.debug(f"Trace ID={self.id}: Opacity set to {value}.")
        self.style_changed.emit(self.id, "opacity", value)

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str):
        if value not in {"Group", "Isolate"}:
            logger.warning(f"Trace ID={self.id}: Invalid mode '{value}'. Keeping existing mode '{self._mode}'.")
            return
        old_mode = self._mode
        self._mode = value
        logger.debug(f"Trace ID={self.id}: Mode changed from '{old_mode}' to '{value}'.")
        self.mode_changed.emit(self.id, value)

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        self._visible = value
        logger.debug(f"Trace ID={self.id}: Visibility set to {value}.")
        self.visibility_changed.emit(self.id, value)

    # Serialization
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the Trace to a dictionary."""
        return {
            "id": self.id,
            "plot_id": self.plot_id,
            "name": self.name,
            "x_data": self._x_data.tolist(),
            "y_data": self._y_data.tolist(),
            "color": self.color,
            "width": self.width,
            "style": self.style,
            "opacity": self.opacity,
            "mode": self.mode,
            "visible": self.visible
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Trace':
        """Deserialize a Trace from a dictionary."""
        trace = Trace(
            plot_id=data["plot_id"],
            name=data["name"],
            x_data=np.array(data["x_data"]),
            y_data=np.array(data["y_data"]),
            id=data.get("id"),
            color=data.get("color", "#000000"),
            width=data.get("width", 1.0),
            style=data.get("style", "solid"),
            opacity=data.get("opacity", 1.0),
            mode=data.get("mode", "Group"),
            visible=data.get("visible", True)
        )
        logger.debug(f"Trace.from_dict: Deserialized Trace ID={trace.id}")
        return trace