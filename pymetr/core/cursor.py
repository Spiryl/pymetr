# --- cursor.py ---

class Cursor:
    def __init__(self, label=None, color='#white', line_style='dotted', line_thickness='1px', position=0.0, orientation='x'):
        self.label = label
        self.color = color
        self.line_style = line_style
        self.line_thickness = line_thickness
        self.position = position
        self.visible = True
        self.orientation = orientation  # 'x' for vertical cursor, 'y' for horizontal cursor