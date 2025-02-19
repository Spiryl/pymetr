from typing import Optional, Tuple, TYPE_CHECKING
import numpy as np
from scipy import interpolate

from PySide6.QtCore import QThread, Qt, QMetaObject, Q_ARG

from pymetr.models.base import BaseModel
from pymetr.core.logging import logger

if TYPE_CHECKING:
    from pymetr.models import Trace

class Marker(BaseModel):
    """
    A marker on the plot, typically a scatter point or set of points,
    plus optional text annotation.
    
    Properties:
        x (float): X-coordinate of the marker
        y (float): Y-coordinate of the marker
        name (str): Text name for the marker
        color (str): Marker color (e.g., 'yellow', '#FFFF00')
        size (int): Marker size in pixels
        symbol (str): Marker symbol ('o' for circle, 't' for triangle, etc.)
        visible (bool): Whether the marker is visible
    """

    def __init__(
        self, 
        x: float = 0, 
        y: float = 0,
        name: str = "",
        color: str = "yellow",
        size: int = 8,
        symbol: str = "o",
        visible: bool = True,
        model_id: Optional[str] = None,
    ):
        super().__init__(model_type='Marker', model_id=model_id, name=name)
        self._init_properties(x, y, name, color, size, symbol, visible)

    def _init_properties(self, x, y, name, color, size, symbol, visible):
        """Initialize all marker properties."""
        self.set_property("x", x)
        self.set_property("y", y)
        self.set_property("name", name)
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
    def name(self) -> str:
        """Get marker name text."""
        return self.get_property("name")

    @name.setter
    def name(self, value: str):
        self.set_property("name", value)

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

    @property
    def bound_to_trace(self) -> bool:
        """Check if marker is bound to a trace."""
        if not self.state:
            return False
        parent = self.state.get_parent(self.id)
        return parent is not None and isinstance(parent, Trace)
    
    def _get_interpolated_y(self, x: float) -> Optional[float]:
        """Get interpolated y-value from parent trace at x position."""
        if not self.bound_to_trace:
            return None
            
        parent = self.state.get_parent(self.id)
        if not parent:
            return None
            
        # Get trace data
        x_data = parent.get_property('x_data', [])
        y_data = parent.get_property('y_data', [])
        if len(x_data) == 0 or len(y_data) == 0:
            return None
            
        # Get interpolation mode
        mode = self.get_property('interpolation_mode', 'linear')
        
        try:
            if mode == 'nearest':
                # Find nearest point
                idx = np.abs(np.array(x_data) - x).argmin()
                return y_data[idx]
                
            elif mode == 'linear':
                # Linear interpolation
                if x < min(x_data) or x > max(x_data):
                    return None
                f = interpolate.interp1d(x_data, y_data, 
                                       bounds_error=False,
                                       fill_value=np.nan)
                return float(f(x))
                
        except Exception as e:
            logger.error(f"Error interpolating marker value: {e}")
            return None
            
        return None
    
    def get_position(self) -> Tuple[float, float]:
        """
        Get marker position, computing y from trace if bound.
        Returns (x, y) tuple.
        """
        x = self.get_property('x', 0.0)
        
        if self.bound_to_trace:
            # Get y from trace interpolation
            y = self._get_interpolated_y(x)
            if y is not None:
                return (x, y)
        
        # Free marker or interpolation failed
        return (x, self.get_property('y', 0.0))
    
    def get_uncertainty_bounds(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Get uncertainty bounds if enabled.
        Returns (lower, upper) tuple or (None, None) if disabled.
        """
        if not self.get_property('uncertainty_visible', False):
            return (None, None)
            
        _, y = self.get_position()
        lower = y - self.get_property('uncertainty_lower', 0.0)
        upper = y + self.get_property('uncertainty_upper', 0.0)
        return (lower, upper)
    
    def follows_parent_isolation(self) -> bool:
        """
        Determine if marker should follow parent into isolation.
        True if bound to a trace.
        """
        return self.bound_to_trace
    
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