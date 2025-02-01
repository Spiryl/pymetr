# src/pymetr/views/manager.py
from typing import Dict, Set, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from pymetr.state import ApplicationState

class ViewType(Enum):
    """Enumeration of supported view types"""
    TREE = auto()
    SCRIPT = auto()
    PLOT = auto()
    RESULT = auto()
    INSTRUMENT = auto()

@dataclass
class ViewState:
    """Tracks state for a specific view instance"""
    view_type: ViewType
    model_id: str
    properties: Dict[str, Any] = field(default_factory=dict)
    is_dirty: bool = False
    is_active: bool = False

class ViewManager:
    """Manages view states and synchronization"""
    def __init__(self, state: 'ApplicationState'):
        self.state = state
        self._views: Dict[str, ViewState] = {}
        self._model_views: Dict[str, Set[str]] = {}  # model_id -> view_ids
        self._active_view: Optional[str] = None
        
        # Connect to state signals
        self.state.signals.connect('model_changed', self._handle_model_change)
        self.state.signals.connect('model_deleted', self._handle_model_delete)
        
    def register_view(self, view_id: str, view_type: ViewType, model_id: str) -> ViewState:
        """Register a new view and create its state"""
        view_state = ViewState(view_type=view_type, model_id=model_id)
        self._views[view_id] = view_state
        
        # Track which views are showing this model
        if model_id not in self._model_views:
            self._model_views[model_id] = set()
        self._model_views[model_id].add(view_id)
        
        # Initial view setup
        self._sync_view_with_model(view_id)
        return view_state
    
    def unregister_view(self, view_id: str) -> None:
        """Remove a view registration"""
        if view_id in self._views:
            view_state = self._views[view_id]
            # Remove from model tracking
            if view_state.model_id in self._model_views:
                self._model_views[view_state.model_id].discard(view_id)
            # Clear active view if needed
            if self._active_view == view_id:
                self._active_view = None
            # Remove view state
            del self._views[view_id]
    
    def set_active_view(self, view_id: Optional[str]) -> None:
        """Set the currently active view"""
        if view_id == self._active_view:
            return
            
        # Deactivate current
        if self._active_view and self._active_view in self._views:
            self._views[self._active_view].is_active = False
            
        # Activate new
        self._active_view = view_id
        if view_id and view_id in self._views:
            self._views[view_id].is_active = True
            
        # Notify state of active model change
        if view_id and view_id in self._views:
            self.state.set_active_model(self._views[view_id].model_id)
        else:
            self.state.set_active_model(None)
    
    def get_view_state(self, view_id: str) -> Optional[ViewState]:
        """Get the state for a specific view"""
        return self._views.get(view_id)
    
    def set_view_property(self, view_id: str, key: str, value: Any) -> None:
        """Set a property on a view's state"""
        if view_id in self._views:
            self._views[view_id].properties[key] = value
    
    def mark_dirty(self, view_id: str) -> None:
        """Mark a view as needing update"""
        if view_id in self._views:
            self._views[view_id].is_dirty = True
    
    def _handle_model_change(self, model_id: str, property_name: str, value: Any) -> None:
        """Handle model property changes"""
        if model_id in self._model_views:
            for view_id in self._model_views[model_id]:
                self.mark_dirty(view_id)
    
    def _handle_model_delete(self, model_id: str) -> None:
        """Handle model deletion"""
        if model_id in self._model_views:
            # Get list of affected views
            affected_views = list(self._model_views[model_id])
            # Clean up registrations
            for view_id in affected_views:
                self.unregister_view(view_id)
            # Remove model tracking
            del self._model_views[model_id]
    
    def _sync_view_with_model(self, view_id: str) -> None:
        """Synchronize view state with its model"""
        view_state = self._views.get(view_id)
        if not view_state:
            return
            
        model = self.state.registry.get_model(view_state.model_id)
        if not model:
            return
            
        # Update view properties based on model
        view_state.properties.update({
            'model_type': type(model).__name__,
            'model_properties': model.to_dict().get('properties', {})
        })
        view_state.is_dirty = False