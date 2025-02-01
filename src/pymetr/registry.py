# src/registry.py
from typing import Dict, Set, Optional, List, TypeVar, Type
from .models.base import BaseModel

T = TypeVar('T', bound=BaseModel)

class ModelRegistry:
    """Central registry for all application models"""
    def __init__(self):
        self._models: Dict[str, BaseModel] = {}
        self._relationships: Dict[str, Set[str]] = {}
        self._type_index: Dict[str, Set[str]] = {}
        
    def register(self, model: BaseModel) -> None:
        """Register a model in the registry"""
        self._models[model.id] = model
        model_type = type(model).__name__
        if model_type not in self._type_index:
            self._type_index[model_type] = set()
        self._type_index[model_type].add(model.id)
        
    def unregister(self, model_id: str) -> None:
        """Remove a model from the registry"""
        if model_id in self._models:
            model = self._models[model_id]
            model_type = type(model).__name__
            self._type_index[model_type].discard(model_id)
            del self._models[model_id]
            # Cleanup relationships
            self._relationships.pop(model_id, None)
            for parent_id in self._relationships:
                self._relationships[parent_id].discard(model_id)
                
    def get_model(self, model_id: str) -> Optional[BaseModel]:
        """Retrieve a model by ID"""
        return self._models.get(model_id)
        
    def get_models_by_type(self, model_type: Type[T]) -> List[T]:
        """Get all models of a specific type"""
        type_name = model_type.__name__
        if type_name in self._type_index:
            return [self._models[mid] for mid in self._type_index[type_name]]
        return []
        
    def link(self, parent_id: str, child_id: str) -> None:
        """Create a relationship between models"""
        if parent_id not in self._relationships:
            self._relationships[parent_id] = set()
        self._relationships[parent_id].add(child_id)
        
    def unlink(self, parent_id: str, child_id: str) -> None:
        """Remove a relationship between models"""
        if parent_id in self._relationships:
            self._relationships[parent_id].discard(child_id)
            
    def get_children(self, parent_id: str) -> List[str]:
        """Get all child models for a parent"""
        return list(self._relationships.get(parent_id, set()))