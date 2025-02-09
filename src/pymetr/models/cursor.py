# models/cursor.py
from pymetr.models.base import BaseModel
from typing import Optional
from PySide6.QtCore import QThread, Qt, QMetaObject, Q_ARG
from pymetr.core.logging import logger

class Cursor(BaseModel):
    """
    An infinite line on the plot, either vertical (axis='x') or horizontal (axis='y').
    """

    def __init__(
        self, 
        axis: str = "x", 
        position: float = 0.0,
        color: str = "yellow",
        style: str = "solid",
        width: int = 1,
        visible: bool = True,
        model_id: Optional[str] = None,
    ):
        super().__init__(model_id=model_id)
        
        # Validate axis
        if axis not in ("x", "y"):
            raise ValueError("Cursor axis must be 'x' or 'y'.")

        self.set_property("axis", axis)
        self.set_property("position", position)
        self.set_property("color", color)
        self.set_property("style", style)   # 'solid', 'dash', 'dot', etc.
        self.set_property("width", width)
        self.set_property("visible", visible)

    @property
    def axis(self) -> str:
        return self.get_property("axis")

    @property
    def position(self) -> float:
        return self.get_property("position")

    def set_position(self, pos: float):
        # For thread safety, we might schedule updates if needed
        if QThread.currentThread() != self.thread():
            QMetaObject.invokeMethod(
                self,
                "_set_position_internal",
                Qt.QueuedConnection,
                Q_ARG(float, pos)
            )
        else:
            self._set_position_internal(pos)

    def _set_position_internal(self, pos: float):
        self.set_property("position", pos)
        logger.debug(f"Cursor {self.id} moved to {pos} on {self.axis} axis.")
