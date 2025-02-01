# src/pymetr/actions/manager.py
from typing import Dict, Any, Type, Optional
from .commands import Command, Result
from .history import CommandHistory

from pymetr.state import ApplicationState

class ActionManager:
    """Manages command execution and history"""
    def __init__(self, state: 'ApplicationState'):
        self.state = state
        self.history = CommandHistory()
        self._command_types: Dict[str, Type[Command]] = {}
    
    def register_command(self, action_id: str, command_class: Type[Command]) -> None:
        """Register a command type for an action"""
        self._command_types[action_id] = command_class
    
    def execute(self, action_id: str, **params) -> Result:
        """Execute an action with parameters"""
        command_class = self._command_types.get(action_id)
        if not command_class:
            return Result(False, error=f"Unknown action: {action_id}")
            
        try:
            command = command_class(self.state, **params)
            if command.can_execute():
                result = command.execute()
                if result.success:
                    self.history.push(command)
                return result
            return Result(False, error="Command validation failed")
        except Exception as e:
            return Result(False, error=str(e))
    
    def undo(self) -> Result:
        """Undo last command"""
        command = self.history.undo()
        if command and command.undo():
            return Result(True)
        return Result(False, error="Undo failed")
    
    def redo(self) -> Result:
        """Redo previously undone command"""
        command = self.history.redo()
        if command:
            return command.execute()
        return Result(False, error="No command to redo")