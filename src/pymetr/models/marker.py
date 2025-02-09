# models/marker.py
from pymetr.models.base import BaseModel
from typing import Optional, List, Tuple
from PySide6.QtCore import QThread, Qt, QMetaObject, Q_ARG
from pymetr.core.logging import logger

class Marker(BaseModel):
    """
    A marker on the plot, typically a scatter point or set of points, 
    plus optional text annotation.
    """

    def __init__(
        self, 
        x: float, 
        y: float,
        label: str = "",
        color: str = "yellow",
        size: int = 8,
        symbol: str = "o",  # or e.g. 't', 's', 'd' for triangles, squares, diamonds
        visible: bool = True,
        model_id: Optional[str] = None,
    ):
        super().__init__(model_id=model_id)
        self.set_property("x", x)
        self.set_property("y", y)
        self.set_property("label", label)
        self.set_property("color", color)
        self.set_property("size", size)
        self.set_property("symbol", symbol)
        self.set_property("visible", visible)

    @property
    def position(self) -> Tuple[float, float]:
        return (self.get_property("x"), self.get_property("y"))

    def set_position(self, x: float, y: float):
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

    def _set_position_internal(self, x: float, y: float):
        self.set_property("x", x)
        self.set_property("y", y)
        logger.debug(f"Marker {self.id} moved to ({x}, {y}).")
