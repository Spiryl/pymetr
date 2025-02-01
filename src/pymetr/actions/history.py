# src/pymetr/actions/history.py
from typing import List, Optional
from .commands import Command

class CommandHistory:
    """Manages command history for undo/redo"""
    def __init__(self, max_size: int = 100):
        self._history: List[Command] = []
        self._current: int = -1
        self._max_size = max_size
    
    def push(self, command: Command) -> None:
        """Add command to history"""
        # Clear any redoable commands
        if self._current < len(self._history) - 1:
            self._history = self._history[:self._current + 1]
            
        self._history.append(command)
        self._current += 1
        
        # Maintain size limit
        if len(self._history) > self._max_size:
            self._history.pop(0)
            self._current -= 1
    
    def can_undo(self) -> bool:
        return self._current >= 0
    
    def can_redo(self) -> bool:
        return self._current < len(self._history) - 1
    
    def undo(self) -> Optional[Command]:
        """Get the command to undo"""
        if self.can_undo():
            command = self._history[self._current]
            self._current -= 1
            return command
        return None
    
    def redo(self) -> Optional[Command]:
        """Get the command to redo"""
        if self.can_redo():
            self._current += 1
            return self._history[self._current]
        return None