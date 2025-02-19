# Start of C:/Users/rsmith/Documents/GitHub/pymetr/src/pymetr/core/actions.py
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from PySide6.QtWidgets import QMessageBox

from pymetr.services.script import ScriptService
from pymetr.core.logging import logger

class ActionCategory(Enum):
    """Categories for ribbon actions."""
    FILE = auto()
    EDIT = auto()
    RUN = auto()
    ANALYZE = auto()
    PLOT = auto()
    DATA = auto()
    INSTRUMENT = auto()

@dataclass
class MenuItem:
    """Menu item configuration."""
    text: str
    icon: str
    handler: Callable
    tooltip: str = ""

@dataclass
class Action:
    """Base action configuration."""
    id: str
    name: str
    category: ActionCategory
    icon: str
    handler: Callable
    tooltip: str = ""
    menu_items: Dict[str, MenuItem] = field(default_factory=dict)
    enabled: bool = True
    visible: bool = True
    shortcut: str = ""
    
    def can_execute(self, state) -> bool:
        """Check if action can be executed."""
        return self.enabled

class FileActions:
    """File-related actions coordinator."""
    
    @staticmethod
    def new_script(state) -> None:
        """Coordinate script creation between service and state."""
        logger.debug("FileActions: Creating new script")
        parent = getattr(state, '_parent', None)
        logger.debug(f"FileActions: Parent widget exists: {parent is not None}")
        
        success, path, error = ScriptService.create_script(parent)
        logger.debug(f"FileActions: Service result - success: {success}, path: {path}, error: {error}")
        
        if success and path:
            try:
                # Import here to avoid circular import
                from pymetr.models.test import TestScript
                logger.debug("FileActions: Creating script model")
                
                # Create script model in state
                script = state.create_model(TestScript, script_path=path)
                script_name = path.stem
                script.set_property('name', script_name)
                state.set_active_model(script.id)
                logger.debug(f"FileActions: Script model created with ID: {script.id}, name: {script_name}")
            except Exception as e:
                logger.error(f"FileActions: Error creating script model: {e}")
                if parent:
                    QMessageBox.critical(parent, "Error", f"Failed to create script model: {e}")
        elif error and parent:
            logger.error(f"FileActions: Failed to create script: {error}")
            QMessageBox.critical(parent, "Error", f"Failed to create script: {error}")
            
    @staticmethod
    def open_script(state) -> None:
        """Coordinate script opening between service and state."""
        logger.debug("FileActions: Opening script")
        parent = getattr(state, '_parent', None)
        logger.debug(f"FileActions: Parent widget exists: {parent is not None}")
        
        success, path, error = ScriptService.open_script(parent)
        logger.debug(f"FileActions: Service result - success: {success}, path: {path}, error: {error}")
        
        if success and path:
            try:
                from pymetr.models.test import TestScript
                logger.debug("FileActions: Creating script model")
                
                # Add more detailed logging
                logger.debug(f"FileActions: Attempting to create model with path: {path}")
                
                # Create script model in state
                try:
                    script = state.create_model(TestScript, script_path=path)
                    logger.debug(f"FileActions: Script model created successfully")
                except Exception as e:
                    logger.error(f"FileActions: IMMEDIATE create_model error: {type(e).__name__} - {e}")
                    raise
                
                script_name = path.stem
                script.set_property('name', script_name)
                state.set_active_model(script.id)
                logger.debug(f"FileActions: Script model created with ID: {script.id}, name: {script_name}")
            except Exception as e:
                logger.error(f"FileActions: FULL Error creating script model: {type(e).__name__} - {e}")
                import traceback
                logger.error(traceback.format_exc())
                if parent:
                    QMessageBox.critical(parent, "Error", f"Failed to create script model: {e}")
            
    @staticmethod
    def save_script(state) -> None:
        """Coordinate script saving."""
        model = state.get_active_model()
        if model and hasattr(model, 'save'):
            try:
                model.save()
                logger.debug("FileActions: Script saved successfully")
            except Exception as e:
                logger.error(f"FileActions: Failed to save script: {e}")
                parent = getattr(state, '_parent', None)
                if parent:
                    QMessageBox.critical(parent, "Error", f"Failed to save script: {e}")

class RunActions:
    """Script execution actions."""
    
    @staticmethod
    def run_script(state) -> None:
        """Run current script using the Engine."""
        model = state.get_active_model()
        if model and hasattr(model, 'script_path'):
            try:
                logger.debug(f"RunActions: Running script for model {model.id}")
                # Use the engine stored on the state to run the test script.
                state.engine.run_test_script(model.script_path)
            except Exception as e:
                logger.error(f"RunActions: Error running script: {e}")
                parent = getattr(state, '_parent', None)
                if parent:
                    QMessageBox.critical(parent, "Error", f"Failed to run script: {e}")
            
    @staticmethod
    def stop_script(state) -> None:
        """Stop current script using the Engine."""
        try:
            if state.engine and state.engine.script_runner is not None:
                logger.debug("RunActions: Stopping script")
                state.engine.script_runner.stop()
            else:
                logger.debug("RunActions: No active script runner found to stop")
        except Exception as e:
            logger.error(f"RunActions: Error stopping script: {e}")
            parent = getattr(state, '_parent', None)
            if parent:
                QMessageBox.critical(parent, "Error", f"Failed to stop script: {e}")

class InstrumentActions:
    """Instrument-related actions."""
    
    @staticmethod
    def discover_instruments(state) -> None:
        """Open instrument discovery dialog."""
        parent = getattr(state, '_parent', None)
        if parent:
            try:
                from pymetr.views.widgets.discovery_view import DiscoveryDialog
                logger.debug("InstrumentActions: Launching discovery dialog")
                dialog = DiscoveryDialog(state, parent)
                if dialog.exec_():
                    info = dialog.result_info
                    if info:
                        try:
                            from pymetr.models.device import Device
                            device = state.create_model(
                                Device,
                                manufacturer=info.get('manufacturer'),
                                model=info.get('model'),
                                serial_number=info.get('serial'),
                                firmware=info.get('firmware'),
                                resource=info.get('resource')
                            )
                            state.set_active_model(device.id)
                            logger.debug(f"InstrumentActions: Device model created with ID: {device.id}")
                        except Exception as e:
                            logger.error(f"InstrumentActions: Error creating device: {e}")
                            QMessageBox.critical(parent, "Error", f"Failed to create device: {e}")
            except Exception as e:
                logger.error(f"InstrumentActions: Failed to open discovery dialog: {e}")
                QMessageBox.critical(parent, "Error", f"Failed to open discovery dialog: {e}")

# Define standard actions
STANDARD_ACTIONS = {
    # File actions
    'new_script': Action(
        id='new_script',
        name='New',
        category=ActionCategory.FILE,
        icon='new.png',
        handler=FileActions.new_script,
        menu_items={
            'script': MenuItem('New Script', 'new_script.png', FileActions.new_script),
            'suite': MenuItem('New Suite', 'new_suite.png', lambda s: None)
        }
    ),
    'open_script': Action(
        id='open_script',
        name='Open',
        category=ActionCategory.FILE,
        icon='open.png',
        handler=FileActions.open_script,
        menu_items={
            'script': MenuItem('Open Script', 'open_script.png', FileActions.open_script),
            'suite': MenuItem('Open Suite', 'open_suite.png', lambda s: None)
        }
    ),
    'save_script': Action(
        id='save_script',
        name='Save',
        category=ActionCategory.FILE,
        icon='save.png',
        handler=FileActions.save_script
    ),
    
    # Run actions
    'run_script': Action(
        id='run_script',
        name='Run',
        category=ActionCategory.RUN,
        icon='run.png',
        handler=RunActions.run_script
    ),
    'stop_script': Action(
        id='stop_script',
        name='Stop',
        category=ActionCategory.RUN,
        icon='stop.png',
        handler=RunActions.stop_script,
        enabled=False
    ),
    
    # Instrument actions
    'discover_instruments': Action(
        id='discover_instruments',
        name='Connect',
        category=ActionCategory.INSTRUMENT,
        icon='instruments.png',
        handler=InstrumentActions.discover_instruments
    )
}
# End of C:/Users/rsmith/Documents/GitHub/pymetr/src/pymetr/core/actions.py
