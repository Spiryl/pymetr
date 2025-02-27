from typing import Any, Optional
from PySide6.QtCore import QObject
import pyqtgraph as pg
import numpy as np
from pymetr.core.logging import logger

class MarkerHandler(QObject):
    # MarkerHandler manages markers in the plot.
    # Public methods: register_marker, change_marker, link_marker, remove_marker.
    def __init__(self, plot_item: pg.PlotItem, state):
        super().__init__()
        self.plot_item = plot_item
        self.state = state  # For model lookups
        self.markers = {}  # Maps marker_id to dict with 'point' and 'label'
        self.marker_labels = {}  # For quick access to text items
        self.scatter_plot = pg.ScatterPlotItem()
        self.plot_item.addItem(self.scatter_plot)
        logger.debug("MarkerHandler initialized")

    def register_marker(self, marker_model) -> None:
        marker_id = marker_model.id
        if marker_id in self.markers:
            logger.warning(f"Marker {marker_id} already registered.")
            return

        bound_to_trace = False
        parent = self.state.get_parent(marker_id)
        if parent and parent.model_type == 'Trace':
            bound_to_trace = True
            logger.debug(f"Marker {marker_id} is bound to trace {parent.id}.")

        x = marker_model.get_property('x', 0.0)
        y = marker_model.get_property('y', 0.0)
        if bound_to_trace:
            y = self.interpolate(marker_model, x, parent)

        color = marker_model.get_property('color', '#FFFF00')
        size = marker_model.get_property('size', 8)
        symbol = marker_model.get_property('symbol', 'o')
        visible = marker_model.get_property('visible', True)
        label_text = marker_model.get_property('label', '')

        point = {
            'pos': (x, y),
            'brush': pg.mkBrush(color),
            'size': size,
            'symbol': symbol,
            'pen': pg.mkPen('w', width=0.5),
            'data': marker_id,  # For click handling
            'visible': visible,
            'bound_to_trace': bound_to_trace
        }

        label = pg.TextItem(
            text=label_text,
            color=color,
            anchor=(0.5, 1.0),
            fill=pg.mkBrush('#2A2A2A80')
        )
        label.setVisible(visible and bool(label_text))
        label.setPos(x, y)

        self.markers[marker_id] = {'point': point, 'label': label}
        self.marker_labels[marker_id] = label

        self.plot_item.addItem(label)
        self._update_scatter()
        logger.debug(f"Registered marker {marker_id} at ({x}, {y})")

    def change_marker(self, marker_id: str, prop: str, value) -> None:
        if marker_id not in self.markers:
            logger.error(f"Marker {marker_id} not found for update.")
            return

        marker = self.markers[marker_id]
        point = marker['point']
        label = marker['label']
        update_scatter = False

        if prop == 'x':
            _, old_y = point['pos']
            new_x = value
            new_y = old_y
            if point.get('bound_to_trace', False):
                marker_model = self.state.get_model(marker_id)
                parent = self.state.get_parent(marker_id)
                if marker_model and parent and parent.model_type == 'Trace':
                    new_y = self.interpolate(marker_model, new_x, parent)
            point['pos'] = (new_x, new_y)
            label.setPos(new_x, new_y)
            update_scatter = True

        elif prop == 'y':
            if not point.get('bound_to_trace', False):
                x, _ = point['pos']
                point['pos'] = (x, value)
                label.setPos(x, value)
                update_scatter = True

        elif prop == 'color':
            point['brush'] = pg.mkBrush(value)
            label.setColor(value)
            update_scatter = True

        elif prop == 'size':
            point['size'] = value
            update_scatter = True

        elif prop == 'symbol':
            point['symbol'] = value
            update_scatter = True

        # elif prop == 'visible':
        #     point['visible'] = bool(value)
        #     label.setVisible(bool(value) and bool(label.text))
        #     update_scatter = True

        elif prop == 'label':
            label.setText(value)
            label.setVisible(bool(value))

        else:
            logger.warning(f"Unhandled marker property: {prop}")

        if update_scatter:
            self._update_scatter()
            logger.debug(f"Marker {marker_id} updated: {prop}={value}")

    def link_marker(self, marker_model) -> None:
        marker_id = marker_model.id
        parent = self.state.get_parent(marker_id)
        if parent and parent.model_type == 'Trace':
            if marker_id in self.markers:
                self.markers[marker_id]['point']['bound_to_trace'] = True
                x, _ = self.markers[marker_id]['point']['pos']
                new_y = self.interpolate(marker_model, x, parent)
                self.markers[marker_id]['point']['pos'] = (x, new_y)
                self.marker_labels[marker_id].setPos(x, new_y)
                self._update_scatter()
                logger.debug(f"Marker {marker_id} linked to trace {parent.id} and updated.")
        else:
            if marker_id in self.markers:
                self.markers[marker_id]['point']['bound_to_trace'] = False
                logger.debug(f"Marker {marker_id} is no longer bound to a trace.")

    def remove_marker(self, marker_id: str) -> None:
        if marker_id in self.marker_labels:
            label = self.marker_labels[marker_id]
            if label.scene():
                self.plot_item.removeItem(label)
            del self.marker_labels[marker_id]
        if marker_id in self.markers:
            del self.markers[marker_id]
            self._update_scatter()
            logger.debug(f"Marker {marker_id} removed.")

    def interpolate(self, marker_model, x: float, parent_trace) -> float:
        trace_data = parent_trace.data
        if trace_data and len(trace_data) == 2:
            x_data, y_data = trace_data
            if len(x_data) == 0:
                return 0.0
            mode = marker_model.get_property('interpolation_mode', 'linear')
            if len(x_data) > 1:
                if mode == 'nearest':
                    idx = np.abs(np.array(x_data) - x).argmin()
                    return y_data[idx]
                else:
                    idx = np.searchsorted(x_data, x)
                    if idx == 0:
                        return y_data[0]
                    elif idx >= len(x_data):
                        return y_data[-1]
                    else:
                        x0, x1 = x_data[idx-1], x_data[idx]
                        y0, y1 = y_data[idx-1], y_data[idx]
                        if x1 == x0:
                            return y0
                        ratio = (x - x0) / (x1 - x0)
                        return y0 + ratio * (y1 - y0)
            else:
                return y_data[0]
        return 0.0

    def _update_scatter(self) -> None:
        points = []
        for data in self.markers.values():
            point = data['point']
            # Check if the marker is visible; if not, skip it
            if not point.get('visible', True):
                continue
            # Create a shallow copy to avoid modifying the original marker data
            point_copy = point.copy()
            # Remove keys not supported by ScatterPlotItem
            point_copy.pop('visible', None)
            point_copy.pop('bound_to_trace', None)
            points.append(point_copy)
        self.scatter_plot.setData(points)

    def update_label_positions(self) -> None:
        """Update all label positions (e.g., after plot range changes)."""
        try:
            for marker_id, marker in self.markers.items():
                if marker_id in self.marker_labels:
                    pos = marker['point']['pos']
                    self.marker_labels[marker_id].setPos(*pos)
        except Exception as e:
            logger.error(f"Error updating label positions: {e}")

    def get_marker_at_pos(self, pos) -> Optional[str]:
        """
        Get marker ID at the given position.
        """
        try:
            points = self.scatter_plot.pointsAt(pos)
            if points:
                return points[0].data()
            return None
        except Exception as e:
            logger.error(f"Error getting marker at position: {e}")
            return None
        
    def handle_property_change(self, model_id: str, model_type: str, prop: str, value: Any) -> None:
        """
        Handle marker property changes from the state.
        """
        if model_id not in self.markers:
            logger.debug(f"[MarkerHandler] Marker {model_id} not found.")
            return

        logger.debug(f"[MarkerHandler] Updating marker {model_id}: prop={prop}, value={value}")
        self._apply_marker_update(model_id, prop, value)