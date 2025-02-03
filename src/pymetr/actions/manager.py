# src/pymetr/actions/manager.py
from typing import Dict, Any, Type, Optional, TYPE_CHECKING
from .commands import Command, Result
from .history import CommandHistory
from .registry import CommandRegistry

if TYPE_CHECKING:
        from pymetr.state import ApplicationState

from pymetr.logging import logger

class ActionManager:
    """Manages command execution and history"""
    def __init__(self, state: 'ApplicationState'):
        self.state = state
        self.history = CommandHistory()
        self.registry = CommandRegistry()
        self._command_types: Dict[str, Type[Command]] = {}
        logger.debug("ActionManager initialized")
    
    def register_command(self, action_id: str, command_class: Type[Command]) -> None:
        """Register a command type for an action"""
        logger.info(f"Registering command '{action_id}' with class {command_class.__name__}")
        self._command_types[action_id] = command_class
        logger.debug(f"Current registered commands: {list(self._command_types.keys())}")
    
    def execute(self, action_id: str, **params) -> Result:
        """Execute an action with parameters"""
        command_class = self.registry.get_command(action_id)
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
        logger.debug("Attempting to undo last command")
        command = self.history.undo()
        if command and command.undo():
            logger.info(f"Successfully undid command: {command.__class__.__name__}")
            return Result(True)
        logger.warning("Undo failed or no command to undo")
        return Result(False, error="Undo failed")
    
    def redo(self) -> Result:
        """Redo previously undone command"""
        logger.debug("Attempting to redo command")
        command = self.history.redo()
        if command:
            logger.info(f"Redoing command: {command.__class__.__name__}")
            return command.execute()
        logger.warning("No command to redo")
        return Result(False, error="No command to redo")