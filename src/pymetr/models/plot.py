from typing import Optional
import numpy as np
from pymetr.models.base import BaseModel
from pymetr.core.logging import logger


class Plot(BaseModel):
    """
    A container for multiple data traces, with optional grid/legend settings.
    """

    def __init__(self, title: str, model_id: Optional[str] = None):
        super().__init__(model_id=model_id)
        self.set_property("title", title)
        self.set_property("x_label", "")
        self.set_property("y_label", "")
        self.set_property("x_unit", "")
        self.set_property("y_unit", "")
        self.set_property("grid_enabled", True)
        self.set_property("legend_enabled", True)
        self.set_property("roi", None)
        self.set_property("roi_visible", True)
        self.set_property("x_lim", None)

    @property
    def title(self) -> str:
        return self.get_property("title")

    @title.setter
    def title(self, value: str):
        self.set_property("title", value)

    def create_trace(self, x_data: np.ndarray, y_data: np.ndarray, name: str = "", **kwargs):
        """
        Create and register a new Trace model for this Plot.
        """
        from pymetr.models import Trace  # Make sure you import your Trace class
        trace = self.state.create_model(
            Trace,
            x_data=x_data,
            y_data=y_data,
            name=name,
            **kwargs
        )
        self.add_child(trace)
        return trace

    def get_traces(self) -> list:
        """
        Return all Trace children of this Plot.
        """
        from pymetr.models import Trace
        return [child for child in self.get_children() if isinstance(child, Trace)]

    def clear(self):
        """
        Remove all Traces from this Plot.
        """
        traces = self.get_traces()
        for trace in traces:
            self.state.unlink_models(self.id, trace.id)
            self.state.remove_model(trace.id)
        logger.debug(f"Cleared all traces from Plot {self.id} ('{self.title}').")

    def set_trace(
        self,
        trace_name: str,
        x_data: np.ndarray,
        y_data: np.ndarray,
        mode: str = "Group",
        color: Optional[str] = "#ffffff",  # Default white
        style: str = "solid", 
        width: int = 1,
        marker_style: str = "",
        visible: bool = True,
        opacity: float = 1.0,
    ):
        """
        A single-entry method to create or update a trace by name.
        Handles arbitrary data updates efficiently.
        """
        from pymetr.models import Trace

        # Look for an existing trace with this name
        existing_trace = None
        for t in self.get_traces():
            if t.name == trace_name:
                existing_trace = t
                break

        if existing_trace is None:
            # Create a new trace with all properties set
            logger.debug(f"Creating new trace '{trace_name}' in Plot '{self.title}'.")
            new_trace = self.state.create_model(
                Trace,
                x_data=x_data,
                y_data=y_data,
                name=trace_name,
                mode=mode,
                color=color,
                style=style,
                width=width,
                marker_style=marker_style,
                visible=visible,
                opacity=opacity
            )
            self.add_child(new_trace)
        else:
            # Always update data - let Trace handle optimization
            existing_trace.update_data(x_data, y_data)

            # Only update style properties if they changed
            props = {
                "mode": mode,
                "color": color,
                "style": style,
                "width": width,
                "marker_style": marker_style,
                "visible": visible,
                "opacity": opacity
            }

            for prop_name, value in props.items():
                current_value = existing_trace.get_property(prop_name)
                if current_value != value:
                    existing_trace.set_property(prop_name, value)