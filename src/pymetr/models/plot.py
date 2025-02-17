from typing import Optional, List, Dict, Any, Tuple
import numpy as np
from pymetr.models.base import BaseModel
from pymetr.core.logging import logger

class Plot(BaseModel):
    """
    A plot container with comprehensive plotting properties.
    
    Properties:
        - title: Plot title
        - x_label/y_label: Axis labels
        - x_unit/y_unit: Axis units
        - grid_enabled: Show/hide grid
        - legend_enabled: Show/hide legend
        - x_lim/y_lim: Axis limits as (min, max)
        - x_log/y_log: Logarithmic scaling
        - x_inverted/y_inverted: Axis direction
        - x_ticks/y_ticks: Custom tick positions
        - x_tick_labels/y_tick_labels: Custom tick labels
        - background_color: Plot background color
        - foreground_color: Text and axis color
        - grid_color: Grid line color
        - grid_alpha: Grid transparency
        - legend_position: Legend placement ('right', 'top', 'bottom', 'left')
        
    - ROI Properties:
        - roi_visible: Show/hide ROI panel
    """

    def __init__(self, title: str, model_id: Optional[str] = None):
        super().__init__(model_id=model_id, name=title)
        
        # Initialize all properties with defaults
        self._init_properties(title)

    def _init_properties(self, title: str):
        """Initialize basic plot properties."""
        self.set_property("title", title)
        self.set_property("x_label", "")
        self.set_property("y_label", "")
        self.set_property("x_unit", "")
        self.set_property("y_unit", "")
        self.set_property("grid_enabled", True)
        self.set_property("legend_enabled", True)
        self.set_property("roi_visible", True)
        # self.set_property("x_lim", None)  # (min, max) or None for auto
        # self.set_property("y_lim", None)
        # self.set_property("x_log", False)
        # self.set_property("y_log", False)
        # self.set_property("x_inverted", False)
        # self.set_property("y_inverted", False)
        # self.set_property("x_ticks", None)  # List of positions or None for auto
        # self.set_property("y_ticks", None)
        # self.set_property("x_tick_labels", None)  # List of labels or None for auto
        # self.set_property("y_tick_labels", None)
        # self.set_property("background_color", "#1E1E1E")  # Dark theme default
        # self.set_property("foreground_color", "#FFFFFF")  # White text/axes
        # self.set_property("grid_color", "#404040")       # Dark gray grid
        # self.set_property("grid_alpha", 0.3)
        # self.set_property("legend_position", "right")    # 'right', 'top', 'bottom', 'left'

    # Property accessors with proper typing
    @property
    def title(self) -> str:
        return self.get_property("title")

    @title.setter
    def title(self, value: str):
        self.set_property("title", value)

    @property
    def x_lim(self) -> Optional[Tuple[float, float]]:
        return self.get_property("x_lim")

    @x_lim.setter
    def x_lim(self, value: Optional[Tuple[float, float]]):
        if value is not None:
            if not isinstance(value, (tuple, list)) or len(value) != 2:
                raise ValueError("x_lim must be a tuple/list of (min, max) or None")
            if not all(isinstance(v, (int, float)) for v in value):
                raise ValueError("x_lim values must be numbers")
        self.set_property("x_lim", value)

    @property
    def y_lim(self) -> Optional[Tuple[float, float]]:
        return self.get_property("y_lim")

    @y_lim.setter
    def y_lim(self, value: Optional[Tuple[float, float]]):
        if value is not None:
            if not isinstance(value, (tuple, list)) or len(value) != 2:
                raise ValueError("y_lim must be a tuple/list of (min, max) or None")
            if not all(isinstance(v, (int, float)) for v in value):
                raise ValueError("y_lim values must be numbers")
        self.set_property("y_lim", value)

    @property
    def x_log(self) -> bool:
        return self.get_property("x_log", False)

    @x_log.setter 
    def x_log(self, value: bool):
        self.set_property("x_log", value)

    @property
    def y_log(self) -> bool:
        return self.get_property("y_log", False)

    @y_log.setter
    def y_log(self, value: bool):
        self.set_property("y_log", value)

    @property
    def grid_enabled(self) -> bool:
        return self.get_property("grid_enabled", True)

    @grid_enabled.setter
    def grid_enabled(self, value: bool):
        self.set_property("grid_enabled", value)

    @property
    def legend_enabled(self) -> bool:
        return self.get_property("legend_enabled", True)

    @legend_enabled.setter
    def legend_enabled(self, value: bool):
        self.set_property("legend_enabled", value)

    @property
    def roi_visible(self) -> bool:
        return self.get_property("roi_visible", True)

    @roi_visible.setter
    def roi_visible(self, value: bool):
        self.set_property("roi_visible", value)

    def create_trace(self, x_data: np.ndarray, y_data: np.ndarray, name: str = "", **kwargs):
        """Create and register a new Trace model."""
        from pymetr.models import Trace
        trace = self.state.create_model(
            Trace,
            x_data=x_data,
            y_data=y_data,
            name=name,
            **kwargs
        )
        self.add_child(trace)
        return trace

    def create_marker(
        self, 
        x: float, 
        y: float, 
        label: str = "", 
        color: str = "yellow",
        **kwargs
    ):
        """Create and register a new Marker model."""
        from pymetr.models import Marker
        marker = self.state.create_model(
            Marker,
            x=x,
            y=y,
            label=label,
            color=color,
            **kwargs
        )
        self.add_child(marker)
        return marker

    def create_cursor(
        self, 
        axis: str = "x",
        position: float = 0.0,
        color: str = "yellow",
        **kwargs
    ):
        """Create and register a new Cursor model."""
        from pymetr.models import Cursor
        cursor = self.state.create_model(
            Cursor,
            axis=axis,
            position=position,
            color=color,
            **kwargs
        )
        self.add_child(cursor)
        return cursor

    def get_traces(self) -> list:
        """Return all Trace children."""
        from pymetr.models import Trace
        return [child for child in self.get_children() if isinstance(child, Trace)]

    def get_markers(self) -> list:
        """Return all Marker children."""
        from pymetr.models import Marker
        return [child for child in self.get_children() if isinstance(child, Marker)]

    def get_cursors(self) -> list:
        """Return all Cursor children."""
        from pymetr.models import Cursor
        return [child for child in self.get_children() if isinstance(child, Cursor)]

    def clear(self):
        """Remove all child items (traces, markers, cursors)."""
        children = self.get_children()
        for child in children:
            self.state.unlink_models(self.id, child.id)
            self.state.remove_model(child.id)
        logger.debug(f"Cleared all items from Plot {self.id} ('{self.title}').")

    def add(self, item: BaseModel) -> None:
        """
        Add an existing Trace, Marker, or Cursor to the plot.
        
        Args:
            item: A Trace, Marker, or Cursor instance
            
        Raises:
            TypeError: If item is not a valid plot item type
            ValueError: If item is already added to another plot
        """
        from pymetr.models import Trace, Marker, Cursor
        
        if not isinstance(item, (Trace, Marker, Cursor)):
            raise TypeError(f"Can only add Trace, Marker, or Cursor objects, got {type(item).__name__}")
        
        # Check if item already has a parent
        current_parent = self.state.get_parent(item.id)
        if current_parent:
            raise ValueError(f"Item {item.id} is already added to plot {current_parent.id}")
            
        self.add_child(item)
        logger.debug(f"Added {type(item).__name__} {item.id} to Plot {self.id}")

    def set_trace(
        self,
        trace_name: str,
        x_data: np.ndarray,
        y_data: np.ndarray,
        mode: str = "Group",
        color: Optional[str] = "#ffffff",  # Default white
        style: str = "solid", 
        width: int = 1,
        marker_style: str = "",
        visible: bool = True,
        opacity: float = 1.0,
    ):
        """
        A single-entry method to create or update a trace by name.
        Handles arbitrary data updates efficiently.
        """
        from pymetr.models import Trace

        # Look for an existing trace with this name
        existing_trace = None
        for t in self.get_traces():
            if t.name == trace_name:
                existing_trace = t
                break

        if existing_trace is None:
            # Create a new trace with all properties set
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
        else:
            # Always update data - let Trace handle optimization
            existing_trace.update_data(x_data, y_data)

            # Only update style properties if they changed
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