# Start of C:/Users/rsmith/Documents/GitHub/pymetr/src/pymetr/core/actions.py
from dataclasses import dataclass, field
from enum import Enum, auto
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from PySide6.QtWidgets import QMessageBox

from pymetr.models.test import TestSuite
from pymetr.services.script_service import ScriptService
from pymetr.services.file_service import FileService
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
    WINDOW = auto()
    OPTIONS = auto()
    REPORT = auto()

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
    def new_suite(state) -> None:
        """Create a new empty test suite."""
        try:
            from pymetr.models.test import TestSuite
            # Create basic suite with just a name
            suite = state.create_model(TestSuite, name="New Test Suite")
            state.set_active_model(suite.id)
            logger.debug(f"Created new test suite with ID: {suite.id}")
            
            # Could add a default test script folder here if desired:
            # script_group = state.create_model(TestGroup, name="Scripts")
            # state.link_models(suite.id, script_group.id)
            
        except Exception as e:
            logger.error(f"Error creating test suite: {e}")
            parent = getattr(state, '_parent', None)
            if parent:
                QMessageBox.critical(parent, "Error", f"Failed to create test suite: {e}")

    @staticmethod
    def open_suite(state) -> None:
        """Open an existing test suite."""
        parent = getattr(state, '_parent', None)
        success, path, error = FileService.open_suite(parent)
        
        if success and path:
            try:
                suite_id = FileService.import_model_data(path, state)
                if suite_id:
                    state.set_active_model(suite_id)
                    logger.debug(f"Opened test suite from {path}")
            except Exception as e:
                logger.error(f"Error opening suite: {e}")
                if parent:
                    QMessageBox.critical(parent, "Error", f"Failed to open suite: {e}")
        elif error and parent:
            QMessageBox.critical(parent, "Error", f"Failed to open suite: {error}")

    @staticmethod
    def save_suite(state) -> None:
        """Save current test suite."""
        model = state.get_active_model()
        if model and isinstance(model, TestSuite):
            parent = getattr(state, '_parent', None)
            success, path, error = FileService.save_suite(model, parent)
            
            if not success and error and parent:
                QMessageBox.critical(parent, "Error", f"Failed to save suite: {error}")

    @staticmethod 
    def add_script_to_suite(state, suite_id: str) -> None:
        """Add an existing script to a suite."""
        try:
            # Let user select a script file
            parent = getattr(state, '_parent', None)
            success, path, error = ScriptService.open_script(parent)
            
            if success and path:
                from pymetr.models.test import TestScript
                # Create script model
                script = state.create_model(TestScript, script_path=path)
                script.set_property('name', path.stem)
                
                # Link to suite
                state.link_models(suite_id, script.id)
                logger.debug(f"Added script {script.id} to suite {suite_id}")
                
        except Exception as e:
            logger.error(f"Error adding script to suite: {e}")
            if parent:
                QMessageBox.critical(parent, "Error", f"Failed to add script: {e}")

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
        logger.debug("InstrumentActions: Initiating instrument discovery")
        parent = getattr(state, '_parent', None)
        
        try:
            from pymetr.ui.dialogs.discovery_dialog import DiscoveryDialog
            from PySide6.QtWidgets import QDialog  # Import QDialog to access standard return values
            
            dialog = DiscoveryDialog(state, parent=parent)
            
            if dialog.exec() == QDialog.Accepted:  # Use QDialog.Accepted instead of dialog.Accepted
                # User selected an instrument
                info = dialog.result_info
                if info:
                    device = state.connect_instrument(info)
                    if device:
                        logger.info(f"Successfully connected to {device.get_property('model')}")
                        # Set as active model so it's shown in the UI
                        state.set_active_model(device.id)
                        
        except Exception as e:
            logger.error(f"Error in discover_instruments: {e}")
            if parent:
                QMessageBox.critical(
                    parent,
                    "Discovery Error",
                    f"Failed to discover instruments: {str(e)}"
                )

    @staticmethod
    def connect_instrument(state) -> None:
        """Open manual connection dialog."""
        logger.debug("InstrumentActions: Opening manual connection dialog")
        parent = getattr(state, '_parent', None)
        
        try:
            from pymetr.ui.dialogs.connection_dialog import ConnectionDialog
            from PySide6.QtWidgets import QDialog  # Import QDialog for standard return values
            
            dialog = ConnectionDialog(parent)
            
            if dialog.exec() == QDialog.Accepted:  # Use QDialog.Accepted
                # User entered connection info
                info = dialog.result_info
                if info:
                    device = state.connect_instrument(info)
                    if device:
                        logger.info(f"Successfully connected to {device.get_property('resource')}")
                        # Set as active model so it's shown in the UI
                        state.set_active_model(device.id)
                        
        except Exception as e:
            logger.error(f"Error in manual connection: {e}")
            if parent:
                QMessageBox.critical(
                    parent,
                    "Connection Error",
                    f"Failed to connect to instrument: {str(e)}"
                )

    @staticmethod
    def disconnect_instrument(state) -> None:
        """Disconnect the active instrument."""
        logger.debug("InstrumentActions: Disconnecting instrument")
        
        model = state.get_active_model()
        if model and hasattr(model, 'disconnect'):
            try:
                model.disconnect()
                logger.info(f"Disconnected instrument {model.get_property('name')}")
            except Exception as e:
                logger.error(f"Error disconnecting instrument: {e}")
                parent = getattr(state, '_parent', None)
                if parent:
                    QMessageBox.critical(
                        parent,
                        "Disconnection Error",
                        f"Failed to disconnect instrument: {str(e)}"
                    )
# Define standard actions
STANDARD_ACTIONS = {
    # File actions
    'new_suite': Action(
        id='new_suite',
        name='New Suite',
        category=ActionCategory.FILE,
        icon='new_suite.png',
        handler=FileActions.new_suite
    ),
    'open_suite': Action(
        id='open_suite',
        name='Open Suite',
        category=ActionCategory.FILE,
        icon='open_suite.png',
        handler=FileActions.open_suite
    ),
    'save_suite': Action(
        id='save_suite',
        name='Save Suite',
        category=ActionCategory.FILE,
        icon='save.png',
        handler=FileActions.save_suite
    ),
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
        name='Discover',
        category=ActionCategory.INSTRUMENT,
        icon='discover.png',
        handler=InstrumentActions.discover_instruments,
        tooltip="Discover available instruments"
    ),
    'connect_instrument': Action(
        id='connect_instrument',
        name='Connect',
        category=ActionCategory.INSTRUMENT,
        icon='connect.png',
        handler=InstrumentActions.connect_instrument,
        tooltip="Manually connect to an instrument"
    ),
    'disconnect_instrument': Action(
        id='disconnect_instrument',
        name='Disconnect',
        category=ActionCategory.INSTRUMENT,
        icon='disconnect.png',
        handler=InstrumentActions.disconnect_instrument,
        tooltip="Disconnect the current instrument"
    )
}
# End of C:/Users/rsmith/Documents/GitHub/pymetr/src/pymetr/core/actions.py
