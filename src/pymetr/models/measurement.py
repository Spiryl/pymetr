# app/models/measurement.py

from typing import Optional
from .base import BaseModel
from ..logging import logger

class Measurement(BaseModel):
    """A calculated measurement result."""
    
    def __init__(self, test_id: str, label: str, value: float,
                 units: str = "", id: Optional[str] = None):
        super().__init__(id)
        self.test_id = test_id
        self.label = label
        self._value = value
        self._units = units
        self._position: Optional[float] = None
        self._color: str = "#00FF00"
        self._visible: bool = True
        self._pass_fail: Optional[bool] = None
    
    @property
    def value(self) -> float:
        return self._value
    
    @value.setter
    def value(self, new_value: float):
        old_value = self._value
        self._value = new_value
        self.notify_change("value", {
            "measurement_id": self.id,
            "old": old_value,
            "new": new_value,
            "label": self.label
        })
    
    @property
    def pass_fail(self) -> Optional[bool]:
        return self._pass_fail
    
    @pass_fail.setter
    def pass_fail(self, value: Optional[bool]):
        old_value = self._pass_fail
        self._pass_fail = value
        self.notify_change("pass_fail", {
            "measurement_id": self.id,
            "old": old_value,
            "new": value,
            "label": self.label
        })
    
    @property
    def position(self) -> Optional[float]:
        return self._position
    
    @position.setter
    def position(self, value: Optional[float]):
        self._position = value
        self.notify_change("position", {
            "measurement_id": self.id,
            "value": value,
            "label": self.label
        })
    
    @property
    def visible(self) -> bool:
        return self._visible
    
    @visible.setter
    def visible(self, value: bool):
        self._visible = value
        self.notify_change("visibility", {
            "measurement_id": self.id,
            "visible": value,
            "label": self.label
        })