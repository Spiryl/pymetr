from PySide6.QtCore import QObject, Qt
import pyqtgraph as pg
import numpy as np
from typing import Dict, Any, Tuple, List
from pymetr.core.logging import logger

class TraceHandler(QObject):
    """
    High-performance trace handler optimized for real-time visualization.
    """
    
    def __init__(self, plot_item: pg.PlotItem, plot_layout: pg.GraphicsLayoutWidget):
        super().__init__()
        self.plot_item = plot_item
        self.plot_layout = plot_layout
        
        # Store tuple: (trace_model, curve)
        self.traces: Dict[str, Tuple[Any, pg.PlotDataItem]] = {}
        
        # Store isolated axes and view boxes separately
        self.isolated_axes: Dict[str, pg.AxisItem] = {}
        self.isolated_view_boxes: Dict[str, pg.ViewBox] = {}
        
        # Keep track of column positions for isolated axes
        self.axis_columns: Dict[str, int] = {}
        
        # Initialize autorange by default for main viewbox
        self.plot_item.enableAutoRange()
        
        logger.debug("TraceHandler initialized with autorange enabled")

    def register_trace(self, trace_model) -> None:
        """Add a new trace from model."""
        trace_id = trace_model.id
        if trace_id in self.traces:
            logger.warning(f"Trace {trace_id} already exists, updating instead")
            self.handle_property_change(trace_id, 'Trace', 'data', trace_model.data)
            return

        try:
            # Create curve with initial properties
            pen = pg.mkPen(
                color=trace_model.get_property('color', '#ffffff'),
                width=trace_model.get_property('width', 1),
                style=self._get_qt_line_style(trace_model.get_property('style', 'solid'))
            )

            curve = pg.PlotDataItem(
                trace_model.x_data,
                trace_model.y_data,
                pen=pen,
                name=trace_model.get_property('name', ''),
                connect='finite'
            )

            # Store both model and curve
            self.traces[trace_id] = (trace_model, curve)
            
            # Handle isolation mode
            mode = trace_model.get_property('mode', 'Group')
            logger.debug(f"Adding trace {trace_id} in {mode} mode")
            
            if mode == "Isolate":
                self._setup_isolated_view(trace_id, curve, trace_model)
            else:
                self.plot_item.addItem(curve)
                logger.debug(f"Added trace {trace_id} to main plot")

            # Set initial visibility
            curve.setVisible(trace_model.get_property('visible', True))

        except Exception as e:
            logger.error(f"Error adding trace {trace_id}: {e}")
            self.remove_trace(trace_id)

    def change_trace(self, model_id: str, prop: str, value: Any):
        """Handle trace property changes with proper cleanup when switching modes."""
        if model_id not in self.traces:
            logger.warning(f"Trace {model_id} not found for property update: {prop}")
            return

        try:
            model, curve = self.traces[model_id]
            
            if prop == "data":
                x_data, y_data = value
                curve.setData(x_data, y_data, connect='finite')
                
            elif prop == "color":
                # Update pen color
                pen = curve.opts['pen']
                pen.setColor(pg.mkColor(value))
                curve.setPen(pen)
                
                # Also update isolated axis color if it exists
                if model_id in self.isolated_axes:
                    logger.debug(f"Updating isolated axis color for {model_id}")
                    self.isolated_axes[model_id].setPen(pg.mkPen(value))
                    
            elif prop == "visible":
                curve.setVisible(value)
                
                # Also update isolated axis visibility
                if model_id in self.isolated_axes:
                    logger.debug(f"Updating isolated axis visibility for {model_id}")
                    self.isolated_axes[model_id].setVisible(value)
                    
            elif prop == "width":
                pen = curve.opts['pen']
                pen.setWidth(value)
                curve.setPen(pen)
                
            elif prop == "style":
                pen = curve.opts['pen']
                pen.setStyle(self._get_qt_line_style(value))
                curve.setPen(pen)
                
            elif prop == "mode":
                current_mode = value
                previous_mode = "Isolate" if model_id in self.isolated_view_boxes else "Group"
                
                if current_mode == previous_mode:
                    logger.debug(f"Trace {model_id} already in {current_mode} mode, no change needed")
                    return
                
                logger.debug(f"Switching trace {model_id} from {previous_mode} to {current_mode} mode")
                
                # Remove from current location first
                if current_mode == "Group":
                    # Moving from Isolate to Group
                    logger.debug(f"Moving trace {model_id} from isolated view to main plot")
                    self._remove_from_isolated_view(model_id, curve)
                    self.plot_item.addItem(curve)
                    logger.debug(f"Added trace {model_id} to main plot in Group mode")
                else:
                    # Moving from Group to Isolate
                    logger.debug(f"Moving trace {model_id} from main plot to isolated view")
                    if curve.scene() == self.plot_item.scene():
                        self.plot_item.removeItem(curve)
                    self._setup_isolated_view(model_id, curve, model)

                # Critical: Force geometry and layout updates after mode changes
                # Without these explicit updates, isolated trace viewboxes may not align correctly
                # when multiple traces change mode (especially "isolate all" or "group all" operations)
                self.update_geometry(self.plot_item.vb.sceneBoundingRect())
                # Also trigger a layout update
                self.plot_layout.updateGeometry()

        except Exception as e:
            logger.error(f"Error updating trace {model_id}.{prop}: {e}")

    def link_trace(self, trace_model) -> None:
        logger.debug(f"Linking trace {trace_model.id}; no special handling implemented.")
        # For now, no additional processing is needed.
        pass
        
    def remove_trace(self, trace_id: str) -> None:
        """Remove a trace and clean up all resources."""
        if trace_id not in self.traces:
            logger.warning(f"Cannot remove trace {trace_id} - not found")
            return

        try:
            model, curve = self.traces[trace_id]
            
            # Check if in isolated mode and cleanup
            if trace_id in self.isolated_view_boxes:
                self._remove_from_isolated_view(trace_id, curve)
            else:
                # Remove from main plot if present
                if curve.scene() == self.plot_item.scene():
                    self.plot_item.removeItem(curve)
                    logger.debug(f"Removed trace {trace_id} from main plot")
            
            # Remove from traces dictionary
            del self.traces[trace_id]
            logger.debug(f"Trace {trace_id} removed completely")
            
        except Exception as e:
            logger.error(f"Error removing trace {trace_id}: {e}")

    def _remove_from_isolated_view(self, trace_id: str, curve: pg.PlotDataItem) -> None:
        """
        Remove trace from isolated view with thorough cleanup.
        
        This method handles all cleanup of the isolated view:
        1. Remove curve from viewbox 
        2. Remove and delete the axis
        3. Remove and delete the viewbox
        4. Clear all references
        """
        # First check if this trace is actually in an isolated view
        if trace_id not in self.isolated_view_boxes:
            logger.warning(f"Trace {trace_id} not found in isolated views")
            return
            
        logger.debug(f"Starting isolated view cleanup for trace {trace_id}")
        
        # Step 1: Remove curve from viewbox
        view_box = self.isolated_view_boxes[trace_id]
        if curve.scene():
            try:
                view_box.removeItem(curve)
                logger.debug(f"Removed curve from viewbox for trace {trace_id}")
            except Exception as e:
                logger.error(f"Error removing curve from viewbox: {e}")
        
        # Step 2: Handle axis cleanup
        if trace_id in self.isolated_axes:
            axis = self.isolated_axes[trace_id]
            col = self.axis_columns.get(trace_id, -1)
            
            try:
                # First remove axis from layout
                if axis.scene():
                    # Use removeItem directly on the layout with the known column
                    if col >= 0:
                        self.plot_layout.removeItem(axis)
                        logger.debug(f"Removed axis from plot layout at column {col}")
                    else:
                        logger.warning(f"Column position unknown for axis {trace_id}, trying direct removal")
                        # We don't know the column, so we need to search and remove
                        for item_pos, item in list(self.plot_layout.items()):
                            if item == axis:
                                self.plot_layout.removeItem(item)
                                logger.debug(f"Found and removed axis at position {item_pos}")
                                break
                
                # Then properly delete the axis
                axis.setParent(None)  # Detach from any parent
                axis.deleteLater()
                logger.debug(f"Deleted axis object for trace {trace_id}")
                
                # Clear from our tracking dict
                del self.isolated_axes[trace_id]
                if trace_id in self.axis_columns:
                    del self.axis_columns[trace_id]
            except Exception as e:
                logger.error(f"Error cleaning up axis for {trace_id}: {e}")
        
        # Step 3: Handle viewbox cleanup
        try:
            # Remove from scene if still there
            if view_box.scene():
                view_box.scene().removeItem(view_box)
                logger.debug(f"Removed viewbox from scene for trace {trace_id}")
            
            # Delete the viewbox
            view_box.setParent(None)  # Detach from any parent
            view_box.deleteLater()
            logger.debug(f"Deleted viewbox object for trace {trace_id}")
            
            # Clear from our tracking dict
            del self.isolated_view_boxes[trace_id]
        except Exception as e:
            logger.error(f"Error cleaning up viewbox for {trace_id}: {e}")
        
        logger.debug(f"Completed isolated view cleanup for trace {trace_id}")

    def _setup_isolated_view(self, trace_id: str, curve: pg.PlotDataItem, model) -> None:
        """Create an isolated view for a trace with proper linking."""
        try:
            # Get model properties
            color = model.get_property('color', '#ffffff')
            
            # Create right-side y-axis with matching color
            axis = pg.AxisItem("right")
            axis.setPen(pg.mkPen(color))
            
            # Calculate position (one column to the right of the main plot)
            next_col = 1
            while any(col == next_col for col in self.axis_columns.values()):
                next_col += 1
            
            self.plot_layout.addItem(axis, row=0, col=next_col)
            self.isolated_axes[trace_id] = axis
            self.axis_columns[trace_id] = next_col
            logger.debug(f"Created isolated axis for {trace_id} at column {next_col}")

            # Create and link viewbox
            view_box = pg.ViewBox()
            view_box.enableAutoRange()  # Enable autorange by default
            axis.linkToView(view_box)   # Link axis to viewbox
            view_box.setXLink(self.plot_item.vb)  # Link X-axis to main plot
            
            # Add viewbox to scene and store reference
            self.plot_layout.scene().addItem(view_box)
            view_box.setGeometry(self.plot_item.vb.sceneBoundingRect())
            self.isolated_view_boxes[trace_id] = view_box
            
            # Add curve to viewbox
            view_box.addItem(curve)
            logger.debug(f"Added trace {trace_id} to isolated view")

            # Set initial range if data exists
            y_data = model.y_data
            if y_data.size > 0:
                ymin, ymax = np.nanmin(y_data), np.nanmax(y_data)
                if np.isfinite(ymin) and np.isfinite(ymax):
                    padding = (ymax - ymin) * 0.1
                    if padding == 0:  # Handle case of single value
                        padding = abs(ymin) * 0.1 if ymin != 0 else 0.1
                    view_box.setYRange(ymin - padding, ymax + padding)

            # Force layout update - this is critical for correct positioning
            self.plot_layout.updateGeometry()

        except Exception as e:
            logger.error(f"Error setting up isolated view for {trace_id}: {e}")

    def debug_state(self):
        """Log the current state of traces, axes and viewboxes."""
        logger.debug("=== TraceHandler Debug State ===")
        logger.debug(f"Number of traces: {len(self.traces)}")
        logger.debug(f"Number of isolated axes: {len(self.isolated_axes)}")
        logger.debug(f"Number of isolated viewboxes: {len(self.isolated_view_boxes)}")
        
        # Check for mismatches
        for trace_id in self.traces:
            in_isolated = trace_id in self.isolated_view_boxes
            has_axis = trace_id in self.isolated_axes
            if in_isolated != has_axis:
                logger.error(f"MISMATCH: Trace {trace_id} has viewbox={in_isolated} but axis={has_axis}")
        
        # Log axis columns
        logger.debug(f"Axis columns: {self.axis_columns}")
        
        # Check for orphaned objects
        axes_in_layout = 0
        for item_pos, item in self.plot_layout.items():
            if isinstance(item, pg.AxisItem) and item != self.plot_item.getAxis('left') and item != self.plot_item.getAxis('bottom'):
                axes_in_layout += 1
                
        if axes_in_layout > len(self.isolated_axes):
            logger.error(f"Found {axes_in_layout} axes in layout but only {len(self.isolated_axes)} tracked!")
            
        logger.debug("=== End Debug State ===")

    def clear_all(self) -> None:
        """Remove all traces and clean up resources."""
        logger.debug(f"Clearing all traces ({len(self.traces)} total)")
        # Make a copy of the keys to avoid dictionary size change during iteration
        for trace_id in list(self.traces.keys()):
            self.remove_trace(trace_id)
        
        # Double-check for any orphaned axes or viewboxes
        if self.isolated_axes or self.isolated_view_boxes:
            logger.error(f"After clear_all, still have {len(self.isolated_axes)} axes and {len(self.isolated_view_boxes)} viewboxes")
            
            # Force cleanup of any remaining axes
            for trace_id, axis in list(self.isolated_axes.items()):
                try:
                    self.plot_layout.removeItem(axis)
                    axis.setParent(None)
                    axis.deleteLater()
                except Exception as e:
                    logger.error(f"Error cleaning up orphaned axis {trace_id}: {e}")
            
            # Force cleanup of any remaining viewboxes
            for trace_id, vb in list(self.isolated_view_boxes.items()):
                try:
                    if vb.scene():
                        vb.scene().removeItem(vb)
                    vb.setParent(None)
                    vb.deleteLater()
                except Exception as e:
                    logger.error(f"Error cleaning up orphaned viewbox {trace_id}: {e}")
            
            self.isolated_axes.clear()
            self.isolated_view_boxes.clear()
        
        self.axis_columns.clear()

    @staticmethod
    def _get_qt_line_style(style_str: str) -> Qt.PenStyle:
        """Convert string style to Qt PenStyle."""
        styles = {
            'solid': Qt.SolidLine,
            'dash': Qt.DashLine,
            'dot': Qt.DotLine,
            'dashdot': Qt.DashDotLine
        }
        return styles.get(style_str.lower(), Qt.SolidLine)

    def update_geometry(self, main_rect) -> None:
        """Update geometry of isolated view boxes when the main plot resizes."""
        # Get the exact geometry of the main plot's viewbox
        main_viewbox_rect = self.plot_item.vb.sceneBoundingRect()
        
        for trace_id, view_box in self.isolated_view_boxes.items():
            if view_box.scene():
                # Important: Set all viewboxes to exactly match the main viewbox geometry
                view_box.setGeometry(main_viewbox_rect)
                
                # Ensure the Y-axis is linked to its viewbox and positioned correctly
                if trace_id in self.isolated_axes:
                    axis = self.isolated_axes[trace_id]
                    axis.linkToView(view_box)
                    
                logger.debug(f"Updated geometry for isolated viewbox {trace_id}")
            else:
                logger.warning(f"ViewBox for {trace_id} not in scene, cannot update geometry")
                
    def get_traces_by_model_type(self, model_type: str) -> List[Tuple[Any, pg.PlotDataItem]]:
        """Get traces that match a specific model type."""
        return [(model, curve) for model, curve in self.traces.values() 
                if hasattr(model, 'model_type') and model.model_type == model_type]