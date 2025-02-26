from PySide6.QtCore import QObject, Qt, Signal
import pyqtgraph as pg
from pymetr.core.logging import logger

class CursorHandler(QObject):
    # CursorHandler manages cursors on a plot.
    # It emits a cursor_updated signal when a cursor is dragged.
    cursor_updated = Signal(str, str, object)  # model_id, property, new value

    _style_map = {
        'solid': Qt.SolidLine,
        'dash': Qt.DashLine,
        'dot': Qt.DotLine,
        'dashdot': Qt.DashDotLine
    }
    
    def __init__(self, plot_item: pg.PlotItem, state):
        super().__init__()
        self.plot_item = plot_item
        self.state = state  # For model lookups
        self.cursors = {}  # Maps cursor id to InfiniteLine instances
        logger.debug("CursorHandler initialized")
    
    def _get_qt_line_style(self, style_str: str) -> Qt.PenStyle:
        styles = {
            'solid': Qt.SolidLine,
            'dash': Qt.DashLine,
            'dot': Qt.DotLine,
            'dashdot': Qt.DashDotLine
        }
        return styles.get(style_str.lower(), Qt.SolidLine)
    
    def register_cursor(self, cursor_model) -> None:
        cursor_id = cursor_model.id
        if cursor_id in self.cursors:
            logger.warning(f"Cursor {cursor_id} is already registered.")
            return
        try:
            position = cursor_model.get_property('position', 0.0)
            axis = cursor_model.get_property('axis', 'x')
            color = cursor_model.get_property('color', '#FFFF00')
            style = cursor_model.get_property('style', 'solid')
            width = cursor_model.get_property('width', 1)
            visible = cursor_model.get_property('visible', True)
            
            pen = pg.mkPen(
                color=color,
                width=width,
                style=self._get_qt_line_style(style)
            )
            angle = 90 if axis.lower() == "x" else 0
            cursor_line = pg.InfiniteLine(
                pos=position,
                angle=angle,
                pen=pen,
                movable=True
            )
            cursor_line.setVisible(visible)
            self.plot_item.addItem(cursor_line)
            self.cursors[cursor_id] = cursor_line
            logger.debug(f"Registered cursor {cursor_id} at position {position} with axis {axis}")
            # Connect the cursor's position-changed signal to our handler
            cursor_line.sigPositionChanged.connect(lambda pos, cid=cursor_id: self._cursor_dragged(cid, pos))
        except Exception as e:
            logger.error(f"Error registering cursor {cursor_id}: {e}", exc_info=True)
    
    def _cursor_dragged(self, cursor_id: str, pos) -> None:
        logger.debug(f"Cursor {cursor_id} dragged to position {pos}")
        # Emit the cursor_updated signal with model_id, property "position", and the new value
        self.cursor_updated.emit(cursor_id, "position", pos)
    
    def change_cursor(self, cursor_id: str, prop: str, value) -> None:
        if cursor_id not in self.cursors:
            logger.debug(f"Cursor {cursor_id} not found for update.")
            return
        logger.debug(f"Changing cursor {cursor_id}: property '{prop}' to {value}")
        try:
            cursor_line = self.cursors[cursor_id]
            if not cursor_line.scene():
                logger.debug(f"Cursor {cursor_id} scene not available; skipping update.")
                return
            
            if prop == "position":
                cursor_line.setValue(value)
                logger.debug(f"Cursor {cursor_id} position set to {value}")
            elif prop == "axis":
                angle = 90 if value.lower() == "x" else 0
                pos = cursor_line.value()
                current_pen = cursor_line.pen
                is_visible = cursor_line.isVisible()
                is_movable = cursor_line.movable
                self.plot_item.removeItem(cursor_line)
                new_cursor = pg.InfiniteLine(
                    pos=pos,
                    angle=angle,
                    pen=current_pen,
                    movable=is_movable
                )
                new_cursor.setVisible(is_visible)
                self.plot_item.addItem(new_cursor)
                self.cursors[cursor_id] = new_cursor
                # Reconnect the dragged signal on the new cursor
                new_cursor.sigPositionChanged.connect(lambda pos, cid=cursor_id: self._cursor_dragged(cid, pos))
                logger.debug(f"Cursor {cursor_id} axis changed; new angle set to {angle}")
            elif prop == "color":
                current_pen = cursor_line.pen
                pen = pg.mkPen(
                    color=value,
                    width=current_pen.width(),
                    style=current_pen.style()
                )
                cursor_line.setPen(pen)
                logger.debug(f"Cursor {cursor_id} color changed to {value}")
            elif prop == "style":
                current_pen = cursor_line.pen
                qt_style = self._get_qt_line_style(value)
                pen = pg.mkPen(
                    color=current_pen.color(),
                    width=current_pen.width(),
                    style=qt_style
                )
                cursor_line.setPen(pen)
                logger.debug(f"Cursor {cursor_id} style changed to {value}")
            elif prop == "width":
                current_pen = cursor_line.pen
                pen = pg.mkPen(
                    color=current_pen.color(),
                    width=int(value),
                    style=current_pen.style()
                )
                cursor_line.setPen(pen)
                logger.debug(f"Cursor {cursor_id} width changed to {value}")
            elif prop == "visible":
                cursor_line.setVisible(bool(value))
                logger.debug(f"Cursor {cursor_id} visibility set to {value}")
            else:
                logger.warning(f"Unhandled cursor property: {prop}")
        except Exception as e:
            logger.error(f"Error changing cursor {cursor_id} property {prop}: {e}", exc_info=True)

    def link_cursor(self, cursor_model) -> None:
        logger.debug(f"Linking cursor {cursor_model.id}; no special handling implemented.")
        # For now, no additional processing is needed.
        pass

    def remove_cursor(self, cursor_id: str) -> None:
        if cursor_id not in self.cursors:
            logger.debug(f"Cursor {cursor_id} not found for removal.")
            return
        try:
            cursor_line = self.cursors[cursor_id]
            if cursor_line.scene():
                self.plot_item.removeItem(cursor_line)
            del self.cursors[cursor_id]
            logger.debug(f"Removed cursor {cursor_id}")
        except Exception as e:
            logger.error(f"Error removing cursor {cursor_id}: {e}", exc_info=True)
