from typing import Dict, Optional, Type, List, Any
import importlib
from enum import Enum, auto
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal, QThread, Slot, Qt, QMetaObject, Q_ARG

from pymetr.core.logging import logger

class ConnectionType(Enum):
    """Known connection interface types"""
    VISA = auto()
    SOCKET = auto()
    SERIAL = auto()

@dataclass
class DriverInfo:
    """Driver configuration information"""
    module: str
    class_name: str
    interfaces: List[ConnectionType]
    socket_port: Optional[int] = None
    discovery_config: Optional[Dict[str, Any]] = None

class InstrumentRegistry(QObject):
    """
    Thread-safe singleton registry for instrument drivers and instances.
    """
    # Singleton instance
    _instance = None
    
    # Signals
    driver_loaded = Signal(str)  # driver_module
    instance_created = Signal(str, object)  # model, instance
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if self._initialized:
            return
            
        super().__init__()
        self._drivers: Dict[str, DriverInfo] = {}
        self._driver_cache: Dict[str, Type] = {}
        self._instances: Dict[str, object] = {}
        self._register_builtin_drivers()
        self._initialized = True
        
    def _register_builtin_drivers(self):
        """Register built-in instrument drivers."""
        self.register_driver(
            "DSOX1204G",
            DriverInfo(
                module="pymetr.drivers.instruments.dsox1204g",
                class_name="DSOX1204G",
                interfaces=[ConnectionType.VISA],
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
        # Add more built-in drivers...
        
    def register_driver(self, model: str, info: DriverInfo) -> None:
        """
        Register a new instrument driver.
        
        Args:
            model: Instrument model identifier
            info: Driver configuration information
        """
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
        
    def get_driver(self, model: str) -> Optional[Type]:
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
            
    def create_instance(self, model: str, connection: Any) -> Optional[object]:
        """
        Create an instrument instance with thread safety.
        
        Args:
            model: Instrument model identifier
            connection: Connection interface instance
            
        Returns:
            Instrument instance or None if creation fails
        """
        if QThread.currentThread() != self.thread():
            result = None
            QMetaObject.invokeMethod(
                self,
                "_create_instance_internal",
                Qt.BlockingQueuedConnection,  # We need the result
                Q_ARG(str, model),
                Q_ARG(object, connection),
                Q_ARG(object, result)
            )
            return result
        else:
            return self._create_instance_internal(model, connection)
            
    @Slot(str, object, object)
    def _create_instance_internal(self, model: str, connection: Any, result: object = None) -> Optional[object]:
        """Internal creation that always runs in main thread."""
        driver_class = self.get_driver(model)
        if not driver_class:
            return None
            
        try:
            # Create instance
            instance = driver_class(connection)
            
            # Store instance
            instance_id = f"{model}_{len(self._instances)}"
            self._instances[instance_id] = instance
            
            self.instance_created.emit(model, instance)
            logger.debug(f"Created instance {instance_id} of {model}")
            
            return instance
            
        except Exception as e:
            logger.error(f"Failed to create instance of {model}: {e}")
            return None
            
    def get_supported_interfaces(self, model: str) -> List[ConnectionType]:
        """Get supported connection types for a model."""
        info = self._drivers.get(model.upper())
        return info.interfaces if info else []
        
    def get_discovery_config(self, model: str) -> Optional[Dict[str, Any]]:
        """Get discovery configuration for a model."""
        info = self._drivers.get(model.upper())
        return info.discovery_config if info else None
        
def create_instrument(model: str, connection: Optional[Any] = None) -> Optional[object]:
    """
    Global function to create instrument instances.
    Uses default connection if none provided.
    
    Args:
        model: Instrument model identifier
        connection: Optional connection interface
        
    Returns:
        Instrument instance or None if creation fails
    """
    registry = InstrumentRegistry()  # This could be a singleton
    if not connection:
        # Create default connection based on model
        # This would use your connection factories
        pass
    return registry.create_instance(model, connection)

# Global access function
def get_registry() -> InstrumentRegistry:
    """Get the global instrument registry instance."""
    return InstrumentRegistry()