

from typing import Dict, Optional, Type, TypeVar, List, Any
from PySide6.QtCore import QObject, Signal, Slot, QThread, Qt, QMetaObject, Q_ARG, QTimer
from pymetr.models.base import BaseModel
from pymetr.models import Device
from pymetr.core.engine import Engine
from pymetr.core.logging import logger
from pymetr.drivers import Instrument

T = TypeVar('T', bound=BaseModel)


class DiscoveryWorker(QObject):
    """Worker object for performing instrument discovery in a background thread."""
    
    # Signals
    finished = Signal(dict)  # Emits discovered instruments dict
    instrument_found = Signal(dict)  # Emits each instrument as it's found
    error = Signal(str)  # Emits error message if discovery fails

    def __init__(self, model_filter: Optional[List[str]] = None):
        super().__init__()
        self.model_filter = model_filter
        self._running = False
        
    def discover(self):
        """Run discovery process."""
        try:
            logger.debug("Starting discovery in worker thread")
            self._running = True
            
            # Perform discovery
            instruments = Instrument.list_instruments(self.model_filter)
            
            # Emit each instrument as we find it
            for uid, info in instruments.items():
                if not self._running:
                    # Check if we should stop
                    break
                self.instrument_found.emit(info)
            
            if self._running:
                # Only emit finished if we weren't stopped
                self.finished.emit(instruments)
                
        except Exception as e:
            logger.error(f"Error in discovery worker: {e}")
            self.error.emit(str(e))
        finally:
            self._running = False
            
    def stop(self):
        """Stop the discovery process."""
        self._running = False

class ApplicationState(QObject):
    # Signals
    model_registered = Signal(str)           # model_id
    model_changed = Signal(str, str, str, object)          # model_id, model_type, prop_name, value
    models_linked = Signal(str, str)         # parent_id, child_id
    active_model_changed = Signal(str)       # model_id
    active_test_changed = Signal(str)        # model_id
    model_registration_requested = Signal(str, str)  # model_id, model_type_name

    status_changed = Signal(str)  # Basic status message
    status_progress = Signal(float, str)  # Progress updates (percent, message)
    status_error = Signal(str)  # Error messages
    status_warning = Signal(str)  # Warning messages
    status_info = Signal(str)  # Info messages

    model_removed = Signal(str)   # model_id
    model_viewed = Signal(str)  # Emits model_id

    discovery_started = Signal()  # When instrument discovery begins
    discovery_complete = Signal(dict)  # When discovery finishes (with instruments dict)
    instrument_found = Signal(dict)  # When each instrument is found (with instrument info)
    instrument_connected = Signal(str)  # Emits the device ID when an instrument is connected

    def __init__(self):
        super().__init__()
        self._models: Dict[str, BaseModel] = {}
        self._pending_models: Dict[str, BaseModel] = {}
        self._relationships: Dict[str, set[str]] = {}
        self._active_model_id: Optional[str] = None
        self._active_test_id: Optional[str] = None
        self._parent: Optional[QObject] = None
        
        # Update throttling
        self._pending_updates = []
        self._update_timer = QTimer(self)  # Timer created in main thread
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._process_pending_updates)
        self._throttle_interval = 16  # About 60fps

        self._discovered_instruments = {}
        self._discovery_thread = None
        self._discovery_worker = None
        
        self.engine = Engine(self)
        self.model_registration_requested.connect(self._handle_registration_request)
        logger.debug("ApplicationState initialized with Engine.")

    def set_parent(self, parent: QObject):
        """Optionally store a reference to a parent widget for dialogs."""
        self._parent = parent

    def register_model(self, model: BaseModel) -> None:
        """Register a model - keep it simple and in the main thread."""
        if model.id not in self._models:
            # Let the model know its state manager
            model.state = self
            self._models[model.id] = model

            # Connect signals
            model.property_changed.connect(self._handle_model_change)
            model.child_added.connect(self._handle_child_added)

            self.model_registered.emit(model.id)
            logger.debug(f"Registered model {model.id}")

    @Slot(str, str)
    def _handle_registration_request(self, model_id: str, model_type: str) -> None:
        """Handle registration requests from other threads."""
        if model_id in self._pending_models:
            model = self._pending_models.pop(model_id)
            self._register_model_internal(model)
        else:
            logger.error(f"Model {model_id} not found in pending registrations")

    def _register_model_internal(self, model: BaseModel) -> None:
        """Internal registration that always runs in main thread."""
        if model.id not in self._models:
            # Move model to main thread if needed
            if model.thread() != self.thread():
                model.moveToThread(self.thread())

            # Let the model know its state manager
            model.state = self
            self._models[model.id] = model

            # Connect to type-specific signals
            model.property_changed_str.connect(self._handle_model_change)
            model.property_changed_float.connect(self._handle_model_change)
            model.property_changed_int.connect(self._handle_model_change)
            model.property_changed_bool.connect(self._handle_model_change)
            model.child_added.connect(self._handle_child_added)

            self.model_registered.emit(model.id)
            logger.debug(f"Registered model {model.id}")

    def link_models(self, parent_id: str, child_id: str) -> None:
        """
        Create a relationship between models.
        """
        if QThread.currentThread() != self.thread():
            QMetaObject.invokeMethod(
                self,
                "_link_models_internal",
                Qt.QueuedConnection,
                Q_ARG(str, parent_id),
                Q_ARG(str, child_id)
            )
        else:
            self._link_models_internal(parent_id, child_id)

    @Slot(str, str)
    def _link_models_internal(self, parent_id: str, child_id: str) -> None:
        """Internal linking in main thread."""
        # Check if relationship already exists
        if parent_id in self._relationships and child_id in self._relationships[parent_id]:
            logger.debug(f"Relationship already exists between {parent_id} and {child_id}")
            return
            
        if parent_id not in self._relationships:
            self._relationships[parent_id] = set()
        self._relationships[parent_id].add(child_id)
        self.models_linked.emit(parent_id, child_id)
        logger.debug(f"Linked model {child_id} to parent {parent_id}")

    def unlink_models(self, parent_id: str, child_id: str) -> None:
        """Remove a relationship between models."""
        if parent_id in self._relationships:
            self._relationships[parent_id].discard(child_id)
            logger.debug(f"Unlinked model {child_id} from parent {parent_id}")

    def get_model(self, model_id: str) -> Optional[BaseModel]:
        """Get a model by ID."""
        return self._models.get(model_id)

    def get_models_by_type(self, model_type: Type[T]) -> List[T]:
        """Get all models of a specific type."""
        return [
            model for model in self._models.values()
            if isinstance(model, model_type)
        ]

    def get_children(self, parent_id: str) -> List[BaseModel]:
        """Get all child models for a parent."""
        child_ids = self._relationships.get(parent_id, set())
        return [
            self._models[child_id]
            for child_id in child_ids
            if child_id in self._models
        ]

    def get_parent(self, child_id: str) -> Optional[BaseModel]:
        """Get parent model of a child."""
        for parent_id, children in self._relationships.items():
            if child_id in children:
                return self._models.get(parent_id)
        return None

    @Slot(str, str, str, object)
    def _handle_model_change(self, model_id: str, model_type: str, prop: str, value: Any) -> None:
        """Handle property changes."""
        self.model_changed.emit(model_id, model_type, prop, value)

    @Slot(str, str)
    def _handle_child_added(self, parent_id: str, child_id: str) -> None:
        """A model had a child added -> link them."""
        self.link_models(parent_id, child_id)

    def set_active_test(self, model_id: Optional[str]) -> None:
        """Set the currently active test."""
        if model_id != self._active_test_id:
            self._active_test_id = model_id
            self.active_test_changed.emit(model_id)
            logger.debug(f"Active test changed to {model_id}")

    def get_active_test(self) -> Optional[BaseModel]:
        """Get the currently active test."""
        if self._active_test_id:
            return self._models.get(self._active_test_id)
        return None
    
    def set_active_model(self, model_id: Optional[str]) -> None:
        """Set the currently active model."""
        if model_id != self._active_model_id:
            self._active_model_id = model_id
            self.active_model_changed.emit(model_id)
            logger.debug(f"Active model changed to {model_id}")

    def get_model_by_name(self, name: str) -> Optional[BaseModel]:
        """Return the first model with the given human‑readable name."""
        for model in self._models.values():
            if model.get_property("name") == name:
                return model
        return None

    def get_active_model(self) -> Optional[BaseModel]:
        """Get the currently active model."""
        if self._active_model_id:
            return self._models.get(self._active_model_id)
        return None

    def create_model(self, model_class: Type[T], **kwargs) -> T:
        """
        Create and register a new model. (Convenience method)
        """
        model = model_class(**kwargs)
        self.register_model(model)
        return model
    
    def remove_model(self, model_id: str) -> None:
        if model_id in self._models:
            # Remove as child from any parent
            parent = self.get_parent(model_id)
            if parent:
                self.unlink_models(parent.id, model_id)
                    
            # Remove any children it might have
            if model_id in self._relationships:
                child_ids = list(self._relationships[model_id])
                for child_id in child_ids:
                    self.remove_model(child_id)
                del self._relationships[model_id]
                    
            # Remove the model itself
            model = self._models[model_id]
            model.deleteLater()
            del self._models[model_id]
            logger.debug(f"Removed model {model_id}")
            
            # Emit signal so that any views (like tab views or tree views) can update
            self.model_removed.emit(model_id)

    def clear_children(self, parent_id: str) -> None:
        """Remove all child models of the given parent."""
        children = self.get_children(parent_id)
        for child in children:
            self.remove_model(child.id)

    def set_status(self, message: str):
        """Set main status message."""
        self.status_changed.emit(message)
        logger.debug(f"Status: {message}")

    def set_progress(self, percent: float, message: str = ""):
        """Update progress status."""
        self.status_progress.emit(percent, message)
        logger.debug(f"Progress: {percent}% - {message}")

    def set_error(self, message: str):
        """Show error status."""
        self.status_error.emit(message)
        logger.error(f"Error: {message}")

    def set_warning(self, message: str):
        """Show warning status."""
        self.status_warning.emit(message)
        logger.warning(f"Warning: {message}")

    def set_info(self, message: str):
        """Show info status."""
        self.status_info.emit(message)
        logger.info(f"Info: {message}")

    def queue_model_update(self, model_id: str, prop: str, value: Any):
        """Queue a model update to be processed in the main thread."""
        self._pending_updates.append((model_id, prop, value))
        if not self._update_timer.isActive():
            self._update_timer.start(self._throttle_interval)

    def _process_pending_updates(self):
        """Process all pending model updates."""
        if not self._pending_updates:
            return
            
        # Group updates by model
        updates_by_model = {}
        for model_id, model_type, prop, value in self._pending_updates:
            if model_id not in updates_by_model:
                updates_by_model[model_id] = []
            updates_by_model[model_id].append((model_type, prop, value))
            
        # Process updates
        for model_id, updates in updates_by_model.items():
            model = self._models.get(model_id)
            if model:
                for model_type, prop, value in updates:
                    self.model_changed.emit(model_id, model_type, prop, value)
                    
        self._pending_updates.clear()

    def update_active_view(self, model_id: str):
        """Called when a dock is done activating."""
        self.model_viewed.emit(model_id)

    def discover_instruments(self, model_filter: Optional[List[str]] = None):
        """Start instrument discovery process in background thread."""
        logger.debug("Starting instrument discovery")
        self.discovery_started.emit()
        
        # Create worker and thread
        self._discovery_worker = DiscoveryWorker(model_filter)
        self._discovery_thread = QThread()
        
        # Move worker to thread
        self._discovery_worker.moveToThread(self._discovery_thread)
        
        # Connect signals
        self._discovery_thread.started.connect(self._discovery_worker.discover)
        self._discovery_worker.finished.connect(self._handle_discovery_complete)
        self._discovery_worker.instrument_found.connect(self._handle_instrument_found)
        self._discovery_worker.error.connect(self._handle_discovery_error)
        self._discovery_worker.finished.connect(self._discovery_thread.quit)
        self._discovery_thread.finished.connect(self._cleanup_discovery)
        
        # Start the thread
        self._discovery_thread.start()

    def stop_discovery(self):
        """Stop any ongoing discovery process."""
        if self._discovery_worker:
            self._discovery_worker.stop()
        if self._discovery_thread:
            self._discovery_thread.quit()
            self._discovery_thread.wait()
        self._cleanup_discovery()

    def _cleanup_discovery(self):
        """Clean up discovery thread and worker."""
        if self._discovery_thread:
            self._discovery_thread.deleteLater()
            self._discovery_thread = None
        if self._discovery_worker:
            self._discovery_worker.deleteLater()
            self._discovery_worker = None

    def _handle_discovery_complete(self, instruments: Dict):
        """Handle discovery completion."""
        logger.debug(f"Discovery complete, found {len(instruments)} instruments")
        self._discovered_instruments = instruments
        self.discovery_complete.emit(instruments)

    def _handle_instrument_found(self, info: Dict):
        """Handle individual instrument discovery."""
        logger.debug(f"Found instrument: {info.get('model', 'Unknown')}")
        self.instrument_found.emit(info)

    def _handle_discovery_error(self, error: str):
        """Handle discovery error."""
        logger.error(f"Discovery error: {error}")
        self.discovery_complete.emit({})  # Emit empty dict on error

    def get_discovered_instruments(self) -> Dict[str, Dict]:
        """Get the currently discovered instruments."""
        return self._discovered_instruments

    def connect_instrument(self, info: Dict[str, Any]):
        """Connect to an instrument from discovery info."""
        try:
            logger.debug(f"ApplicationState: Creating device from discovery info: {info}")
            
            # Create device with state reference
            device = Device.from_discovery_info(info, state=self)  # Pass self as state
            logger.debug(f"ApplicationState: Created device with ID: {device.id}")
            
            # Register with state BEFORE connecting
            logger.debug("ApplicationState: Registering device with state")
            self.register_model(device)
            
            # Now connect to instrument
            logger.debug("ApplicationState: Connecting device")
            device.connect_device()
            
            logger.info(f"ApplicationState: Successfully created and connected device: {device.id}")
            self.instrument_connected.emit(device.id)
            
            return device
                
        except Exception as e:
            logger.error(f"ApplicationState.connect_instrument error: {e}", exc_info=True)
            raise

    def set_theme(self, theme_name: str) -> bool:
        """
        Set the application theme.
        
        Args:
            theme_name: Name of the theme to set
            
        Returns:
            True if successful, False otherwise
        """
        from pymetr.services.theme_service import ThemeService
        
        # Get theme service
        theme_service = ThemeService.get_instance()
        
        # Set theme
        success = theme_service.set_theme(theme_name)
        
        # Add status message
        if success:
            self.set_info(f"Theme changed to {theme_name}")
        
        return success

    def set_accent_color(self, color) -> bool:
        """
        Set the accent color.
        
        Args:
            color: QColor or color string
            
        Returns:
            True if successful, False otherwise
        """
        from pymetr.services.theme_service import ThemeService
        from PySide6.QtGui import QColor
        
        # Get theme service
        theme_service = ThemeService.get_instance()
        
        # Convert to QColor if needed
        if not isinstance(color, QColor):
            color = QColor(color)
        
        # Set accent color
        success = theme_service.set_accent_color(color)
        
        # Add status message
        if success:
            self.set_info(f"Accent color changed to {color.name()}")
        
        return success

    def get_resource(self, resource_type: str, name: str, **kwargs):
        """
        Get a resource (icon, image, etc.) from the resource service.
        
        Args:
            resource_type: Type of resource (icon, pixmap, etc.)
            name: Resource name
            **kwargs: Additional parameters for resource loading
            
        Returns:
            Requested resource or None if not found
        """
        from pymetr.services.resource_service import ResourceService
        
        # Get resource service
        resource_service = ResourceService.get_instance()
        
        # Get resource
        if resource_type == "icon":
            return resource_service.get_icon(name, **kwargs)
        elif resource_type == "pixmap":
            return resource_service.get_pixmap(name, **kwargs)
        else:
            logger.warning(f"Unknown resource type: {resource_type}")
            return None
