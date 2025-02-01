# src/models/base.py
from typing import Dict, Any, Optional
import uuid

class BaseModel:
    """Base class for all models in the application"""
    def __init__(self, model_id: Optional[str] = None):
        self._id = model_id or str(uuid.uuid4())
        self._properties: Dict[str, Any] = {}
        
    @property
    def id(self) -> str:
        return self._id
        
    def get_property(self, key: str, default: Any = None) -> Any:
        return self._properties.get(key, default)
        
    def set_property(self, key: str, value: Any) -> None:
        self._properties[key] = value
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for serialization"""
        return {
            'id': self._id,
            'properties': self._properties.copy()
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """Create model instance from dictionary"""
        instance = cls(model_id=data['id'])
        instance._properties = data.get('properties', {}).copy()
        return instance