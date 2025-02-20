from PySide6.QtCore import QObject
import pyqtgraph as pg
import numpy as np
from typing import Dict, Any, Optional
from pymetr.core.logging import logger

class MarkerHandler(QObject):
    """
    Enhanced marker management with optimized scatter plot handling and
    efficient label updates. Uses a single ScatterPlotItem for better performance.
    """

    def __init__(self, plot_item: pg.PlotItem, state):
        """
        Initialize the MarkerHandler.

        Args:
            plot_item: Main plot for marker overlays.
            state: The ApplicationState instance for model lookups.
        """
        super().__init__()
        self.plot_item = plot_item
        self.state = state  # Save the state for all lookups
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
            marker_model: Marker model containing position and style properties.
        """
        marker_id = marker_model.id
        if marker_id in self.markers:
            logger.warning(f"Marker {marker_id} already exists")
            return

        try:
            # Extract main properties
            x = marker_model.get_property('x', 0.0)
            y = marker_model.get_property('y', 0.0)
            color = marker_model.get_property('color', '#FFFF00')
            size = marker_model.get_property('size', 8)
            symbol = marker_model.get_property('symbol', 'o')
            visible = marker_model.get_property('visible', True)
            label_text = marker_model.get_property('label', '')
            
            # Get uncertainty properties
            uncertainty_visible = marker_model.get_property('uncertainty_visible', False)
            uncertainty_upper = marker_model.get_property('uncertainty_upper', 0.0)
            uncertainty_lower = marker_model.get_property('uncertainty_lower', 0.0)

            # Create point data for scatter plot
            point = {
                'pos': (x, y),
                'brush': pg.mkBrush(color),
                'size': size,
                'symbol': symbol,
                'pen': pg.mkPen('w', width=0.5),
                'data': marker_id,  # Store ID for click handling
                'visible': visible,
                'uncertainty': {
                    'visible': uncertainty_visible,
                    'upper': uncertainty_upper,
                    'lower': uncertainty_lower
                }
            }

            # Create and style label
            label = pg.TextItem(
                text=label_text,
                color=color,
                anchor=(0.5, 1.0),
                fill=pg.mkBrush('#2A2A2A')
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

    def _apply_marker_update(self, marker_id: str, prop: str, value: Any) -> None:
        """Apply a single property update to a marker."""
        try:
            marker = self.markers[marker_id]
            point = marker['point']
            label = marker['label']

            update_scatter = False
            
            # Handle top-level properties
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
                update_scatter = True
                
            elif prop == "size":
                point['size'] = value
                update_scatter = True
                
            elif prop == "symbol":
                point['symbol'] = value
                update_scatter = True
                
            elif prop == "label":
                label.setText(value)
                label.setVisible(bool(value) and point['visible'])
                
            elif prop == "visible":
                point['visible'] = bool(value)
                label.setVisible(bool(value) and bool(label.text()))
                update_scatter = True

            elif prop == "interpolation_mode":
                # Store interpolation mode if needed
                point['interpolation_mode'] = value
                
            # Handle uncertainty properties
            elif prop == "uncertainty_visible":
                point['uncertainty']['visible'] = bool(value)
                update_scatter = True
                
            elif prop == "uncertainty_upper":
                point['uncertainty']['upper'] = value
                update_scatter = True
                
            elif prop == "uncertainty_lower":
                point['uncertainty']['lower'] = value
                update_scatter = True
                
            else:
                logger.warning(f"Unhandled marker property: {prop}")
                return

            if update_scatter:
                self._update_scatter()

        except Exception as e:
            logger.error(f"Error updating marker {marker_id}.{prop}: {e}")

    def _handle_parameter_change(self, param, value):
        """Handle parameter changes with trace binding awareness."""
        try:
            # Get current model
            model = self.state.get_model(self.model_id)
            if not model:
                return
            
            # Special handling for y-value when trace bound
            if param.name() == 'y' and model.bound_to_trace:
                return  # Ignore y changes when bound to trace
            
            # Handle uncertainty visibility changes
            if param.name() == 'uncertainty_visible':
                uncertainty_group = self.child('Uncertainty')
                if uncertainty_group:
                    for child in uncertainty_group.children():
                        if child.name() != 'uncertainty_visible':
                            child.setOpts(visible=value)
            
            # Get the full property name for parameter
            prop_name = param.name()
            
            # Update the model
            self.set_model_property(prop_name, value)
            
        except Exception as e:
            logger.error(f"Error handling parameter change: {e}")

    def update_marker(self, marker_id: str, prop: str, value: Any) -> None:
        """
        Update a marker property with batch support.

        Args:
            marker_id: ID of the marker.
            prop: Property name.
            value: New value.
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
            marker_id: ID of the marker to remove.
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
                label.setColor(value)  # Update text color
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
                is_visible = bool(value)
                old_color = point['brush'].color()
                old_color.setAlpha(255 if is_visible else 0)
                point['brush'] = pg.mkBrush(old_color)
                label.setVisible(is_visible and bool(label.text()))
                update_scatter = True
                
            else:
                logger.warning(f"Unhandled marker property: {prop}")
                return

            if update_scatter:
                self._update_scatter()

        except Exception as e:
            logger.error(f"Error updating marker {marker_id}.{prop}: {e}")


    def _update_scatter(self) -> None:
        """Update the ScatterPlotItem with current markers."""
        try:
            points = []
            for marker in self.markers.values():
                point = marker['point']
                if point.get('visible', True):  # Only include visible points
                    # Create a clean point dict without extra properties
                    scatter_point = {
                        'pos': point['pos'],
                        'brush': point['brush'],
                        'size': point['size'],
                        'symbol': point['symbol'],
                        'pen': point['pen'],
                        'data': point['data']
                    }
                    points.append(scatter_point)
                    
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
        Handle marker property changes from the parameter tree.
        Handles both top-level and uncertainty group properties.
        """
        if model_id not in self.markers:
            logger.debug(f"[MarkerHandler] Marker {model_id} not found.")
            return

        logger.debug(f"[MarkerHandler] Updating marker {model_id}: prop={prop}, value={value}")
        try:
            # Check if property is in uncertainty group
            if prop.startswith('uncertainty_'):
                self._apply_marker_update(model_id, prop, value)
            else:
                # Handle top-level property
                self._apply_marker_update(model_id, prop, value)
        except Exception as e:
            logger.error(f"Error updating marker {model_id}.{prop}: {e}")
