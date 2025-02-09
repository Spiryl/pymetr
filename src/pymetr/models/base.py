# pymetr/models/base.py
from PySide6.QtCore import QObject, Signal, QThread, Qt, QMetaObject, Q_ARG
from typing import Optional, Any
import uuid
from pymetr.core.logging import logger

class BaseModel(QObject):
    property_changed = Signal(str, str, object)  # model_id, property, value
    child_added = Signal(str, str)              # parent_id, child_id

    def __init__(self, state=None, model_id: Optional[str] = None):
        super().__init__()
        self._id = model_id or str(uuid.uuid4())
        self._properties = {}
        self._children = {}
        self.state = state
        if self.state is not None:
            self.state.register_model(self)
        logger.debug(f"BaseModel created with ID: {self._id}")

    @property
    def id(self) -> str:
        return self._id

    def set_property(self, name: str, value: object) -> None:
        """Set a property value."""
        if self._properties.get(name) != value:
            self._properties[name] = value
            self.property_changed.emit(self.id, name, value)
            logger.debug(f"Property '{name}' set to '{value}' for {self.id}")

    def get_property(self, name: str, default: object = None) -> object:
        return self._properties.get(name, default)

    def add_child(self, child: 'BaseModel') -> None:
        """Add a child model."""
        if child.id in self._children:
            return
        self._children[child.id] = child
        if self.state:
            self.state.register_model(child)
            self.state.link_models(self.id, child.id)
        self.child_added.emit(self.id, child.id)
        logger.debug(f"Added child {child.id} to {self.id}")

    def get_children(self) -> list:
        return list(self._children.values())

    def get_child(self, child_id: str) -> Optional['BaseModel']:
        return self._children.get(child_id)