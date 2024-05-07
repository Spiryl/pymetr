# --- marker.py ---

class Marker:
    def __init__(self, label="marker", color=None, shape=None, position=None, size=10, placement_mode='nearest'):
        self.label = label
        self.color = color
        self.shape = shape
        self.position = position
        self.size = size
        self.placement_mode = placement_mode
        self.visible = True
