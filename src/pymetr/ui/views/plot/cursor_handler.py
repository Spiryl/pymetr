from PySide6.QtCore import QObject, Qt
import pyqtgraph as pg
from pymetr.core.logging import logger
from typing import Dict, Any

class CursorHandler(QObject):
    """
    CursorHandler for managing cursors on a plot.
    """
    # Add a style mapping dictionary
    _style_map = {
        'solid': Qt.SolidLine,
        'dash': Qt.DashLine,
        'dot': Qt.DotLine,
        'dashdot': Qt.DashDotLine
    }

    def __init__(self, plot_item: pg.PlotItem, state):
        """
        Initialize the CursorHandler.

        Args:
            plot_item: Main plot for cursor overlays.
            state: The ApplicationState instance.
        """
        super().__init__()
        self.plot_item = plot_item
        self.state = state  # Save state for lookups
        self.cursors: Dict[str, pg.InfiniteLine] = {}

        logger.debug("CursorHandler initialized")

        # Connect to plot item signals as needed.
        # For example, if you have a mechanism to detect cursor movement,
        # you might connect a lambda to call _handle_cursor_moved.

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
    
    def handle_property_change(self, model_id: str, model_type: str, prop: str, value: Any) -> None:
        """Handle cursor property changes."""
        if model_id not in self.cursors:
            logger.debug(f"[CursorHandler] Cursor {model_id} not found.")
            return

        logger.debug(f"[CursorHandler] Updating cursor {model_id}: prop={prop}, value={value}")
        try:
            cursor_line = self.cursors[model_id]
            
            # Check if cursor still exists
            if not cursor_line.scene():
                logger.debug(f"[CursorHandler] Cursor {model_id} already deleted")
                return
            
            if prop == "position":
                cursor_line.setValue(value)
            elif prop == "axis":
                try:
                    # Handle axis change - recreate cursor with new angle
                    angle = 90 if value == "x" else 0
                    pos = cursor_line.value()
                    current_pen = cursor_line.pen
                    is_visible = cursor_line.isVisible()
                    is_movable = cursor_line.movable
                    
                    # Remove old cursor
                    if cursor_line.scene():
                        self.plot_item.removeItem(cursor_line)
                    
                    # Create new cursor with updated angle
                    new_cursor = pg.InfiniteLine(
                        pos=pos, 
                        angle=angle,
                        pen=current_pen,
                        movable=is_movable
                    )
                    # Set visibility after creation
                    new_cursor.setVisible(is_visible)
                    
                    self.plot_item.addItem(new_cursor)
                    self.cursors[model_id] = new_cursor
                except Exception as e:
                    logger.error(f"Error recreating cursor: {e}")
                    
            elif prop == "color":
                try:
                    current_pen = cursor_line.pen
                    pen = pg.mkPen(
                        color=value,
                        width=current_pen.width(),
                        style=current_pen.style()
                    )
                    cursor_line.setPen(pen)
                except Exception as e:
                    logger.error(f"Error updating cursor color: {e}")
                    
            elif prop == "style":
                try:
                    style_map = {
                        'solid': Qt.SolidLine,
                        'dash': Qt.DashLine,
                        'dot': Qt.DotLine,
                        'dashdot': Qt.DashDotLine
                    }
                    current_pen = cursor_line.pen
                    qt_style = style_map.get(value, Qt.SolidLine)
                    pen = pg.mkPen(
                        color=current_pen.color(),
                        width=current_pen.width(),
                        style=qt_style
                    )
                    cursor_line.setPen(pen)
                except Exception as e:
                    logger.error(f"Error updating cursor style: {e}")
                    
            elif prop == "width":
                try:
                    current_pen = cursor_line.pen
                    pen = pg.mkPen(
                        color=current_pen.color(),
                        width=int(value),
                        style=current_pen.style()
                    )
                    cursor_line.setPen(pen)
                except Exception as e:
                    logger.error(f"Error updating cursor width: {e}")
                    
            elif prop == "visible":
                if cursor_line.scene():  # Only set if cursor still exists
                    cursor_line.setVisible(bool(value))
            else:
                logger.warning(f"Unhandled cursor property: {prop}")
                
        except Exception as e:
            logger.error(f"Error updating cursor {model_id}.{prop}: {e}")

    def add_cursor(self, cursor_model) -> None:
        """Add a new cursor from a model."""
        cursor_id = cursor_model.id
        if cursor_id in self.cursors:
            return
        try:
            position = cursor_model.get_property('position', 0.0)
            axis = cursor_model.get_property('axis', 'x')
            color = cursor_model.get_property('color', '#FFFF00')
            style = cursor_model.get_property('style', 'solid')
            width = cursor_model.get_property('width', 1)
            visible = cursor_model.get_property('visible', True)

            # Create pen with proper style
            pen = pg.mkPen(
                color=color,
                width=width,
                style=self._get_qt_line_style(style)
            )

            # Create cursor with proper angle based on axis
            angle = 90 if axis == "x" else 0
            cursor_line = pg.InfiniteLine(
                pos=position,
                angle=angle,
                pen=pen,
                movable=True
            )
            
            cursor_line.setVisible(visible)
            self.plot_item.addItem(cursor_line)
            self.cursors[cursor_id] = cursor_line

            logger.debug(f"Added cursor {cursor_id} at position {position}")
        except Exception as e:
            logger.error(f"Error adding cursor {cursor_id}: {e}")

    def remove_cursor(self, cursor_id: str) -> None:
        """Remove a cursor."""
        if cursor_id not in self.cursors:
            return
        try:
            cursor_line = self.cursors[cursor_id]
            if cursor_line.scene():  # Check if cursor still exists
                self.plot_item.removeItem(cursor_line)
            del self.cursors[cursor_id]
            logger.debug(f"Removed cursor {cursor_id}")
        except Exception as e:
            logger.error(f"Error removing cursor {cursor_id}: {e}")

    def clear_all(self) -> None:
        """Remove all cursors."""
        for cursor_id in list(self.cursors.keys()):
            self.remove_cursor(cursor_id)

    def _handle_cursor_moved(self, cursor_id: str) -> None:
        """
        Called when a cursor is moved interactively.
        Use the stored state to look up the cursor model.
        """
        try:
            cursor_model = self.state.get_model(cursor_id)
            if cursor_model is None:
                return
            # Here you can update the model based on the new cursor position.
            # For example, if the cursor is movable:
            new_pos = self.cursors[cursor_id].value()
            cursor_model.set_property('position', new_pos)
        except Exception as e:
            logger.error(f"Error handling cursor move for {cursor_id}: {e}")
