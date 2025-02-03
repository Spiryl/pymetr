# src/pymetr/state.py
import importlib
import os
from typing import Dict, Any, Optional, List, Callable, Type

from pymetr.logging import logger
from pymetr.drivers.base import Instrument
from pymetr.workers.discovery_thread import DiscoveryThread
from .actions.registry import CommandRegistry
from .registry import ModelRegistry
from .engine import Engine
from .models.base import BaseModel
from .models.test_script import TestScript
from .views.manager import ViewManager
from .actions.manager import ActionManager

class SignalManager:
    """Manages signal/event handling"""
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        logger.debug("SignalManager initialized with empty handlers.")

    def connect(self, signal: str, handler: Callable) -> None:
        """Connect a handler to a signal"""
        handler_name = getattr(handler, '__name__', repr(handler))
        logger.debug(f"Connecting handler '{handler_name}' to signal '{signal}'.")
        if signal not in self._handlers:
            self._handlers[signal] = []
        self._handlers[signal].append(handler)
        logger.debug(f"Handler '{handler_name}' connected to signal '{signal}' successfully.")

    def emit(self, signal: str, *args, **kwargs) -> None:
        """Emit a signal with arguments"""
        logger.debug(f"Emitting signal '{signal}' with args: {args} and kwargs: {kwargs}.")
        if signal in self._handlers:
            for handler in self._handlers[signal]:
                try:
                    handler(*args, **kwargs)
                    handler_name = getattr(handler, '__name__', repr(handler))
                    logger.debug(f"Handler '{handler_name}' for signal '{signal}' executed successfully.")
                except Exception as e:
                    logger.exception(f"Error in signal handler '{handler}' for signal '{signal}': {e}")
        else:
            logger.debug(f"No handlers connected for signal '{signal}'.")

    def disconnect(self, signal: str, handler: Callable) -> None:
        """Disconnect a handler from a signal"""
        logger.debug(f"Disconnecting handler '{handler}' from signal '{signal}'.")
        if signal in self._handlers:
            original_count = len(self._handlers[signal])
            self._handlers[signal] = [h for h in self._handlers[signal] if h != handler]
            new_count = len(self._handlers[signal])
            logger.debug(f"Handler disconnected. {original_count - new_count} handler(s) removed from signal '{signal}'.")

class ApplicationState:
    """Centralizes application state management"""
    def __init__(self):
        logger.debug("Initializing ApplicationState.")
        self.registry = ModelRegistry()
        self.signals = SignalManager()
        self.views = ViewManager(self)
        self.actions = ActionManager(self)
        self.engine = Engine(self)
        self._initialize_commands()
        self._active_model_id: Optional[str] = None
        self._discovery_thread = None  # keep a reference so it's not garbage-collected
        logger.debug("ApplicationState initialized successfully.")

    def create_model(self, model_or_class, **kwargs) -> BaseModel:
        """
        Create and register a new model.
        
        If `model_or_class` is a subclass of BaseModel, it will be instantiated
        with the provided kwargs. If it is already an instance of BaseModel,
        it will simply be registered.
        """
        if isinstance(model_or_class, type) and issubclass(model_or_class, BaseModel):
            model = model_or_class(**kwargs)
        elif isinstance(model_or_class, BaseModel):
            model = model_or_class
        else:
            raise TypeError("create_model must be called with a subclass of BaseModel or an instance of BaseModel")
        
        self.registry.register(model)
        logger.debug(f"Model '{model.id}' registered successfully.")
        self.signals.emit('model_created', model.id, type(model).__name__)
        logger.debug(f"'model_created' signal emitted for model '{model.id}'.")
        return model
        
    def delete_model(self, model_id: str) -> None:
        """Delete a model and its relationships"""
        logger.debug(f"Deleting model with id '{model_id}'.")
        model = self.registry.get_model(model_id)
        if model:
            logger.debug(f"Model found. Emitting 'model_deleting' signal for model '{model_id}'.")
            self.signals.emit('model_deleting', model_id, type(model).__name__)
            self.registry.unregister(model_id)
            logger.debug(f"Model '{model_id}' unregistered successfully.")
            self.signals.emit('model_deleted', model_id)
            logger.debug(f"'model_deleted' signal emitted for model '{model_id}'.")
        else:
            logger.warning(f"Attempted to delete non-existent model with id '{model_id}'.")

    def set_active_model(self, model_id: Optional[str]) -> None:
        """Set the currently active model"""
        old_id = self._active_model_id
        self._active_model_id = model_id
        logger.debug(f"Active model changed from '{old_id}' to '{model_id}'. Emitting 'active_model_changed' signal.")
        self.signals.emit('active_model_changed', model_id, old_id)
        
    def get_active_model(self) -> Optional[BaseModel]:
        """Get the currently active model"""
        logger.debug("Retrieving the active model.")
        if self._active_model_id:
            model = self.registry.get_model(self._active_model_id)
            logger.debug(f"Active model retrieved: '{model.id if model else None}'.")
            return model
        logger.debug("No active model set.")
        return None
        
    def link_models(self, parent_id: str, child_id: str) -> None:
        """Create a relationship between models"""
        logger.debug(f"Linking parent model '{parent_id}' with child model '{child_id}'.")
        self.registry.link(parent_id, child_id)
        self.signals.emit('models_linked', parent_id, child_id)
        logger.debug(f"'models_linked' signal emitted for parent '{parent_id}' and child '{child_id}'.")
        
    def unlink_models(self, parent_id: str, child_id: str) -> None:
        """Remove a relationship between models"""
        logger.debug(f"Unlinking child model '{child_id}' from parent model '{parent_id}'.")
        self.registry.unlink(parent_id, child_id)
        self.signals.emit('models_unlinked', parent_id, child_id)
        logger.debug(f"'models_unlinked' signal emitted for parent '{parent_id}' and child '{child_id}'.")
        
    def get_model_children(self, model_id: str) -> List[BaseModel]:
        """Get all child models for a given model"""
        logger.debug(f"Retrieving children for model '{model_id}'.")
        child_ids = self.registry.get_children(model_id)
        children = [self.registry.get_model(cid) for cid in child_ids if self.registry.get_model(cid)]
        logger.debug(f"Found {len(children)} child(ren) for model '{model_id}'.")
        return children
        
    def notify_model_changed(self, model_id: str, property_name: str, value: Any) -> None:
        """Notify system of model property changes"""
        logger.debug(f"Notifying change for model '{model_id}': property '{property_name}' changed to {value}.")
        self.signals.emit('model_changed', model_id, property_name, value)
        logger.debug(f"'model_changed' signal emitted for model '{model_id}'.")

    def _initialize_commands(self):
        """Initialize commands and connect engine signals"""
        # Auto-discover commands
        self.command_registry = CommandRegistry()
        commands = self.command_registry.get_available_commands()
        logger.info(f"Discovered commands: {list(commands.keys())}")
        
        # Connect engine signals to commands
        self.engine.script_started.connect(self._handle_script_started)
        self.engine.script_finished.connect(self._handle_script_finished)
        self.engine.progressChanged.connect(self._handle_progress_update)

    def _handle_progress_update(self, test_id: str, percent: float, message: str):
        """Handle progress updates coming from the engine."""
        logger.debug(f"Received progress update for {test_id}: {percent}% - {message}")
        # You can either notify the model directly or execute an update command.
        self.notify_model_changed(test_id, 'progress', percent)
        # Optionally, if you want to update the message or status as well:
        if message:
            self.notify_model_changed(test_id, 'progressMessage', message)
                    
    def _handle_script_started(self, test_id: str):
        """Handle script start"""
        logger.debug(f"Script started: {test_id}")
        self.actions.execute("update_script_progress", 
                            test_id=test_id,
                            status="Running",
                            percent=0)

    def _handle_script_finished(self, test_id: str, success: bool, error_msg: str):
        """Handle script completion"""
        status = "Pass" if success else "Error"
        logger.debug(f"Script finished: {test_id} -> {status}")
        self.actions.execute("update_script_progress",
                            test_id=test_id,
                            status=status,
                            percent=100)

    def find_test_by_id(self, test_id: str) -> Optional[TestScript]:
        """Find a TestScript by ID"""
        model = self.registry.get_model(test_id)
        if isinstance(model, TestScript):
            return model
        return None
            
    def find_instruments(self):
        """Launch separate thread for instrument discovery."""
        self.signals.emit("locating_instruments")

        if self._discovery_thread:
            # If thread exists, make sure it's stopped
            self._discovery_thread.stop()
            self._discovery_thread = None

        # Create and start new thread
        self._discovery_thread = DiscoveryThread()
        self._discovery_thread.discovered.connect(self._on_discovery_finished)
        self._discovery_thread.error.connect(self._on_discovery_error)
        self._discovery_thread.start()

    def _on_discovery_finished(self, discovered: dict):
        """Handle discovery completion"""
        logger.debug(f"Discovery finished with {len(discovered)} devices")
        # Keep thread reference until we're done with results
        self.signals.emit("instruments_discovered", discovered)
        # Now safe to clear thread
        self._discovery_thread.stop()
        self._discovery_thread = None

    def _on_discovery_error(self, msg: str):
        """Handle discovery errors"""
        logger.error(f"Discovery error: {msg}")
        self.signals.emit("error", f"Instrument discovery failed: {msg}")
        self._discovery_thread.stop()
        self._discovery_thread = None

    def connect_instrument(self, instrument_info: dict):
        """
        Takes the discovered instrument info dict, creates & registers
        the Device model, then attempts to physically connect via the
        driver. If successful, emits 'instrument_connected' so UI can
        set up param trees, etc.
        """
        from pymetr.models.device import Device, ConnectionState
        from pymetr.drivers.connections import RawSocketConnection, PyVisaConnection

        # 1) Build the Device model (our "app-level" instrument entity)
        device = Device(
            manufacturer=instrument_info.get('manufacturer'),
            model=instrument_info.get('model'),
            serial_number=instrument_info.get('serial'),
            firmware=instrument_info.get('firmware'),
            resource=instrument_info.get('resource'),
        )

        # If there's driver_info, store it
        driver_info = instrument_info.get('driver_info', {})
        if driver_info:
            device.set_driver_info(driver_info)

        self.registry.register(device)
        device.connection_state = ConnectionState.CONNECTING

        # 2) Parse driver info to dynamically load the driver class
        # Example: driver_info might be {"module": "drivers.hs9000", "class": "HS9000"}
        module_name = driver_info.get('module')
        class_name = driver_info.get('class')
        if not (module_name and class_name):
            device.connection_state = ConnectionState.ERROR
            device.error_message = "Missing or incomplete driver_info."
            self.signals.emit("instrument_connected", device.id)
            return

        try:
            # Ensure full module path
            if not module_name.startswith('pymetr.'):
                module_name = f'pymetr.{module_name}'  # Convert 'drivers.hs9000' to 'pymetr.drivers.hs9000'
                    
            driver_module = importlib.import_module(module_name)
            DriverClass = getattr(driver_module, class_name)
        except (ImportError, AttributeError) as e:
            device.connection_state = ConnectionState.ERROR
            device.error_message = f"Could not load driver '{module_name}.{class_name}': {e}"
            self.signals.emit("instrument_connected", device.id)
            return

        # 3) Build a connection interface depending on the resource string
        #    (Simplistic example: check if "TCPIP" => RawSocketConnection, else try PyVisa.)
        resource_str = device.resource or ""
        try:
            if resource_str.startswith("TCPIP"):
                host, port = RawSocketConnection.parse_resource_string(resource_str)
                connection = RawSocketConnection(host=host, port=port)
            else:
                # Fall back to PyVISA for other strings (e.g. "USB" or "GPIB::")
                connection = PyVisaConnection(resource_string=resource_str)
        except Exception as e:
            device.connection_state = ConnectionState.ERROR
            device.error_message = f"Invalid resource '{resource_str}': {e}"
            self.signals.emit("instrument_connected", device.id)
            return

        # 4) Instantiate the SCPIInstrument (or other) driver and physically open the connection
        try:
            scpi_instrument = DriverClass(connection=connection)
            scpi_instrument.open()  # Attempt hardware connection
            device.connection_state = ConnectionState.CONNECTED
        except Exception as e:
            device.connection_state = ConnectionState.ERROR
            device.error_message = str(e)
            scpi_instrument = None

        # 5) Optionally store the driver instance on the Device or in some manager
        #    so you can access SCPI commands later:
        device.driver_instance = scpi_instrument  # or store in registry, etc.

        # 6) Emit a signal so that InstrumentDock (or others) can set up the UI
        self.signals.emit("instrument_connected", device.id)