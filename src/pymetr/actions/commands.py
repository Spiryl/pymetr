# src/pymetr/actions/commands.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass
from PySide6.QtCore import Qt

if TYPE_CHECKING:
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
    
from .commands import Command, Result
from pymetr.models.device import Device
from pymetr.views.windows.instrument_discovery import InstrumentDiscoveryDialog
from PySide6.QtWidgets import QApplication

class DiscoverInstrumentsCommand(Command):
    """
    1) Opens the discovery dialog
    2) If user selects an instrument, create an Instrument model in the registry
    3) Emit a signal to let MainWindow (or any observer) know
    """

    def execute(self) -> Result:
        dialog = InstrumentDiscoveryDialog(parent=QApplication.activeWindow())
        ret = dialog.exec_()
        if ret != dialog.Accepted or not dialog.selected_instrument:
            return Result(False, error="No instrument selected.")

        selected = dialog.selected_instrument  # dict with manufacturer, model, resource, driver_info, etc.

        # Build a new device model
        device = Device(
            manufacturer=selected["manufacturer"],
            model=selected["model"],
            serial_number=selected["serial"],
            firmware=selected["firmware"],
            resource=selected["resource"]
            # optionally: pass an id= or let it auto-generate
        )

        # Register in your state registry
        # self.state.registry.register(instrument)

        # Now let the MainWindow (or whomever) know
        self.state.signals.emit("instrument_connected", device.id)

        return Result(True)

    def undo(self) -> bool:
        # Typically not used here
        return True