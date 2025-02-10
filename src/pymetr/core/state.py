# state.py

from typing import Dict, Optional, Type, TypeVar, List, Any
from PySide6.QtCore import QObject, Signal, Slot, QThread, Qt, QMetaObject, Q_ARG
from pymetr.models.base import BaseModel
from pymetr.core.engine import Engine
from pymetr.core.logging import logger

T = TypeVar('T', bound=BaseModel)

_global_state = None

def set_global_state(state):
    global _global_state
    _global_state = state

def get_global_state():
    global _global_state
    return _global_state

class ApplicationState(QObject):
    # Signals
    model_registered = Signal(str)           # model_id
    model_changed = Signal(str, str, object) # model_id, prop_name, value
    models_linked = Signal(str, str)         # parent_id, child_id
    active_model_changed = Signal(str)       # model_id
    active_test_changed = Signal(str)        # model_id
    model_registration_requested = Signal(str, str)  # model_id, model_type_name

    def __init__(self):
        super().__init__()
        self._models: Dict[str, BaseModel] = {}
        self._pending_models: Dict[str, BaseModel] = {}
        self._relationships: Dict[str, set[str]] = {}  # parent_id -> set of child_ids
        self._active_model_id: Optional[str] = None
        self._active_test_id: Optional[str] = None
        self._parent: Optional[QObject] = None 
        self.engine = Engine(self)
        
        # Connect the registration request signal
        self.model_registration_requested.connect(self._handle_registration_request)
        logger.debug("ApplicationState initialized with Engine.")

    def set_parent(self, parent: QObject):
        """Optionally store a reference to a parent widget for dialogs."""
        self._parent = parent

    def register_model(self, model: BaseModel) -> None:
        """Register a model - keep it simple and in the main thread."""
        if model.id not in self._models:
            # Let the model know its state manager
            model.state = self
            self._models[model.id] = model

            # Connect signals
            model.property_changed.connect(self._handle_model_change)
            model.child_added.connect(self._handle_child_added)

            self.model_registered.emit(model.id)
            logger.debug(f"Registered model {model.id}")

    @Slot(str, str)
    def _handle_registration_request(self, model_id: str, model_type: str) -> None:
        """Handle registration requests from other threads."""
        if model_id in self._pending_models:
            model = self._pending_models.pop(model_id)
            self._register_model_internal(model)
        else:
            logger.error(f"Model {model_id} not found in pending registrations")

    def _register_model_internal(self, model: BaseModel) -> None:
        """Internal registration that always runs in main thread."""
        if model.id not in self._models:
            # Move model to main thread if needed
            if model.thread() != self.thread():
                model.moveToThread(self.thread())

            # Let the model know its state manager
            model.state = self
            self._models[model.id] = model

            # Connect to type-specific signals
            model.property_changed_str.connect(self._handle_model_change)
            model.property_changed_float.connect(self._handle_model_change)
            model.property_changed_int.connect(self._handle_model_change)
            model.property_changed_bool.connect(self._handle_model_change)
            model.child_added.connect(self._handle_child_added)

            self.model_registered.emit(model.id)
            logger.debug(f"Registered model {model.id}")

    def link_models(self, parent_id: str, child_id: str) -> None:
        """
        Create a relationship between models.
        """
        if QThread.currentThread() != self.thread():
            QMetaObject.invokeMethod(
                self,
                "_link_models_internal",
                Qt.QueuedConnection,
                Q_ARG(str, parent_id),
                Q_ARG(str, child_id)
            )
        else:
            self._link_models_internal(parent_id, child_id)

    @Slot(str, str)
    def _link_models_internal(self, parent_id: str, child_id: str) -> None:
        """Internal linking in main thread."""
        if parent_id not in self._relationships:
            self._relationships[parent_id] = set()
        self._relationships[parent_id].add(child_id)
        self.models_linked.emit(parent_id, child_id)
        logger.debug(f"Linked model {child_id} to parent {parent_id}")

    def unlink_models(self, parent_id: str, child_id: str) -> None:
        """Remove a relationship between models."""
        if parent_id in self._relationships:
            self._relationships[parent_id].discard(child_id)
            logger.debug(f"Unlinked model {child_id} from parent {parent_id}")

    def get_model(self, model_id: str) -> Optional[BaseModel]:
        """Get a model by ID."""
        return self._models.get(model_id)

    def get_models_by_type(self, model_type: Type[T]) -> List[T]:
        """Get all models of a specific type."""
        return [
            model for model in self._models.values()
            if isinstance(model, model_type)
        ]

    def get_children(self, parent_id: str) -> List[BaseModel]:
        """Get all child models for a parent."""
        child_ids = self._relationships.get(parent_id, set())
        return [
            self._models[child_id]
            for child_id in child_ids
            if child_id in self._models
        ]

    def get_parent(self, child_id: str) -> Optional[BaseModel]:
        """Get parent model of a child."""
        for parent_id, children in self._relationships.items():
            if child_id in children:
                return self._models.get(parent_id)
        return None

    @Slot(str, str, object)
    def _handle_model_change(self, model_id: str, prop: str, value: Any) -> None:
        """Handle property changes."""
        self.model_changed.emit(model_id, prop, value)

    @Slot(str, str)
    def _handle_child_added(self, parent_id: str, child_id: str) -> None:
        """A model had a child added -> link them."""
        self.link_models(parent_id, child_id)

    def set_active_test(self, model_id: Optional[str]) -> None:
        """Set the currently active test."""
        if model_id != self._active_test_id:
            self._active_test_id = model_id
            self.active_test_changed.emit(model_id)
            logger.debug(f"Active test changed to {model_id}")

    def get_active_test(self) -> Optional[BaseModel]:
        """Get the currently active test."""
        if self._active_test_id:
            return self._models.get(self._active_test_id)
        return None
    
    def set_active_model(self, model_id: Optional[str]) -> None:
        """Set the currently active model."""
        if model_id != self._active_model_id:
            self._active_model_id = model_id
            self.active_model_changed.emit(model_id)
            logger.debug(f"Active model changed to {model_id}")

    def get_active_model(self) -> Optional[BaseModel]:
        """Get the currently active model."""
        if self._active_model_id:
            return self._models.get(self._active_model_id)
        return None

    def create_model(self, model_class: Type[T], **kwargs) -> T:
        """
        Create and register a new model. (Convenience method)
        """
        model = model_class(**kwargs)
        self.register_model(model)
        return model
    
    def remove_model(self, model_id: str) -> None:
        """Remove a model and clean up its relationships."""
        if model_id in self._models:
            # Remove as child from any parent
            parent = self.get_parent(model_id)
            if parent:
                self.unlink_models(parent.id, model_id)
                
            # Remove any children it might have
            if model_id in self._relationships:
                child_ids = list(self._relationships[model_id])
                for child_id in child_ids:
                    self.remove_model(child_id)
                del self._relationships[model_id]
                
            # Remove the model itself
            model = self._models[model_id]
            model.deleteLater()
            del self._models[model_id]
            logger.debug(f"Removed model {model_id}")