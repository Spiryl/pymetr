from pymetr.models.base import BaseModel
from typing import Optional, Tuple
from PySide6.QtCore import QThread, Qt, QMetaObject, Q_ARG
from pymetr.core.logging import logger

class Marker(BaseModel):
    """
    A marker on the plot, typically a scatter point or set of points,
    plus optional text annotation.
    
    Properties:
        x (float): X-coordinate of the marker
        y (float): Y-coordinate of the marker
        label (str): Text label for the marker
        color (str): Marker color (e.g., 'yellow', '#FFFF00')
        size (int): Marker size in pixels
        symbol (str): Marker symbol ('o' for circle, 't' for triangle, etc.)
        visible (bool): Whether the marker is visible
    """

    def __init__(
        self, 
        x: float, 
        y: float,
        label: str = "",
        color: str = "yellow",
        size: int = 8,
        symbol: str = "o",
        visible: bool = True,
        model_id: Optional[str] = None,
    ):
        super().__init__(model_id=model_id, name=label)
        self._init_properties(x, y, label, color, size, symbol, visible)

    def _init_properties(self, x, y, label, color, size, symbol, visible):
        """Initialize all marker properties."""
        self.set_property("x", x)
        self.set_property("y", y)
        self.set_property("label", label)
        self.set_property("color", color)
        self.set_property("size", size)
        self.set_property("symbol", symbol)
        self.set_property("visible", visible)

    # --- Property Accessors ---

    @property
    def x(self) -> float:
        """Get marker x-coordinate."""
        return self.get_property("x")

    @x.setter
    def x(self, value: float):
        self.set_property("x", value)

    @property
    def y(self) -> float:
        """Get marker y-coordinate."""
        return self.get_property("y")

    @y.setter
    def y(self, value: float):
        self.set_property("y", value)

    @property
    def label(self) -> str:
        """Get marker label text."""
        return self.get_property("label")

    @label.setter
    def label(self, value: str):
        self.set_property("label", value)

    @property
    def color(self) -> str:
        """Get marker color."""
        return self.get_property("color")

    @color.setter
    def color(self, value: str):
        self.set_property("color", value)

    @property
    def size(self) -> int:
        """Get marker size."""
        return self.get_property("size")

    @size.setter
    def size(self, value: int):
        self.set_property("size", value)

    @property
    def symbol(self) -> str:
        """Get marker symbol."""
        return self.get_property("symbol")

    @symbol.setter
    def symbol(self, value: str):
        self.set_property("symbol", value)

    @property
    def visible(self) -> bool:
        """Get marker visibility."""
        return self.get_property("visible")

    @visible.setter
    def visible(self, value: bool):
        self.set_property("visible", value)

    @property
    def position(self) -> Tuple[float, float]:
        """Get marker position as (x, y) tuple."""
        return (self.x, self.y)

    # --- Public Methods ---

    def set_position(self, x: float, y: float):
        """Set marker position with thread safety."""
        if QThread.currentThread() != self.thread():
            QMetaObject.invokeMethod(
                self,
                "_set_position_internal",
                Qt.QueuedConnection,
                Q_ARG(float, x),
                Q_ARG(float, y)
            )
        else:
            self._set_position_internal(x, y)

    # --- Internal Methods ---

    def _set_position_internal(self, x: float, y: float):
        """Internal method to update position."""
        self.set_property("x", x)
        self.set_property("y", y)
        logger.debug(f"Marker {self.id} moved to ({x}, {y}).")