from pymetr.models.base import BaseModel
from typing import Optional
from PySide6.QtCore import QThread, Qt, QMetaObject, Q_ARG
from pymetr.core.logging import logger

class Cursor(BaseModel):
    """
    An infinite line on the plot, either vertical (axis='x') or horizontal (axis='y').
    
    Properties:
        axis (str): 'x' for vertical cursor, 'y' for horizontal cursor
        position (float): Position along the axis
        color (str): Cursor color (e.g., 'yellow', '#FFFF00')
        style (str): Line style ('solid', 'dash', 'dot', 'dash-dot')
        width (int): Line width in pixels
        visible (bool): Whether the cursor is visible
    """

    def __init__(
        self, 
        name: str = "Cursor",
        axis: str = "x", 
        position: float = 0.0,
        color: str = "yellow",
        style: str = "solid",
        width: int = 1,
        visible: bool = True,
        model_id: Optional[str] = None,
    ):
        super().__init__(model_id=model_id, name=name)
        
        # Validate axis
        if axis not in ("x", "y"):
            raise ValueError("Cursor axis must be 'x' or 'y'.")

        # Initialize all properties
        self._init_properties(name, axis, position, color, style, width, visible)

    def _init_properties(self, name, axis, position, color, style, width, visible):
        """Initialize all cursor properties."""
        self.set_property("name", name)
        self.set_property("axis", axis)
        self.set_property("position", position)
        self.set_property("color", color)
        self.set_property("style", style)
        self.set_property("width", width)
        self.set_property("visible", visible)

    # --- Property Accessors ---

    @property
    def name(self) -> str:
        return self.get_property("name")

    @name.setter
    def name(self, value: str):
        self.set_property("name", value)

    @property
    def axis(self) -> str:
        """Get the cursor axis ('x' or 'y')."""
        return self.get_property("axis")

    @axis.setter
    def axis(self, value: str):
        if value not in ("x", "y"):
            raise ValueError("Cursor axis must be 'x' or 'y'.")
        self.set_property("axis", value)

    @property
    def position(self) -> float:
        """Get the cursor position."""
        return self.get_property("position")

    @position.setter
    def position(self, value: float):
        """Set the cursor position with thread safety."""
        if QThread.currentThread() != self.thread():
            QMetaObject.invokeMethod(
                self,
                "_set_position_internal",
                Qt.QueuedConnection,
                Q_ARG(float, value)
            )
        else:
            self._set_position_internal(value)

    @property
    def color(self) -> str:
        """Get the cursor color."""
        return self.get_property("color")

    @color.setter
    def color(self, value: str):
        self.set_property("color", value)

    @property
    def style(self) -> str:
        """Get the cursor line style."""
        return self.get_property("style")

    @style.setter
    def style(self, value: str):
        self.set_property("style", value)

    @property
    def width(self) -> int:
        """Get the cursor line width."""
        return self.get_property("width")

    @width.setter
    def width(self, value: int):
        self.set_property("width", value)

    @property
    def visible(self) -> bool:
        """Get cursor visibility."""
        return self.get_property("visible")

    @visible.setter
    def visible(self, value: bool):
        self.set_property("visible", value)

    # --- Internal Methods ---

    def _set_position_internal(self, pos: float):
        """Internal method to update position."""
        self.set_property("position", pos)
        logger.debug(f"Cursor {self.id} moved to {pos} on {self.axis} axis.")

    # --- Public Methods ---

    def set_position(self, pos: float):
        """Public method for setting position (maintains backward compatibility)."""
        self.position = pos