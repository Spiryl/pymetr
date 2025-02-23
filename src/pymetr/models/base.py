# pymetr/models/base.py
from PySide6.QtCore import QObject, Signal
from typing import Optional, Any
import uuid
import pandas as pd
from pymetr.core.logging import logger

class BaseModel(QObject):
    # Updated signal to include model_type
    property_changed = Signal(str, str, str, object)  # model_id, model_type, property, value
    child_added = Signal(str, str)              # parent_id, child_id

    def __init__(self, model_type: str, state=None, model_id: Optional[str] = None, name: Optional[str] = None):
        super().__init__()
        self.model_type = model_type
        self._id = model_id or str(uuid.uuid4())
        # Set the human-readable name; default to "Untitled" if not provided.
        self._name = name if name is not None else "Untitled"
        
        # Create a valid Qt objectName from the model name/id
        # Replace spaces and special chars with underscores
        safe_name = self._name.replace(' ', '_').replace(';', '').replace(':', '')
        object_name = f"{safe_name}_{self._id}"
        self.setObjectName(object_name)  # Set QObject name
        
        self._properties = {}
        self._children = {}
        self._connections = []
        self._batch_mode = False
        self._pending_updates = {}
        self.state = state
        if self.state is not None:
            self.state.register_model(self)
        logger.debug(f"{self.model_type} created with ID: {self._id}, name: {self._name}, objectName: {object_name}")
        # Store both name and objectName as properties
        self.set_property('name', self._name)
        self.set_property('objectName', object_name)

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        """Return the human-readable name of the model."""
        return self._name

    def set_property(self, name: str, value: object) -> None:
        """
        Assign value to self._properties[name] unconditionally
        and emit self.property_changed(...) with (model_id, model_type, name, value).
        Skips all array/DataFrame comparison logic, so it may emit even if unchanged.
        """

        # If it's a DataFrame, store a copy so we don't accidentally mutate the original
        if isinstance(value, pd.DataFrame):
            self._properties[name] = value.copy()
        else:
            self._properties[name] = value

        # Always emit the signal (no old/new comparison)
        self.property_changed.emit(self.id, self.model_type, name, value)

    def get_property(self, prop: str, default: Any = None) -> Any:
        """Get a property value with optional default."""
        return self._properties.get(prop, default)

    def begin_update(self) -> None:
        """Begin batch update mode."""
        self._batch_mode = True
        self._pending_updates.clear()

    def end_update(self) -> None:
        """End batch update mode and emit changes."""
        self._batch_mode = False
        self._process_pending_updates()

    def _process_pending_updates(self) -> None:
        """Process all pending updates."""
        if not self._pending_updates:
            return

        # Emit all pending changes
        for prop, value in self._pending_updates.items():
            self.property_changed.emit(self.id, self.model_type, prop, value)
        
        self._pending_updates.clear()

    def add_child(self, child_model: 'BaseModel') -> None:
        """Add a child model with proper cleanup handling."""
        if child_model.id in self._children:
            logger.warning(f"Child {child_model.id} already exists in {self.id}")
            return

        self._children[child_model.id] = child_model
        self.child_added.emit(self.id, child_model.id)
        logger.debug(f"Added child {child_model.id} to {self.id}")

    def get_children(self) -> list['BaseModel']:
        """Get list of child models."""
        return list(self._children.values())

    def clear_children(self) -> None:
        """Remove all children with proper cleanup."""
        for child_id in list(self._children.keys()):
            if self.state:
                self.state.remove_model(child_id)
        self._children.clear()
        logger.debug(f"Cleared all children from {self.id}")

    def cleanup(self) -> None:
        """Clean up resources and connections."""
        # Clear all properties and pending updates
        self._properties.clear()
        self._pending_updates.clear()
        
        # Clean up children
        self.clear_children()
        
        # Clear state reference
        self.state = None
        
        logger.debug(f"Cleaned up model {self.id}")

    def deleteLater(self) -> None:
        """Override deleteLater for proper cleanup."""
        self.cleanup()
        super().deleteLater()

    def show(self) -> None:
        """Request model view activation."""
        if self.state:
            self.state.set_active_model(self.id)
            logger.debug(f"Model {self.id} requested to be shown")
        else:
            logger.warning(f"Cannot show model {self.id} - no state manager attached")

