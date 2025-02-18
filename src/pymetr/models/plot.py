from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
import numpy as np
from pymetr.models.base import BaseModel
from pymetr.core.logging import logger

if TYPE_CHECKING:
    from pymetr.models.trace import Trace
    from pymetr.models.marker import Marker
    from pymetr.models.cursor import Cursor
    from pymetr.models.measurement import Measurement

class Plot(BaseModel):
    """
    A plot container with comprehensive plotting properties.
    
    Properties:
        Basic Properties:
            title (str): Plot title
            x_label (str): X-axis label
            y_label (str): Y-axis label
            x_unit (str): X-axis units
            y_unit (str): Y-axis units
            
        Display Properties:
            grid_enabled (bool): Show/hide grid
            legend_enabled (bool): Show/hide legend
            roi_visible (bool): Show/hide ROI panel
            background_color (str): Plot background color
            foreground_color (str): Text and axis color
            grid_color (str): Grid line color
            grid_alpha (float): Grid transparency
            legend_position (str): Legend placement ('right', 'top', 'bottom', 'left')
            
        Axis Properties:
            x_log (bool): X-axis logarithmic scaling
            y_log (bool): Y-axis logarithmic scaling
            x_inverted (bool): X-axis direction
            y_inverted (bool): Y-axis direction
            x_ticks (List[float]): Custom X-axis tick positions
            y_ticks (List[float]): Custom Y-axis tick positions
            x_tick_labels (List[str]): Custom X-axis tick labels
            y_tick_labels (List[str]): Custom Y-axis tick labels
            
        Range Properties:
            x_lim (Tuple[float, float]): X-axis limits (min, max)
            y_lim (Tuple[float, float]): Y-axis limits (min, max)
    """

    def __init__(self, title: str, model_id: Optional[str] = None):
        super().__init__(model_id=model_id, name=title)
        self._init_properties(title)

    def _init_properties(self, title: str):
        """Initialize all plot properties with defaults."""
        # Basic properties
        self.set_property("title", title)
        self.set_property("x_label", "")
        self.set_property("y_label", "")
        self.set_property("x_unit", "")
        self.set_property("y_unit", "")

        # Display properties
        self.set_property("grid_enabled", True)
        self.set_property("legend_enabled", True)
        self.set_property("roi_visible", True)
        self.set_property("background_color", "#1E1E1E")
        self.set_property("foreground_color", "#FFFFFF")
        self.set_property("grid_color", "#404040")
        self.set_property("grid_alpha", 0.3)
        self.set_property("legend_position", "right")

        # Axis properties
        self.set_property("x_log", False)
        self.set_property("y_log", False)
        self.set_property("x_inverted", False)
        self.set_property("y_inverted", False)
        self.set_property("x_ticks", None)
        self.set_property("y_ticks", None)
        self.set_property("x_tick_labels", None)
        self.set_property("y_tick_labels", None)

        # Range properties
        self.set_property("x_lim", None)
        self.set_property("y_lim", None)

        # ROI properties
        self.set_property("roi", None)  # Will be set when ROI is first shown
        self.set_property("roi_visible", True)

    # --- Basic Property Accessors ---

    @property
    def title(self) -> str:
        return self.get_property("title")

    @title.setter
    def title(self, value: str):
        self.set_property("title", value)

    @property
    def x_label(self) -> str:
        return self.get_property("x_label")

    @x_label.setter
    def x_label(self, value: str):
        self.set_property("x_label", value)

    @property
    def y_label(self) -> str:
        return self.get_property("y_label")

    @y_label.setter
    def y_label(self, value: str):
        self.set_property("y_label", value)

    @property
    def x_unit(self) -> str:
        return self.get_property("x_unit")

    @x_unit.setter
    def x_unit(self, value: str):
        self.set_property("x_unit", value)

    @property
    def y_unit(self) -> str:
        return self.get_property("y_unit")

    @y_unit.setter
    def y_unit(self, value: str):
        self.set_property("y_unit", value)

    # --- Display Property Accessors ---

    @property
    def grid_enabled(self) -> bool:
        return self.get_property("grid_enabled")

    @grid_enabled.setter
    def grid_enabled(self, value: bool):
        self.set_property("grid_enabled", bool(value))

    @property
    def legend_enabled(self) -> bool:
        return self.get_property("legend_enabled")

    @legend_enabled.setter
    def legend_enabled(self, value: bool):
        self.set_property("legend_enabled", bool(value))

    @property
    def roi(self) -> Optional[List[float]]:
        """Get the ROI region as [start, end]."""
        return self.get_property("roi")

    @roi.setter
    def roi(self, value: Optional[List[float]]):
        """Set the ROI region."""
        if value is not None:
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise ValueError("ROI must be a list/tuple of [start, end] or None")
            value = [float(x) for x in value]
        self.set_property("roi", value)

    @property
    def roi_visible(self) -> bool:
        """Get ROI visibility state."""
        return self.get_property("roi_visible", True)

    @roi_visible.setter
    def roi_visible(self, value: bool):
        """Set ROI visibility."""
        self.set_property("roi_visible", bool(value))

    @property
    def background_color(self) -> str:
        return self.get_property("background_color")

    @background_color.setter
    def background_color(self, value: str):
        self.set_property("background_color", value)

    @property
    def foreground_color(self) -> str:
        return self.get_property("foreground_color")

    @foreground_color.setter
    def foreground_color(self, value: str):
        self.set_property("foreground_color", value)

    @property
    def grid_color(self) -> str:
        return self.get_property("grid_color")

    @grid_color.setter
    def grid_color(self, value: str):
        self.set_property("grid_color", value)

    @property
    def grid_alpha(self) -> float:
        return self.get_property("grid_alpha")

    @grid_alpha.setter
    def grid_alpha(self, value: float):
        self.set_property("grid_alpha", float(value))

    @property
    def legend_position(self) -> str:
        return self.get_property("legend_position")

    @legend_position.setter
    def legend_position(self, value: str):
        if value not in ("right", "top", "bottom", "left"):
            raise ValueError("Legend position must be 'right', 'top', 'bottom', or 'left'")
        self.set_property("legend_position", value)

    # --- Axis Property Accessors ---

    @property
    def x_log(self) -> bool:
        return self.get_property("x_log")

    @x_log.setter
    def x_log(self, value: bool):
        self.set_property("x_log", bool(value))

    @property
    def y_log(self) -> bool:
        return self.get_property("y_log")

    @y_log.setter
    def y_log(self, value: bool):
        self.set_property("y_log", bool(value))

    @property
    def x_inverted(self) -> bool:
        return self.get_property("x_inverted")

    @x_inverted.setter
    def x_inverted(self, value: bool):
        self.set_property("x_inverted", bool(value))

    @property
    def y_inverted(self) -> bool:
        return self.get_property("y_inverted")

    @y_inverted.setter
    def y_inverted(self, value: bool):
        self.set_property("y_inverted", bool(value))

    @property
    def x_ticks(self) -> Optional[List[float]]:
        return self.get_property("x_ticks")

    @x_ticks.setter
    def x_ticks(self, value: Optional[List[float]]):
        if value is not None:
            value = [float(x) for x in value]
        self.set_property("x_ticks", value)

    @property
    def y_ticks(self) -> Optional[List[float]]:
        return self.get_property("y_ticks")

    @y_ticks.setter
    def y_ticks(self, value: Optional[List[float]]):
        if value is not None:
            value = [float(y) for y in value]
        self.set_property("y_ticks", value)

    @property
    def x_tick_labels(self) -> Optional[List[str]]:
        return self.get_property("x_tick_labels")

    @x_tick_labels.setter
    def x_tick_labels(self, value: Optional[List[str]]):
        if value is not None:
            value = [str(x) for x in value]
        self.set_property("x_tick_labels", value)

    @property
    def y_tick_labels(self) -> Optional[List[str]]:
        return self.get_property("y_tick_labels")

    @y_tick_labels.setter
    def y_tick_labels(self, value: Optional[List[str]]):
        if value is not None:
            value = [str(y) for y in value]
        self.set_property("y_tick_labels", value)

    # --- Range Property Accessors ---

    @property
    def x_lim(self) -> Optional[Tuple[float, float]]:
        return self.get_property("x_lim")

    @x_lim.setter
    def x_lim(self, value: Optional[Tuple[float, float]]):
        if value is not None:
            if not isinstance(value, (tuple, list)) or len(value) != 2:
                raise ValueError("x_lim must be a tuple/list of (min, max) or None")
            value = (float(value[0]), float(value[1]))
        self.set_property("x_lim", value)

    @property
    def y_lim(self) -> Optional[Tuple[float, float]]:
        return self.get_property("y_lim")

    @y_lim.setter
    def y_lim(self, value: Optional[Tuple[float, float]]):
        if value is not None:
            if not isinstance(value, (tuple, list)) or len(value) != 2:
                raise ValueError("y_lim must be a tuple/list of (min, max) or None")
            value = (float(value[0]), float(value[1]))
        self.set_property("y_lim", value)

# --- Trace Management Methods ---

    def create_trace(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        name: str = "",
        **kwargs
    ) -> 'Trace':
        """
        Create and register a new Trace model.
        
        Args:
            x_data: X-axis data points
            y_data: Y-axis data points
            name: Display name for the trace
            **kwargs: Additional trace properties (color, style, etc.)
            
        Returns:
            Trace: The created trace object
        """
        from pymetr.models import Trace
        trace = self.state.create_model(
            Trace,
            x_data=x_data,
            y_data=y_data,
            name=name,
            **kwargs
        )
        self.add(trace)
        return trace

    def add(self, item: BaseModel) -> None:
        """
        Add an existing Trace, Marker, or Cursor to the plot.
        If the item already has a parent, it will be moved to this plot.
        
        Args:
            item: A Trace, Marker, or Cursor instance
            
        Raises:
            TypeError: If item is not a valid plot item type
        """
        from pymetr.models import Trace, Marker, Cursor
        
        if not isinstance(item, (Trace, Marker, Cursor)):
            raise TypeError(f"Can only add Trace, Marker, or Cursor objects, got {type(item).__name__}")
        
        # Check if item already has a parent
        current_parent = self.state.get_parent(item.id)
        if current_parent:
            # Remove from current parent
            self.state.unlink_models(current_parent.id, item.id)
            
        # Add to this plot
        self.add_child(item)
        logger.debug(f"Added {type(item).__name__} {item.id} to Plot {self.id}")

    def set_trace(
        self,
        trace_name: str,
        x_data: np.ndarray,
        y_data: np.ndarray,
        mode: str = "Group",
        color: Optional[str] = "#ffffff",
        style: str = "solid", 
        width: int = 1,
        marker_style: str = "",
        visible: bool = True,
        opacity: float = 1.0,
    ) -> 'Trace':
        """
        Create or update a trace by name.
        
        Args:
            trace_name: Name to identify the trace
            x_data: X-axis data points
            y_data: Y-axis data points
            mode: 'Group' or 'Isolate'
            color: Trace color (hex or name)
            style: Line style ('solid', 'dash', 'dot', etc.)
            width: Line width
            marker_style: Point marker style
            visible: Visibility flag
            opacity: Opacity value (0.0 to 1.0)
            
        Returns:
            Trace: The created or updated trace object
        """
        from pymetr.models import Trace

        # Look for existing trace
        existing_trace = None
        for t in self.get_traces():
            if t.name == trace_name:
                existing_trace = t
                break

        if existing_trace is None:
            # Create new trace
            logger.debug(f"Creating new trace '{trace_name}' in Plot '{self.title}'.")
            new_trace = self.state.create_model(
                Trace,
                x_data=x_data,
                y_data=y_data,
                name=trace_name,
                mode=mode,
                color=color,
                style=style,
                width=width,
                marker_style=marker_style,
                visible=visible,
                opacity=opacity
            )
            self.add_child(new_trace)
            return new_trace
        else:
            # Update existing trace
            existing_trace.update_data(x_data, y_data)

            # Update style properties if they changed
            props = {
                "mode": mode,
                "color": color,
                "style": style,
                "width": width,
                "marker_style": marker_style,
                "visible": visible,
                "opacity": opacity
            }

            for prop_name, value in props.items():
                current_value = existing_trace.get_property(prop_name)
                if current_value != value:
                    existing_trace.set_property(prop_name, value)
                    
            return existing_trace

    def get_traces(self) -> List['Trace']:
        """Return all Trace children."""
        from pymetr.models import Trace
        return [child for child in self.get_children() if isinstance(child, Trace)]

    def get_markers(self) -> List['Marker']:
        """Return all Marker children."""
        from pymetr.models import Marker
        return [child for child in self.get_children() if isinstance(child, Marker)]

    def get_cursors(self) -> List['Cursor']:
        """Return all Cursor children."""
        from pymetr.models import Cursor
        return [child for child in self.get_children() if isinstance(child, Cursor)]

    def create_marker(
        self, 
        x: float, 
        y: float, 
        label: str = "", 
        color: str = "yellow",
        size: int = 8,
        symbol: str = "o",
        visible: bool = True
    ) -> 'Marker':
        """
        Create and register a new Marker model.
        
        Args:
            x: X-coordinate
            y: Y-coordinate
            label: Marker label text; if not provided, a default is generated.
            color: Marker color
            size: Marker size in pixels
            symbol: Marker symbol ('o', 't', 's', 'd')
            visible: Visibility flag
            
        Returns:
            Marker: The created marker object
        """
        from pymetr.models import Marker
        if not label:
            # Auto-generate a label based on the current number of markers.
            current_markers = self.get_markers()  # Assumes this method exists.
            label = f"Marker {len(current_markers) + 1}"
        marker = self.state.create_model(
            Marker,
            x=x,
            y=y,
            label=label,
            color=color,
            size=size,
            symbol=symbol,
            visible=visible
        )
        self.add_child(marker)
        return marker

    def create_cursor(
        self,
        name: str = "",
        axis: str = "x",
        position: float = 0.0,
        color: str = "yellow",
        style: str = "solid",
        width: int = 1,
        visible: bool = True,
        **kwargs
    ) -> 'Cursor':
        """
        Create and register a new Cursor model.
        
        Args:
            name: The cursor name. If not provided, a default name will be auto-generated.
            axis: 'x' for vertical, 'y' for horizontal
            position: Position along the axis
            color: Cursor color
            style: Line style
            width: Line width
            visible: Visibility flag
            **kwargs: Additional cursor properties
            
        Returns:
            Cursor: The created cursor object
        """
        from pymetr.models import Cursor
        # Auto-generate a name if one is not provided.
        if not name:
            current_cursors = self.get_cursors()  # Assumes a method that returns a list of existing cursors.
            name = f"Cursor {len(current_cursors) + 1}"
        cursor = self.state.create_model(
            Cursor,
            name=name,
            axis=axis,
            position=position,
            color=color,
            style=style,
            width=width,
            visible=visible,
            **kwargs
        )
        self.add_child(cursor)
        return cursor

    def clear(self):
        """Remove all child items (traces, markers, cursors)."""
        children = self.get_children()
        for child in children:
            self.state.unlink_models(self.id, child.id)
            self.state.remove_model(child.id)
        logger.debug(f"Cleared all items from Plot {self.id} ('{self.title}').")