# src/pymetr/actions/commands.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

from pymetr.state import ApplicationState

@dataclass
class Result:
    """Command execution result"""
    success: bool
    data: Dict[str, Any] = None
    error: str = ""

class Command(ABC):
    """Base command interface"""
    def __init__(self, state: 'ApplicationState'):
        self.state = state
        self._stored_state: Dict[str, Any] = {}
    
    @abstractmethod
    def execute(self) -> Result:
        """Execute the command"""
        pass
        
    @abstractmethod
    def undo(self) -> bool:
        """Reverse the command effects"""
        pass
    
    def can_execute(self) -> bool:
        """Check if command can be executed"""
        try:
            return self.validate()
        except Exception as e:
            return False
    
    def validate(self) -> bool:
        """Validate command preconditions"""
        return True

class ModelCommand(Command):
    """Base for commands that modify models"""
    def __init__(self, state: 'ApplicationState', model_id: str):
        super().__init__(state)
        self.model_id = model_id
        self._previous_state: Optional[Dict[str, Any]] = None
        
    def store_model_state(self):
        """Store model state for undo"""
        model = self.state.registry.get_model(self.model_id)
        if model:
            self._previous_state = model.to_dict()
            
    def restore_model_state(self) -> bool:
        """Restore model to previous state"""
        if self._previous_state and self.model_id:
            model = self.state.registry.get_model(self.model_id)
            if model:
                for key, value in self._previous_state.get('properties', {}).items():
                    model.set_property(key, value)
                return True
        return False