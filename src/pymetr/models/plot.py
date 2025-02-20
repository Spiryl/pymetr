from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING, Union
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
        super().__init__(model_type='Plot', model_id=model_id, name=title)
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
        self.set_property("roi_visible", False)

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

    def add(self, item: Union['BaseModel', List['BaseModel']]) -> None:
        """
        Add an existing Trace, Marker, or Cursor to the plot.
        Accepts a single model or a list of models.
        If a model already has a parent, it will be moved to this plot.
        
        Args:
            item: A Trace, Marker, or Cursor instance or a list of such instances
            
        Raises:
            TypeError: If any item is not a valid plot item type.
        """
        from pymetr.models import Trace, Marker, Cursor

        # Wrap single model into a list for uniform processing
        items = item if isinstance(item, list) else [item]
        
        for model in items:
            if not isinstance(model, (Trace, Marker, Cursor)):
                raise TypeError(
                    f"Can only add Trace, Marker, or Cursor objects, got {type(model).__name__}"
                )
            # Unlink from the current parent if it exists
            current_parent = self.state.get_parent(model.id)
            if current_parent:
                self.state.unlink_models(current_parent.id, model.id)
                
            # Add the model as a child of this plot
            self.add_child(model)
            logger.debug(f"Added {type(model).__name__} {model.id} to Plot {self.id}")


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

    def set_trace(
        self,
        trace_name: str,
        x_data: np.ndarray,
        y_data: np.ndarray,
        mode: Optional[str] = None,
        color: Optional[str] = None,
        style: Optional[str] = None,
        width: Optional[int] = None,
        marker_style: Optional[str] = None,
        visible: Optional[bool] = None,
        opacity: Optional[float] = None,
    ) -> 'Trace':
        """
        Create or update a trace by name. Only updates properties that are explicitly passed.
        
        Args:
            trace_name: Name to identify the trace
            x_data: X-axis data points
            y_data: Y-axis data points
            mode: Optional - 'Group' or 'Isolate'
            color: Optional - Trace color (hex or name)
            style: Optional - Line style ('solid', 'dash', 'dot', etc.)
            width: Optional - Line width
            marker_style: Optional - Point marker style
            visible: Optional - Visibility flag
            opacity: Optional - Opacity value (0.0 to 1.0)
            
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
            # For new traces, collect only the non-None properties
            props = {
                'x_data': x_data,
                'y_data': y_data,
                'name': trace_name
            }
            
            # Only add optional properties if they were explicitly set
            optional_props = {
                'mode': mode,
                'color': color,
                'style': style,
                'width': width,
                'marker_style': marker_style,
                'visible': visible,
                'opacity': opacity
            }
            
            # Add only non-None optional properties
            props.update({k: v for k, v in optional_props.items() if v is not None})
            
            # Create new trace with collected properties
            logger.debug(f"Creating new trace '{trace_name}' in Plot '{self.title}'.")
            new_trace = self.state.create_model(Trace, **props)
            self.add_child(new_trace)
            return new_trace
        else:
            # Always update data
            existing_trace.data = (x_data, y_data)

            # Only update properties that were explicitly passed (not None)
            if mode is not None:
                existing_trace.set_property('mode', mode)
            if color is not None:
                existing_trace.set_property('color', color)
            if style is not None:
                existing_trace.set_property('style', style)
            if width is not None:
                existing_trace.set_property('width', width)
            if marker_style is not None:
                existing_trace.set_property('marker_style', marker_style)
            if visible is not None:
                existing_trace.set_property('visible', visible)
            if opacity is not None:
                existing_trace.set_property('opacity', opacity)
                
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
        name: str = "",
        **kwargs
    ) -> 'Marker':
        """
        Create and register a new Marker model.
        
        Args:
            x: X-coordinate
            y: Y-coordinate
            name: Optional marker name (auto-generated if empty)
            **kwargs: Additional marker properties
                Defaults handled by Marker class:
                - color: "yellow"
                - size: 8
                - symbol: "o"
                - visible: True
        """
        from pymetr.models import Marker
        if not name:
            current_markers = self.get_markers()
            name = f"Marker {len(current_markers) + 1}"
            
        marker = self.state.create_model(
            Marker,
            x=x,
            y=y,
            name=name,
            **kwargs
        )
        self.add_child(marker)
        return marker

    def set_marker(
        self,
        name: str,
        x: float,
        y: float,
        color: Optional[str] = None,
        size: Optional[int] = None,
        symbol: Optional[str] = None,
        visible: Optional[bool] = None
    ) -> 'Marker':
        """
        Create or update a marker by name.
        Only updates properties that are explicitly passed.
        """
        existing_marker = None
        for marker in self.get_markers():
            if marker.name == name:
                existing_marker = marker
                break

        if existing_marker is None:
            # For new markers, only include non-None properties
            props = {'x': x, 'y': y}
            if color is not None: props['color'] = color
            if size is not None: props['size'] = size
            if symbol is not None: props['symbol'] = symbol
            if visible is not None: props['visible'] = visible
            
            return self.create_marker(name=name, **props)
        else:
            # Always update position
            existing_marker.x = x
            existing_marker.y = y
            
            # Only update properties that were explicitly passed
            if color is not None:
                existing_marker.color = color
            if size is not None:
                existing_marker.size = size
            if symbol is not None:
                existing_marker.symbol = symbol
            if visible is not None:
                existing_marker.visible = visible
            
            return existing_marker

    def create_cursor(
        self,
        position: float,
        axis: str = "x",
        name: str = "",
        **kwargs
    ) -> 'Cursor':
        """
        Create and register a new Cursor model.
        
        Args:
            position: Position along the axis
            axis: 'x' for vertical, 'y' for horizontal
            name: Optional cursor name (auto-generated if empty)
            **kwargs: Additional cursor properties
                Defaults handled by Cursor class:
                - color: "yellow"
                - style: "solid"
                - width: 1
                - visible: True
        """
        from pymetr.models import Cursor
        if not name:
            current_cursors = self.get_cursors()
            name = f"Cursor {len(current_cursors) + 1}"
            
        cursor = self.state.create_model(
            Cursor,
            position=position,
            axis=axis,
            name=name,
            **kwargs
        )
        self.add_child(cursor)
        return cursor

    def set_cursor(
        self,
        name: str,
        position: float,
        axis: Optional[str] = None,
        color: Optional[str] = None,
        style: Optional[str] = None,
        width: Optional[int] = None,
        visible: Optional[bool] = None
    ) -> 'Cursor':
        """
        Create or update a cursor by name.
        Only updates properties that are explicitly passed.
        """
        existing_cursor = None
        for cursor in self.get_cursors():
            if cursor.name == name:
                existing_cursor = cursor
                break

        if existing_cursor is None:
            # For new cursors, only include non-None properties
            props = {'position': position}
            if axis is not None: props['axis'] = axis
            if color is not None: props['color'] = color
            if style is not None: props['style'] = style
            if width is not None: props['width'] = width
            if visible is not None: props['visible'] = visible
            
            return self.create_cursor(name=name, **props)
        else:
            # Always update position
            existing_cursor.position = position
            
            # Only update properties that were explicitly passed
            if axis is not None:
                existing_cursor.axis = axis
            if color is not None:
                existing_cursor.color = color
            if style is not None:
                existing_cursor.style = style
            if width is not None:
                existing_cursor.width = width
            if visible is not None:
                existing_cursor.visible = visible
            
            return existing_cursor
    
    def clear(self):
        """Remove all child items (traces, markers, cursors)."""
        children = self.get_children()
        for child in children:
            self.state.unlink_models(self.id, child.id)
            self.state.remove_model(child.id)
        logger.debug(f"Cleared all items from Plot {self.id} ('{self.title}').")