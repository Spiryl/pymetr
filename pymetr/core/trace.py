import logging
logger = logging.getLogger(__name__)

import numpy as np


class Trace:
    def __init__(self, data, x_data=None, z_data=None, label=None, color=None, mode=None, visible=True, line_thickness=1.0, line_style='Solid'):
        """
        Initializes a Trace object to store data and attributes for plotting.

        Args:
        label (str): Label for the trace.
        y_data (list or np.array): Primary data points for the trace.
        x_data (list or np.array, optional): X-axis values if different from default range(len(y_data)).
        z_data (list or np.array, optional): Z-axis values for 3D plotting.
        color (str): Color of the trace in hex format.
        visible (bool): Visibility of the trace in the plot.
        line_thickness (float): Thickness of the line in the plot.
        line_style (str): Style of the line (e.g., 'Solid', 'Dash').
        """
        self.data = np.array(data)
        self.x_data = np.array(x_data) if x_data is not None else None
        self.z_data = np.array(z_data) if z_data is not None else None
        self.color = color
        self.label = label
        self.mode = mode
        self.visible = visible
        self.x_range = None
        self.y_range = None
        self.line_thickness = line_thickness
        self.line_style = line_style
        self.show_markers = True

    def update_data(self, y_data, x_data=None, z_data=None):
        """Update the trace data."""
        self.y_data = np.array(y_data)
        if x_data is not None:
            self.x_data = np.array(x_data)
        if z_data is not None:
            self.z_data = np.array(z_data)
