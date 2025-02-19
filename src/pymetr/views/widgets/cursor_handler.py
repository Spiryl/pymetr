from PySide6.QtCore import QObject, Qt, QTimer
import pyqtgraph as pg
import numpy as np
from typing import Dict, Any, Optional
from pymetr.core.logging import logger

class CursorHandler(QObject):
    """
    High-performance cursor management optimized for real-time updates.
    """
    def __init__(self, plot_item: pg.PlotItem):
        super().__init__()
        self.plot_item = plot_item

        # Core storage only - no timers needed
        self.cursors: Dict[str, pg.InfiniteLine] = {}
        self.cursor_labels: Dict[str, pg.TextItem] = {}
        self.cursor_values: Dict[str, Dict[str, float]] = {}
        
        logger.debug("CursorHandler initialized")

    def add_cursor(self, cursor_model) -> None:
        """Add a new cursor from model."""
        cursor_id = cursor_model.id
        if cursor_id in self.cursors:
            return

        try:
            # Extract properties
            pos = cursor_model.get_property('position', 0.0)
            color = cursor_model.get_property('color', '#FFFF00')
            width = cursor_model.get_property('width', 1)
            style = cursor_model.get_property('style', 'solid')
            visible = cursor_model.get_property('visible', True)
            axis = cursor_model.get_property('axis', 'x')

            # Create cursor line
            pen = pg.mkPen(color=color, width=width, style=self._get_qt_line_style(style))
            cursor_line = pg.InfiniteLine(
                pos=pos,
                angle=90 if axis == 'x' else 0,
                movable=True,
                pen=pen
            )

            # Create label
            label = pg.TextItem(
                text="",
                color=color,
                anchor=(0.5, 1.0),
                border=pg.mkPen(color=color, width=1),
                fill=pg.mkBrush(color='#2A2A2A')
            )

            # Add to plot and store
            self.plot_item.addItem(cursor_line)
            self.plot_item.addItem(label)
            
            cursor_line.setVisible(visible)
            label.setVisible(visible)

            self.cursors[cursor_id] = cursor_line
            self.cursor_labels[cursor_id] = label
            self.cursor_values[cursor_id] = {}

            # Connect movement handler
            cursor_line.sigPositionChanged.connect(
                lambda: self._handle_cursor_moved(cursor_id)
            )

            # Initial value update
            self._update_cursor_values(cursor_id)
            logger.debug(f"Added cursor {cursor_id}")

        except Exception as e:
            logger.error(f"Error adding cursor {cursor_id}: {e}")
            self.remove_cursor(cursor_id)

    def handle_property_change(self, model_id: str, model_type: str, prop: str, value: Any) -> None:
        """Direct property change handler without throttling."""
        if model_type != 'Cursor' or model_id not in self.cursors:
            return

        try:
            cursor_line = self.cursors[model_id]
            label = self.cursor_labels[model_id]

            if prop == "position":
                cursor_line.setValue(value)
                self._update_cursor_values(model_id)
            elif prop == "color":
                pen = cursor_line.pen
                pen.setColor(pg.mkColor(value))
                cursor_line.setPen(pen)
                label.setColor(value)
                label.setBorder(pg.mkPen(color=value, width=1))
            elif prop == "visible":
                cursor_line.setVisible(value)
                label.setVisible(value)
            elif prop in ("width", "style"):
                pen = cursor_line.pen
                if prop == "width":
                    pen.setWidth(value)
                else:
                    pen.setStyle(self._get_qt_line_style(value))
                cursor_line.setPen(pen)

        except Exception as e:
            logger.error(f"Error updating cursor {model_id}.{prop}: {e}")

    def _handle_cursor_moved(self, cursor_id: str) -> None:
        """When user moves cursor, update model and values."""
        if cursor_id not in self.cursors:
            return
            
        cursor_line = self.cursors[cursor_id]
        pos = cursor_line.value()
        
        # Update values and label
        self._update_cursor_values(cursor_id)
        
        # Update model position
        cursor_model = self.plot_item.param.state.get_model(cursor_id)
        if cursor_model:
            cursor_model.set_property('position', pos)

    def _update_cursor_values(self, cursor_id: str) -> None:
        """Update cursor values and label directly."""
        cursor_line = self.cursors[cursor_id]
        label = self.cursor_labels[cursor_id]
        pos = cursor_line.value()
        is_vertical = (cursor_line.angle == 90)

        # Calculate intersections
        values = {}
        for item in self.plot_item.items:
            if isinstance(item, pg.PlotDataItem) and item.isVisible():
                data = item.getData()
                if data[0].size == 0:
                    continue

                if is_vertical:
                    idx = np.searchsorted(data[0], pos)
                    if 0 <= idx < len(data[1]):
                        values[item.name()] = data[1][idx]
                else:
                    idx = np.searchsorted(data[1], pos)
                    if 0 <= idx < len(data[0]):
                        values[item.name()] = data[0][idx]

        # Update label
        if values:
            label.setText("\n".join(f"{name}: {val:.4g}" for name, val in values.items()))
            if is_vertical:
                label.setPos(pos, max(values.values()))
            else:
                label.setPos(max(values.values()), pos)
            label.setVisible(True)
        else:
            label.setVisible(False)

    def remove_cursor(self, cursor_id: str) -> None:
        """Remove cursor and clean up resources."""
        if cursor_id not in self.cursors:
            return

        try:
            # Remove items from plot
            self.plot_item.removeItem(self.cursors[cursor_id])
            if cursor_id in self.cursor_labels:
                self.plot_item.removeItem(self.cursor_labels[cursor_id])
                del self.cursor_labels[cursor_id]

            # Clean up storage
            del self.cursors[cursor_id]
            self.cursor_values.pop(cursor_id, None)
            
            logger.debug(f"Removed cursor {cursor_id}")

        except Exception as e:
            logger.error(f"Error removing cursor {cursor_id}: {e}")

    def clear_all(self) -> None:
        """Remove all cursors and clean up."""
        for cursor_id in list(self.cursors.keys()):
            self.remove_cursor(cursor_id)
        self.cursor_values.clear()
        logger.debug("All cursors cleared")

    @staticmethod
    def _get_qt_line_style(style_str: str) -> Qt.PenStyle:
        """Convert string style to Qt pen style."""
        return {
            'solid': Qt.SolidLine,
            'dash': Qt.DashLine,
            'dot': Qt.DotLine,
            'dash-dot': Qt.DashDotLine
        }.get(style_str.lower(), Qt.SolidLine)