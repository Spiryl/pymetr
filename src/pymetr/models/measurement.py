from typing import Optional
from pymetr.models.base import BaseModel
from pymetr.core.logging import logger

class Measurement(BaseModel):
    """
    A single measurement value with optional limits for validation.
    """
    def __init__(self, name: str, value: float, units: str = "", model_id: Optional[str] = None):
        super().__init__(model_id=model_id)
        self.set_property("name", name)
        self.set_property("value", value)
        self.set_property("units", units)
        self.set_property("timestamp", None)
        self.set_property("limits", None)  # Optional (min, max) tuple
        self.set_property("status", "Valid")  # 'Valid', 'Invalid', or 'Warning'

    @property
    def name(self) -> str:
        return self.get_property("name")

    @property
    def value(self) -> float:
        return self.get_property("value")

    @value.setter
    def value(self, val: float):
        self.set_property("value", val)
        # Check limits if present
        limits = self.get_property("limits")
        if limits:
            min_val, max_val = limits
            if not (min_val <= val <= max_val):
                self.set_property("status", "Invalid")
            else:
                self.set_property("status", "Valid")

    @property
    def units(self) -> str:
        return self.get_property("units")

    def set_limits(self, min_val: float, max_val: float):
        """Set measurement limits and validate current value."""
        self.set_property("limits", (min_val, max_val))
        # Re-check current value
        curr_val = self.value
        if not (min_val <= curr_val <= max_val):
            self.set_property("status", "Invalid")

    def to_string(self) -> str:
        """Simple string representation (e.g. '12.34 V')."""
        if self.units:
            return f"{self.value} {self.units}"
        return str(self.value)
