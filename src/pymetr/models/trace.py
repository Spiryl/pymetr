from typing import Optional
import numpy as np
from pymetr.models.base import BaseModel
from pymetr.core.logging import logger

class Trace(BaseModel):
    """
    A single data trace within a plot.

    Properties include:
      - x_data / y_data: Arrays of numeric data
      - name: Display name
      - color: Color of the trace (None => default)
      - style: Line style (e.g., 'solid', 'dash', 'dot', 'dash-dot')
      - width: Line width
      - marker_style: Marker style ('' => none, 'o' => circle, etc.)
      - mode: 'Group' or 'Isolate' (whether trace is on main axis or its own)
      - visible: Whether the trace is drawn
      - opacity: For future dimming/selection (0.0 => invisible, 1.0 => opaque)
    """

    def __init__(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        name: str = "",
        model_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(model_type='Trace', model_id=model_id)
        # Store data arrays directly (converted to numpy arrays)
        self._x_data = np.asarray(x_data)
        self._y_data = np.asarray(y_data)

        # Basic trace properties
        self.set_property("name", name)
        self.set_property("color", kwargs.get("color", None))  # Let view pick default if None
        self.set_property("style", kwargs.get("style", "solid"))  # 'solid', 'dash', 'dot', 'dash-dot'
        self.set_property("width", kwargs.get("width", 1))
        self.set_property("marker_style", kwargs.get("marker_style", ""))  # e.g. 'o' for circles
        self.set_property("mode", kwargs.get("mode", "Group"))  # or "Isolate"
        self.set_property("visible", kwargs.get("visible", True))
        self.set_property("opacity", kwargs.get("opacity", 1.0))  # 1.0 => fully opaque

    # -- Pythonic Property Accessors --

    @property
    def name(self) -> str:
        return self.get_property("name")

    @name.setter
    def name(self, value: str):
        self.set_property("name", value)

    @property
    def x_data(self) -> np.ndarray:
        return self._x_data

    @property
    def y_data(self) -> np.ndarray:
        return self._y_data

    @property
    def data(self):
        """Return a tuple (x_data, y_data)."""
        return (self._x_data, self._y_data)

    @data.setter
    def data(self, new_data):
        x_data, y_data = new_data
        self._x_data = np.asarray(x_data)
        self._y_data = np.asarray(y_data)
        # Emit a property change event for 'data'
        self.set_property("data", (x_data, y_data))  # Will emit for you

    @property
    def color(self) -> Optional[str]:
        return self.get_property("color")

    @color.setter
    def color(self, value: str):
        self.set_property("color", value)

    @property
    def style(self) -> str:
        return self.get_property("style", "solid")

    @style.setter
    def style(self, value: str):
        self.set_property("style", value)

    @property
    def width(self) -> int:
        return self.get_property("width", 1)

    @width.setter
    def width(self, value: int):
        self.set_property("width", value)

    @property
    def marker_style(self) -> str:
        return self.get_property("marker_style", "")

    @marker_style.setter
    def marker_style(self, value: str):
        self.set_property("marker_style", value)

    @property
    def mode(self) -> str:
        return self.get_property("mode", "Group")

    @mode.setter
    def mode(self, value: str):
        self.set_property("mode", value)

    @property
    def visible(self) -> bool:
        return self.get_property("visible", True)

    @visible.setter
    def visible(self, value: bool):
        self.set_property("visible", value)

    @property
    def opacity(self) -> float:
        return self.get_property("opacity", 1.0)

    @opacity.setter
    def opacity(self, value: float):
        self.set_property("opacity", value)

    def update_data(self, x_data: np.ndarray, y_data: np.ndarray):
        """Update the underlying arrays and emit a property change."""
        x_data = np.asarray(x_data)
        y_data = np.asarray(y_data)
        self._x_data = x_data
        self._y_data = y_data
        self.set_property("data", (x_data, y_data))  # Will emit for you
