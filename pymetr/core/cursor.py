# --- cursor.py ---

class Cursor:
    def __init__(self, label=None, color=None, line_style=None, line_thickness=None, position=None, orientation=None):
        self.label = label
        self.color = color
        self.line_style = line_style
        self.line_thickness = line_thickness
        self.position = position
        self.visible = True
        self.orientation = orientation  # 'x' for vertical cursor, 'y' for horizontal cursor