# marker_handler.py
from PySide6.QtCore import QObject
import pyqtgraph as pg
import numpy as np
from typing import Dict, Any, List, Optional
from pymetr.core.logging import logger

class MarkerHandler(QObject):
    """
    Enhanced marker management with optimized scatter plot handling and
    efficient label updates. Uses a single ScatterPlotItem for better performance.
    """

    def __init__(self, plot_item: pg.PlotItem):
        """
        Initialize the MarkerHandler.

        Args:
            plot_item: Main plot for marker overlays
        """
        super().__init__()
        self.plot_item = plot_item

        # Main storage
        self.markers: Dict[str, Dict] = {}  # {marker_id: {point: dict, label: pg.TextItem}}
        self.marker_labels: Dict[str, pg.TextItem] = {}
        
        # Batch update support
        self.batch_mode = False
        self.pending_updates: Dict[str, Dict[str, Any]] = {}
        
        # Use a single ScatterPlotItem for all markers
        self.scatter_plot = pg.ScatterPlotItem()
        self.plot_item.addItem(self.scatter_plot)
        
        logger.debug("MarkerHandler initialized")

    def begin_update(self) -> None:
        """Enable batch update mode."""
        self.batch_mode = True
        self.pending_updates.clear()

    def end_update(self) -> None:
        """Apply pending updates and exit batch mode."""
        self.batch_mode = False
        self._apply_pending_updates()

    def add_marker(self, marker_model) -> None:
        """
        Add a new marker from a model.

        Args:
            marker_model: Marker model containing position and style properties
        """
        marker_id = marker_model.id
        if marker_id in self.markers:
            logger.warning(f"Marker {marker_id} already exists")
            return

        try:
            # Extract marker properties
            x = marker_model.get_property('x', 0.0)
            y = marker_model.get_property('y', 0.0)
            color = marker_model.get_property('color', '#FFFF00')
            size = marker_model.get_property('size', 8)
            symbol = marker_model.get_property('symbol', 'o')
            visible = marker_model.get_property('visible', True)

            # Create point data for scatter plot
            point = {
                'pos': (x, y),
                'brush': pg.mkBrush(color),
                'size': size,
                'symbol': symbol,
                'pen': pg.mkPen('w', width=0.5),
                'data': marker_id  # Store ID for click handling
            }

            # Create and style label
            label_text = marker_model.get_property('label', '')
            label = pg.TextItem(
                text=label_text,
                color=color,
                anchor=(0.5, 1.0),
                border=pg.mkPen(color=color, width=1),
                fill=pg.mkBrush(color='#2A2A2A')
            )
            label.setVisible(visible and bool(label_text))
            label.setPos(x, y)

            # Store marker components
            self.markers[marker_id] = {'point': point, 'label': label}
            self.marker_labels[marker_id] = label
            
            # Add label to plot
            self.plot_item.addItem(label)
            
            # Update scatter plot
            self._update_scatter()
            
            logger.debug(f"Added marker {marker_id} at ({x}, {y})")

        except Exception as e:
            logger.error(f"Error adding marker {marker_id}: {e}")
            self.remove_marker(marker_id)

    def update_marker(self, marker_id: str, prop: str, value: Any) -> None:
        """
        Update a marker property with batch support.

        Args:
            marker_id: ID of the marker
            prop: Property name
            value: New value
        """
        if marker_id not in self.markers:
            logger.error(f"Marker {marker_id} not found")
            return

        if self.batch_mode:
            if marker_id not in self.pending_updates:
                self.pending_updates[marker_id] = {}
            self.pending_updates[marker_id][prop] = value
        else:
            self._apply_marker_update(marker_id, prop, value)

    def remove_marker(self, marker_id: str) -> None:
        """
        Remove a marker and clean up its resources.

        Args:
            marker_id: ID of the marker to remove
        """
        if marker_id in self.markers:
            # Remove label
            if marker_id in self.marker_labels:
                self.plot_item.removeItem(self.marker_labels[marker_id])
                del self.marker_labels[marker_id]

            # Remove marker data
            del self.markers[marker_id]
            
            # Update scatter plot
            self._update_scatter()
            
            logger.debug(f"Removed marker {marker_id}")

    def clear_all(self) -> None:
        """Remove all markers and clean up."""
        # Remove all labels
        for marker_id in list(self.marker_labels.keys()):
            self.plot_item.removeItem(self.marker_labels[marker_id])
        
        # Clear storage
        self.markers.clear()
        self.marker_labels.clear()
        
        # Clear scatter plot
        self.scatter_plot.clear()
        
        logger.debug("All markers cleared")

    def _apply_pending_updates(self) -> None:
        """Apply all pending marker updates."""
        for marker_id, updates in self.pending_updates.items():
            for prop, value in updates.items():
                self._apply_marker_update(marker_id, prop, value)
        self.pending_updates.clear()

    def _apply_marker_update(self, marker_id: str, prop: str, value: Any) -> None:
        """Apply a single property update to a marker."""
        try:
            marker = self.markers[marker_id]
            point = marker['point']
            label = marker['label']

            update_scatter = False
            
            if prop in ('x', 'y'):
                # Update position
                x, y = point['pos']
                new_pos = (value, y) if prop == 'x' else (x, value)
                point['pos'] = new_pos
                label.setPos(*new_pos)
                update_scatter = True
                
            elif prop == "color":
                # Update colors
                point['brush'] = pg.mkBrush(value)
                label.setColor(value)
                label.setBorder(pg.mkPen(color=value, width=1))
                update_scatter = True
                
            elif prop == "size":
                point['size'] = value
                update_scatter = True
                
            elif prop == "symbol":
                point['symbol'] = value
                update_scatter = True
                
            elif prop == "label":
                label.setText(value)
                label.setVisible(bool(value) and point.get('visible', True))
                
            elif prop == "visible":
                # Instead of storing 'visible' in the dict, just use alpha
                is_visible = bool(value)
                old_color = point['brush'].color()
                old_color.setAlpha(255 if is_visible else 0)
                point['brush'] = pg.mkBrush(old_color)

                label.setVisible(is_visible and bool(label.textItem.toPlainText()))
                update_scatter = True
                
            else:
                logger.warning(f"Unhandled marker property: {prop}")
                return

            # Update scatter plot if needed
            if update_scatter:
                self._update_scatter()

        except Exception as e:
            logger.error(f"Error updating marker {marker_id}.{prop}: {e}")

    def _update_scatter(self) -> None:
        """Update the ScatterPlotItem with current markers."""
        try:
            # Collect visible points
            points = [
                marker['point'] for marker in self.markers.values()
                if marker['point'].get('visible', True)
            ]
            
            # Update scatter plot
            self.scatter_plot.setData(points)
            
        except Exception as e:
            logger.error(f"Error updating scatter plot: {e}")

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

        Args:
            pos: (x, y) position to check

        Returns:
            Marker ID if found, None otherwise
        """
        try:
            # Use scatter plot's built-in point detection
            points = self.scatter_plot.pointsAt(pos)
            if points:
                # Return the first marker's ID (stored in data)
                return points[0].data()
            return None
        except Exception as e:
            logger.error(f"Error getting marker at position: {e}")
            return None