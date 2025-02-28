"""
Registry for instrument drivers and device management.

This module provides a thread-safe singleton registry that maintains:
- Driver registration and loading
- Connection type information
- Discovery configuration
- Instance tracking
"""

from typing import Dict, Optional, Type, List, Any
import importlib
from enum import Enum, auto
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal, QThread, Slot, Qt, QMetaObject, Q_ARG

from pymetr.core.logging import logger
from pymetr.drivers.base.connections import ConnectionInterface
from pymetr.models.device import Device

class ConnectionType(Enum):
    """Known connection interface types"""
    VISA = auto()
    SOCKET = auto()
    SERIAL = auto()

@dataclass
class DriverInfo:
    """Driver configuration information"""
    module: str                                      # Driver module path
    class_name: str                                 # Driver class name
    interfaces: List[ConnectionType]                # Supported connection types
    socket_port: Optional[int] = None              # Default socket port if applicable
    discovery_config: Optional[Dict[str, Any]] = None  # Discovery protocol config

class InstrumentRegistry(QObject):
    """
    Thread-safe singleton registry for instrument drivers and instances.
    
    Manages:
    - Driver registration and loading
    - Device model creation
    - Instance tracking
    - Connection configuration
    """
    _instance = None  # Singleton instance
    
    # Signals
    driver_loaded = Signal(str)           # driver_module
    device_created = Signal(str, Device)  # model, device_instance
    driver_created = Signal(str, object)  # model, driver_instance
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if self._initialized:
            return
            
        super().__init__()
        self._drivers: Dict[str, DriverInfo] = {}         # Model -> Driver info
        self._driver_cache: Dict[str, Type] = {}         # Model -> Driver class
        self._devices: Dict[str, Device] = {}            # ID -> Device model
        self._driver_instances: Dict[str, object] = {}   # ID -> Driver instance
        self._register_builtin_drivers()
        self._initialized = True

    def _register_builtin_drivers(self):
        """Register built-in instrument drivers."""
        self.register_driver(
            "DSOX1204G",
            DriverInfo(
                module="pymetr.drivers.instruments.dsox1204g",
                class_name="DSOX1204G",
                interfaces=[ConnectionType.VISA]
            )
        )
        
        self.register_driver(
            "HS9001B",
            DriverInfo(
                module="pymetr.drivers.instruments.hs9000",
                class_name="HS9000",
                interfaces=[ConnectionType.VISA, ConnectionType.SOCKET],
                socket_port=9760,
                discovery_config={
                    "udp_port": 30303,
                    "protocol": "MICROCHIP"
                }
            )
        )
        
    def register_driver(self, model: str, info: DriverInfo) -> None:
        """Register a new instrument driver."""
        if QThread.currentThread() != self.thread():
            QMetaObject.invokeMethod(
                self,
                "_register_driver_internal",
                Qt.QueuedConnection,
                Q_ARG(str, model),
                Q_ARG(object, info)
            )
        else:
            self._register_driver_internal(model, info)

    @Slot(str, object)
    def _register_driver_internal(self, model: str, info: DriverInfo) -> None:
        """Internal registration that always runs in main thread."""
        self._drivers[model.upper()] = info
        logger.debug(f"Registered driver for {model}")

    def create_device(self, info: Dict[str, Any]) -> Optional[Device]:
        """
        Create a Device model from discovery information.
        
        Args:
            info: Dictionary containing device info from discovery
                 (manufacturer, model, serial, etc.)
        
        Returns:
            Device model or None if creation fails
        """
        try:
            # Create device model
            device = Device.from_discovery_info(info)
            
            # Store device
            self._devices[device.id] = device
            
            # Emit signal
            self.device_created.emit(info['model'], device)
            logger.debug(f"Created device model for {info['model']}")
            
            return device
            
        except Exception as e:
            logger.error(f"Failed to create device model: {e}")
            return None
        
    def get_driver_class(self, model: str) -> Optional[Type]:
        """
        Get driver class for an instrument model.
        Loads driver module if needed.
        
        Args:
            model: Instrument model identifier
            
        Returns:
            Driver class or None if not found
        """
        model = model.upper()
        
        # Return cached driver if available
        if model in self._driver_cache:
            return self._driver_cache[model]
            
        # Get driver info
        info = self._drivers.get(model)
        if not info:
            logger.error(f"No driver registered for {model}")
            return None
            
        try:
            # Import driver module
            module = importlib.import_module(info.module)
            
            # Get driver class
            driver_class = getattr(module, info.class_name)
            
            # Cache for future use
            self._driver_cache[model] = driver_class
            self.driver_loaded.emit(info.module)
            
            return driver_class
            
        except Exception as e:
            logger.error(f"Failed to load driver for {model}: {e}")
            return None

    def create_driver_instance(self, 
                            device_or_model,
                            connection: ConnectionInterface,
                            threaded_mode: bool = True) -> Optional[object]:
        """
        Create a driver instance for a device.
        
        Args:
            device_or_model: Device model instance or model name string
            connection: Connection interface instance
            threaded_mode: Whether to use threaded communication
            
        Returns:
            Driver instance or None if creation fails
        """
        if QThread.currentThread() != self.thread():
            result = None
            QMetaObject.invokeMethod(
                self,
                "_create_driver_internal",
                Qt.BlockingQueuedConnection,
                Q_ARG(object, device_or_model),  # Changed to object type
                Q_ARG(object, connection),
                Q_ARG(bool, threaded_mode),
                Q_ARG(object, result)
            )
            return result
        else:
            return self._create_driver_internal(device_or_model, connection, threaded_mode)

    @Slot(object, object, bool, object)  # Changed first param to object
    def _create_driver_internal(self, 
                            device_or_model,
                            connection: ConnectionInterface,
                            threaded_mode: bool,
                            result: object = None) -> Optional[object]:
        """Internal driver creation that always runs in main thread."""
        
        # Handle both Device objects and string model names
        if isinstance(device_or_model, Device):
            device = device_or_model
            model_name = device.get_property('model')
            device_id = device.id
        else:
            # If a string was passed, use it as the model name
            model_name = str(device_or_model)
            device = None
            device_id = f"temp_{id(connection)}"  # Generate a temporary ID
        
        driver_class = self.get_driver_class(model_name)
        if not driver_class:
            logger.error(f"No driver class found for model: {model_name}")
            return None
            
        try:
            # Create driver instance
            instance = driver_class(connection, threaded_mode=threaded_mode)
            
            # Store instance if we have a device
            if device:
                self._driver_instances[device_id] = instance
                
            self.driver_created.emit(model_name, instance)
            logger.debug(f"Created driver instance for model {model_name}")
            
            return instance
            
        except Exception as e:
            logger.error(f"Failed to create driver instance: {e}")
            return None

    def get_supported_interfaces(self, model: str) -> List[ConnectionType]:
        """Get supported connection types for a model."""
        info = self._drivers.get(model.upper())
        return info.interfaces if info else []
        
    def get_discovery_config(self, model: str) -> Optional[Dict[str, Any]]:
        """Get discovery configuration for a model."""
        info = self._drivers.get(model.upper())
        return info.discovery_config if info else None

    def cleanup_device(self, device_id: str) -> None:
        """Clean up a device and its driver instance."""
        if device_id in self._devices:
            del self._devices[device_id]
        if device_id in self._driver_instances:
            del self._driver_instances[device_id]
            
    def get_device(self, device_id: str) -> Optional[Device]:
        """Get a device model by ID."""
        return self._devices.get(device_id)
        
    def get_driver_instance(self, device_id: str) -> Optional[object]:
        """Get a driver instance by device ID."""
        return self._driver_instances.get(device_id)

# Global access function
def get_registry() -> InstrumentRegistry:
    """Get the global instrument registry instance."""
    return InstrumentRegistry()