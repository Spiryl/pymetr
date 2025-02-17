# pymetr/models/base.py
from PySide6.QtCore import QObject, Signal
from typing import Optional, Any
import uuid
import pandas as pd
from pymetr.core.logging import logger

class BaseModel(QObject):
    property_changed = Signal(str, str, object)  # model_id, property, value
    child_added = Signal(str, str)              # parent_id, child_id

    def __init__(self, state=None, model_id: Optional[str] = None, name: Optional[str] = None):
        super().__init__()
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
        logger.debug(f"BaseModel created with ID: {self._id}, name: {self._name}, objectName: {object_name}")
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

    def rename(self, new_name: str) -> None:
        """Rename the model and update its 'name' and 'objectName' properties."""
        if self._name != new_name:
            logger.debug(f"Renaming model {self._id} from '{self._name}' to '{new_name}'")
            self._name = new_name
            # Update objectName to match new name
            safe_name = new_name.replace(' ', '_').replace(';', '').replace(':', '')
            object_name = f"{safe_name}_{self._id}"
            self.setObjectName(object_name)
            # Update properties
            self.set_property('name', new_name)
            self.set_property('objectName', object_name)

    def get_name(self) -> str:
        """Return the human-readable name of the model."""
        return self._name

    def begin_update(self):
        """Start batch update mode."""
        self._batch_mode = True
        self._pending_updates.clear()

    def end_update(self):
        """End batch update mode and emit pending changes."""
        self._batch_mode = False
        # Emit all pending updates
        for name, value in self._pending_updates.items():
            self.property_changed.emit(self.id, name, value)
        self._pending_updates.clear()
        # Uncomment the following line if you have defined batch_update_finished
        # self.batch_update_finished.emit(self.id)

    def set_property(self, name: str, value: object) -> None:
        current_value = self._properties.get(name)
        # Special handling for DataFrames
        if isinstance(value, pd.DataFrame):
            if isinstance(current_value, pd.DataFrame):
                if current_value.equals(value):
                    return
            self._properties[name] = value.copy()  # Store a copy
        else:
            if current_value == value:
                return
            self._properties[name] = value
        self.property_changed.emit(self.id, name, value)

    def get_property(self, name: str, default: object = None) -> object:
        return self._properties.get(name, default)

    def add_child(self, child: 'BaseModel') -> None:
        """Add a child model."""
        if child.id in self._children:
            return
        self._children[child.id] = child
        # if self.state:
        #     self.state.register_model(child)
        #     self.state.link_models(self.id, child.id)
        self.child_added.emit(self.id, child.id)
        logger.debug(f"Added child {child.id} to {self._id}")

    def get_children(self) -> list:
        return list(self._children.values())

    def get_child(self, child_id: str) -> Optional['BaseModel']:
        return self._children.get(child_id)
    
    def cleanup(self):
        """Cleanup resources before deletion."""
        # Disconnect all signals
        for connection in self._connections:
            connection.disconnect()
        self._connections.clear()
        
        # Cleanup children
        for child in list(self._children.values()):
            child.cleanup()
        self._children.clear()
        
        # Clear properties
        self._properties.clear()
        
        # Clear state reference
        self.state = None

    def deleteLater(self):
        """Override deleteLater to ensure cleanup."""
        self.cleanup()
        super().deleteLater()

    def clear_children(self) -> None:
        """
        Remove and clean up all child models of this model.
        This method unlinks each child from the state (if available) and calls
        the removal/cleanup routines.
        """
        # Make a copy of the current children list
        children = list(self.get_children())
        for child in children:
            if self.state:
                # Remove the child using the state's removal method.
                # This should handle unlinking relationships and cleaning up signals.
                self.state.remove_model(child.id)
            else:
                # Fallback: directly delete the child if no state is set.
                child.deleteLater()
        # Clear the internal children dict
        self._children.clear()
        logger.debug(f"Cleared all children for model {self._id}")

    def show(self):
        """
        Request that this model's view be shown and activated.
        This will be handled by the state manager to show appropriate views.
        """
        if self.state:
            self.state.set_active_model(self.id)
            logger.debug(f"Model {self.id} requested to be shown")
        else:
            logger.warning(f"Cannot show model {self.id} - no state manager attached")
