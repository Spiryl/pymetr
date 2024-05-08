# --- cursor_manager.py ---

import logging
logger = logging.getLogger(__name__)

from PySide6.QtCore import QObject, Signal
from pymetr.core.cursor import Cursor

class CursorManager(QObject):
    cursorAdded = Signal(Cursor)
    cursorRemoved = Signal(str)
    cursorVisibilityChanged = Signal(str, bool)
    cursorLabelChanged = Signal(str, str)
    cursorColorChanged = Signal(str, str)
    cursorLineStyleChanged = Signal(str, str)
    cursorLineThicknessChanged = Signal(str, float)
    cursorPositionChanged = Signal(str, float, bool)
    cursorsCleared = Signal()

    def __init__(self):
        super().__init__()
        self.cursors = []

    def add_cursor(self, cursor):
        logger.debug(f"Adding cursor: {cursor.label}")
        self.cursors.append(cursor)
        self.cursorAdded.emit(cursor)

    def remove_cursor(self, cursor_label):
        logger.debug(f"Removing cursor: {cursor_label}")
        for cursor in self.cursors:
            if cursor.label == cursor_label:
                self.cursors.remove(cursor)
                self.cursorRemoved.emit(cursor_label)
                break

    def set_cursor_visibility(self, cursor_label, visible):
        for cursor in self.cursors:
            if cursor.label == cursor_label:
                cursor.visible = visible
                self.cursorVisibilityChanged.emit(cursor_label, visible)
                break

    def set_cursor_label(self, old_label, new_label):
        for cursor in self.cursors:
            if cursor.label == old_label:
                cursor.label = new_label
                self.cursorLabelChanged.emit(old_label, new_label)
                break

    def set_cursor_color(self, cursor_label, color):
        for cursor in self.cursors:
            if cursor.label == cursor_label:
                cursor.color = color
                self.cursorColorChanged.emit(cursor_label, color)
                break

    def set_cursor_line_style(self, cursor_label, style):
        for cursor in self.cursors:
            if cursor.label == cursor_label:
                cursor.line_style = style
                self.cursorLineStyleChanged.emit(cursor_label, style)
                break

    def set_cursor_line_thickness(self, cursor_label, thickness):
        for cursor in self.cursors:
            if cursor.label == cursor_label:
                cursor.line_thickness = thickness
                self.cursorLineThicknessChanged.emit(cursor_label, thickness)
                break

    def set_cursor_position(self, cursor_label, position):
        logger.debug(f"Setting cursor position: {cursor_label}, {position}")
        for cursor in self.cursors:
            if cursor.label == cursor_label:
                cursor.position = position
                self.cursorPositionChanged.emit(cursor_label, position, False)
                break

    def clear_cursors(self):
        self.cursors.clear()
        self.cursorsCleared.emit()