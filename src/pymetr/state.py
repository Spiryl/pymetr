# src/pymetr/state.py
from typing import Dict, Any, Optional, List, Callable, Type
from .registry import ModelRegistry
from .models.base import BaseModel

class SignalManager:
    """Manages signal/event handling"""
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        
    def connect(self, signal: str, handler: Callable) -> None:
        """Connect a handler to a signal"""
        if signal not in self._handlers:
            self._handlers[signal] = []
        self._handlers[signal].append(handler)
        
    def emit(self, signal: str, *args, **kwargs) -> None:
        """Emit a signal with arguments"""
        if signal in self._handlers:
            for handler in self._handlers[signal]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    # In real implementation, we'd want proper logging here
                    print(f"Error in signal handler: {e}")
                    
    def disconnect(self, signal: str, handler: Callable) -> None:
        """Disconnect a handler from a signal"""
        if signal in self._handlers:
            self._handlers[signal] = [h for h in self._handlers[signal] if h != handler]

class ApplicationState:
    """Centralizes application state management"""
    def __init__(self):
        self.registry = ModelRegistry()
        self.signals = SignalManager()
        self._active_model_id: Optional[str] = None
        
    def create_model(self, model_type: Type[BaseModel], **kwargs) -> BaseModel:
        """Create and register a new model"""
        model = model_type(**kwargs)
        self.registry.register(model)
        self.signals.emit('model_created', model.id, type(model).__name__)
        return model
        
    def delete_model(self, model_id: str) -> None:
        """Delete a model and its relationships"""
        model = self.registry.get_model(model_id)
        if model:
            # First emit signal for cleanup
            self.signals.emit('model_deleting', model_id, type(model).__name__)
            # Remove from registry
            self.registry.unregister(model_id)
            # Notify deletion complete
            self.signals.emit('model_deleted', model_id)
            
    def set_active_model(self, model_id: Optional[str]) -> None:
        """Set the currently active model"""
        old_id = self._active_model_id
        self._active_model_id = model_id
        self.signals.emit('active_model_changed', model_id, old_id)
        
    def get_active_model(self) -> Optional[BaseModel]:
        """Get the currently active model"""
        if self._active_model_id:
            return self.registry.get_model(self._active_model_id)
        return None
        
    def link_models(self, parent_id: str, child_id: str) -> None:
        """Create a relationship between models"""
        self.registry.link(parent_id, child_id)
        self.signals.emit('models_linked', parent_id, child_id)
        
    def unlink_models(self, parent_id: str, child_id: str) -> None:
        """Remove a relationship between models"""
        self.registry.unlink(parent_id, child_id)
        self.signals.emit('models_unlinked', parent_id, child_id)
        
    def get_model_children(self, model_id: str) -> List[BaseModel]:
        """Get all child models for a given model"""
        child_ids = self.registry.get_children(model_id)
        return [self.registry.get_model(cid) for cid in child_ids if self.registry.get_model(cid)]
        
    def notify_model_changed(self, model_id: str, property_name: str, value: Any) -> None:
        """Notify system of model property changes"""
        self.signals.emit('model_changed', model_id, property_name, value)