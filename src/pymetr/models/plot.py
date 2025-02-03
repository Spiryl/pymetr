# app/models/plot.py

from typing import Dict, List, Optional, Any
import numpy as np
from PySide6.QtCore import QObject, Signal, QTimer

from ..logging import logger
from .base import BaseModel
from .trace import Trace
from .marker import Marker
from .cursor import Cursor



class Plot(BaseModel, QObject):
    """
    Complete plot state including style, traces, markers, etc.
    
    Signals:
        trace_added(str, str): Emitted when a trace is added (plot_id, trace_id)
        trace_removed(str, str): Emitted when a trace is removed (plot_id, trace_id)
        marker_added(str, str): Emitted when a marker is added (plot_id, marker_id)
        marker_removed(str, str): Emitted when a marker is removed (plot_id, marker_id)
        cursor_added(str, str): Emitted when a cursor is added (plot_id, cursor_id)
        cursor_removed(str, str): Emitted when a cursor is removed (plot_id, cursor_id)
        limits_changed(str): Emitted when plot limits change (plot_id)
        style_changed(str, str, Any): Emitted when style property changes (plot_id, property_name, value)
        roi_changed(str, list): Emitted when ROI changes (plot_id, [start, end])
    """

    # Define signals
    trace_added = Signal(str, str)  # plot_id, trace_id
    trace_removed = Signal(str, str)  # plot_id, trace_id
    marker_added = Signal(str, str)  # plot_id, marker_id
    marker_removed = Signal(str, str)  # plot_id, marker_id
    cursor_added = Signal(str, str)  # plot_id, cursor_id
    cursor_removed = Signal(str, str)  # plot_id, cursor_id
    limits_changed = Signal(str)  # plot_id
    style_changed = Signal(str, str, Any)  # plot_id, property_name, value
    roi_changed = Signal(str, list)  # plot_id, [start, end]

    def __init__(self, name: str, id: Optional[str] = None):
        BaseModel.__init__(self, id)
        QObject.__init__(self)
        
        self.name = name
        self.traces: Dict[str, Trace] = {}
        self.markers: Dict[str, Marker] = {}
        self.cursors: Dict[str, Cursor] = {}
        
        # Plot properties
        self._auto_scale = True
        self._roi_visible = True
        self._roi = [0.0, 10.0]
        self._x_label = ""
        self._y_label = ""
        self._title = ""
        self._x_lim = [-1.0, 1.0]
        self._y_lim = [-1.0, 1.0]
        self._grid = True
        self._background_color = "#FFFFFF"

        # Debounce timer for limit updates
        self._limits_timer = QTimer()
        self._limits_timer.setInterval(200)  # 200ms debounce
        self._limits_timer.setSingleShot(True)
        self._limits_timer.timeout.connect(self._emit_limits_changed)
        self._limits_changed = False

        logger.debug(f"Created Plot '{self.name}' with ID: {self.id}")

    def _connect_trace_signals(self, trace: Trace):
        """Connect signals from a trace."""
        trace.data_changed.connect(lambda t_id: self._handle_trace_data_changed(t_id))
        trace.style_changed.connect(lambda t_id, prop, val: self._handle_trace_style_changed(t_id, prop, val))
        trace.visibility_changed.connect(lambda t_id, vis: self._handle_trace_visibility_changed(t_id, vis))
        trace.mode_changed.connect(lambda t_id, mode: self._handle_trace_mode_changed(t_id, mode))

    def _connect_marker_signals(self, marker: Marker):
        """Connect signals from a marker."""
        marker.position_changed.connect(lambda m_id, pos: self._handle_marker_position_changed(m_id, pos))
        marker.style_changed.connect(lambda m_id, prop, val: self._handle_marker_style_changed(m_id, prop, val))
        marker.visibility_changed.connect(lambda m_id, vis: self._handle_marker_visibility_changed(m_id, vis))

    def _connect_cursor_signals(self, cursor: Cursor):
        """Connect signals from a cursor."""
        cursor.position_changed.connect(lambda c_id, pos: self._handle_cursor_position_changed(c_id, pos))
        cursor.style_changed.connect(lambda c_id, prop, val: self._handle_cursor_style_changed(c_id, prop, val))
        cursor.visibility_changed.connect(lambda c_id, vis: self._handle_cursor_visibility_changed(c_id, vis))

    # Signal handlers
    def _handle_trace_data_changed(self, trace_id: str):
        """Handle trace data changes."""
        if self._auto_scale:
            self.update_from_data()

    def _handle_trace_style_changed(self, trace_id: str, prop: str, value: Any):
        """Handle trace style changes."""
        self.style_changed.emit(self.id, f"trace_{trace_id}_{prop}", value)

    def _handle_trace_visibility_changed(self, trace_id: str, visible: bool):
        """Handle trace visibility changes."""
        if self._auto_scale and not visible:
            self.update_from_data()

    def _handle_trace_mode_changed(self, trace_id: str, mode: str):
        """Handle trace mode changes."""
        self.style_changed.emit(self.id, f"trace_{trace_id}_mode", mode)

    def _handle_marker_position_changed(self, marker_id: str, position: float):
        """Handle marker position changes."""
        self.style_changed.emit(self.id, f"marker_{marker_id}_position", position)

    def _handle_marker_style_changed(self, marker_id: str, prop: str, value: Any):
        """Handle marker style changes."""
        self.style_changed.emit(self.id, f"marker_{marker_id}_{prop}", value)

    def _handle_marker_visibility_changed(self, marker_id: str, visible: bool):
        """Handle marker visibility changes."""
        self.style_changed.emit(self.id, f"marker_{marker_id}_visible", visible)

    def _handle_cursor_position_changed(self, cursor_id: str, position: float):
        """Handle cursor position changes."""
        self.style_changed.emit(self.id, f"cursor_{cursor_id}_position", position)

    def _handle_cursor_style_changed(self, cursor_id: str, prop: str, value: Any):
        """Handle cursor style changes."""
        self.style_changed.emit(self.id, f"cursor_{cursor_id}_{prop}", value)

    def _handle_cursor_visibility_changed(self, cursor_id: str, visible: bool):
        """Handle cursor visibility changes."""
        self.style_changed.emit(self.id, f"cursor_{cursor_id}_visible", visible)

    # Trace Management
    def add_trace(self, trace: Trace):
        """Add a new trace to the plot."""
        self.traces[trace.id] = trace
        self._connect_trace_signals(trace)
        logger.debug(f"Plot ID={self.id}: Added Trace ID={trace.id}")
        self.trace_added.emit(self.id, trace.id)
        if self._auto_scale:
            self.update_from_data()

    def remove_trace(self, trace_id: str):
        """Remove a trace from the plot."""
        if trace_id in self.traces:
            trace = self.traces.pop(trace_id)
            logger.debug(f"Plot ID={self.id}: Removed Trace ID={trace_id}")
            self.trace_removed.emit(self.id, trace_id)
            if self._auto_scale:
                self.update_from_data()

    def clear_traces(self):
        """Remove all traces from the plot."""
        trace_ids = list(self.traces.keys())
        self.traces.clear()
        for trace_id in trace_ids:
            self.trace_removed.emit(self.id, trace_id)
        logger.debug(f"Plot ID={self.id}: Cleared all traces")
        if self._auto_scale:
            self.update_from_data()

    def get_trace_by_name(self, name: str) -> Optional[Trace]:
        """Find a trace by its name rather than ID."""
        for trace in self.traces.values():
            if trace.name == name:
                return trace
        return None

    def set_trace(self, name: str, x_data=None, y_data=None, **style_kwargs) -> Trace:
        """Add or update a trace in the plot."""
        trace = self.get_trace_by_name(name)
        
        if trace is None:
            # Create new trace
            trace = Trace(
                plot_id=self.id,
                name=name,
                x_data=x_data,
                y_data=y_data,
                **style_kwargs
            )
            self.add_trace(trace)
        else:
            # Update existing trace
            if x_data is not None and y_data is not None:
                trace.set_data(x_data, y_data)
            for key, value in style_kwargs.items():
                if hasattr(trace, key):
                    setattr(trace, key, value)
        
        return trace

    # Marker Management
    def add_marker(self, marker: Marker):
        """Add a new marker to the plot."""
        self.markers[marker.id] = marker
        self._connect_marker_signals(marker)
        logger.debug(f"Plot ID={self.id}: Added Marker ID={marker.id}")
        self.marker_added.emit(self.id, marker.id)

    def remove_marker(self, marker_id: str):
        """Remove a marker from the plot."""
        if marker_id in self.markers:
            marker = self.markers.pop(marker_id)
            logger.debug(f"Plot ID={self.id}: Removed Marker ID={marker_id}")
            self.marker_removed.emit(self.id, marker_id)

    # Cursor Management
    def add_cursor(self, cursor: Cursor):
        """Add a new cursor to the plot."""
        self.cursors[cursor.id] = cursor
        self._connect_cursor_signals(cursor)
        logger.debug(f"Plot ID={self.id}: Added Cursor ID={cursor.id}")
        self.cursor_added.emit(self.id, cursor.id)

    def remove_cursor(self, cursor_id: str):
        """Remove a cursor from the plot."""
        if cursor_id in self.cursors:
            cursor = self.cursors.pop(cursor_id)
            logger.debug(f"Plot ID={self.id}: Removed Cursor ID={cursor_id}")
            self.cursor_removed.emit(self.id, cursor_id)

    # Plot Properties
    @property
    def x_label(self) -> str:
        return self._x_label

    @x_label.setter
    def x_label(self, value: str):
        self._x_label = value
        self.style_changed.emit(self.id, "x_label", value)

    @property
    def y_label(self) -> str:
        return self._y_label

    @y_label.setter
    def y_label(self, value: str):
        self._y_label = value
        self.style_changed.emit(self.id, "y_label", value)

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        self._title = value
        self.style_changed.emit(self.id, "title", value)

    @property
    def grid(self) -> bool:
        return self._grid

    @grid.setter
    def grid(self, value: bool):
        self._grid = value
        self.style_changed.emit(self.id, "grid", value)

    @property
    def background_color(self) -> str:
        return self._background_color

    @background_color.setter
    def background_color(self, value: str):
        self._background_color = value
        self.style_changed.emit(self.id, "background_color", value)

    @property
    def roi(self) -> List[float]:
        return self._roi

    @roi.setter
    def roi(self, value: List[float]):
        if not isinstance(value, list) or len(value) != 2:
            logger.error("ROI must be a list of two float values.")
            return
        self._roi = value
        self.roi_changed.emit(self.id, value)

    @property
    def roi_visible(self) -> bool:
        return self._roi_visible

    @roi_visible.setter
    def roi_visible(self, value: bool):
        self._roi_visible = value
        self.style_changed.emit(self.id, "roi_visible", value)

    @property
    def x_lim(self) -> List[float]:
        return self._x_lim

    @x_lim.setter
    def x_lim(self, value: List[float]):
        if not isinstance(value, list) or len(value) != 2:
            logger.error("x_lim must be a list of two float values.")
            return
        self._x_lim = value
        self._emit_limits_changed()

    @property
    def y_lim(self) -> List[float]:
        return self._y_lim

    @y_lim.setter
    def y_lim(self, value: List[float]):
        if not isinstance(value, list) or len(value) != 2:
            logger.error("y_lim must be a list of two float values.")
            return
        self._y_lim = value
        self._emit_limits_changed()

    def update_from_data(self):
        """Update plot limits from trace data."""
        if self._auto_scale:
            x_min = float('inf')
            x_max = float('-inf')
            y_min = float('inf')
            y_max = float('-inf')

            for trace in self.traces.values():
                if not trace.visible:
                    continue
                if len(trace.x_data) > 0:
                    x_min = min(x_min, np.min(trace.x_data))
                    x_max = max(x_max, np.max(trace.x_data))
                if len(trace.y_data) > 0:
                    y_min = min(y_min, np.min(trace.y_data))
                    y_max = max(y_max, np.max(trace.y_data))

            if x_min != float('inf'):
                padding = (x_max - x_min) * 0.05  # 5% padding
                self.x_lim = [x_min - padding, x_max + padding]

            if y_min != float('inf'):
                padding = (y_max - y_min) * 0.05  # 5% padding
                self.y_lim = [y_min - padding, y_max + padding]

    def _emit_limits_changed(self):
        """Emit limits changed signal."""
        if self._limits_changed:
            self._limits_changed = False
            self.limits_changed.emit(self.id)

# Serialization
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the Plot to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "traces": {tid: trace.to_dict() for tid, trace in self.traces.items()},
            "markers": {mid: marker.to_dict() for mid, marker in self.markers.items()},
            "cursors": {cid: cursor.to_dict() for cid, cursor in self.cursors.items()},
            "auto_scale": self._auto_scale,
            "roi": self._roi,
            "roi_visible": self._roi_visible,
            "x_label": self._x_label,
            "y_label": self._y_label,
            "title": self._title,
            "x_lim": self._x_lim,
            "y_lim": self._y_lim,
            "grid": self._grid,
            "background_color": self._background_color
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Plot':
        """Create a new Plot instance from a dictionary."""
        plot = cls(
            name=data.get('name', 'Unnamed Plot'),
            id=data.get('id')
        )
        
        # Recreate child objects
        for tid, t_data in data.get('traces', {}).items():
            trace = Trace.from_dict(t_data)
            plot.add_trace(trace)
            
        for mid, m_data in data.get('markers', {}).items():
            marker = Marker.from_dict(m_data)
            plot.add_marker(marker)
            
        for cid, c_data in data.get('cursors', {}).items():
            cursor = Cursor.from_dict(c_data)
            plot.add_cursor(cursor)

        # Set properties
        plot._auto_scale = data.get('auto_scale', True)
        plot._roi = data.get('roi', [0.0, 10.0])
        plot._roi_visible = data.get('roi_visible', True)
        plot._x_label = data.get('x_label', '')
        plot._y_label = data.get('y_label', '')
        plot._title = data.get('title', '')
        plot._x_lim = data.get('x_lim', [-1.0, 1.0])
        plot._y_lim = data.get('y_lim', [-1.0, 1.0])
        plot._grid = data.get('grid', True)
        plot._background_color = data.get('background_color', "#FFFFFF")

        logger.debug(f"Plot.from_dict: Deserialized Plot ID={plot.id}")
        return plot