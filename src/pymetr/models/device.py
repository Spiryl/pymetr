from typing import Dict, Any, Optional
from PySide6.QtCore import Signal

from pymetr.models.base import BaseModel
from pymetr.core.registry import ConnectionType
from pymetr.core.logging import logger

class Device(BaseModel):
    """
    Model representing an instrument and its state.
    Handles driver loading, connection management, and property updates.
    """
    
    # Signals
    connection_changed = Signal(bool)    # is_connected
    property_changed = Signal(str, Any)  # property_path, value
    error_occurred = Signal(str)         # error_message
    
    def __init__(self, 
                 manufacturer: Optional[str] = None,
                 model: Optional[str] = None,
                 serial_number: Optional[str] = None,
                 firmware: Optional[str] = None,
                 resource: Optional[str] = None,
                 id: Optional[str] = None):
        super().__init__(id, model_type='Device')
        self._driver_instance = None
        self._connection = None
        
        # Store basic properties
        self._manufacturer = manufacturer
        self._model = model
        self._serial_number = serial_number
        self._firmware = firmware
        self._resource = resource
        self._error_message: Optional[str] = None
        self._driver_info: Dict[str, Any] = {}
        self._parameters: Dict[str, Any] = {}
        
        # Set default properties
        self.set_property('name', manufacturer or 'Unnamed Device')
        self.set_property('model', model or '')
        self.set_property('serial', serial_number or '')
        self.set_property('driver_path', '')
        self.set_property('connection_type', ConnectionType.VISA)
        self.set_property('connection_string', resource or '')
        self.set_property('is_connected', False)
        
    @property
    def manufacturer(self) -> Optional[str]:
        return self._manufacturer

    @manufacturer.setter
    def manufacturer(self, value: Optional[str]):
        self._manufacturer = value
        self.set_property('name', value or 'Unnamed Device')

    @property
    def model(self) -> Optional[str]:
        return self._model

    @model.setter
    def model(self, value: Optional[str]):
        self._model = value
        self.set_property('model', value or '')

    @property
    def serial_number(self) -> Optional[str]:
        return self._serial_number

    @serial_number.setter
    def serial_number(self, value: Optional[str]):
        self._serial_number = value
        self.set_property('serial', value or '')

    @property
    def firmware(self) -> Optional[str]:
        return self._firmware

    @firmware.setter 
    def firmware(self, value: Optional[str]):
        self._firmware = value

    @property
    def resource(self) -> Optional[str]:
        return self._resource

    @resource.setter
    def resource(self, value: Optional[str]):
        self._resource = value
        self.set_property('connection_string', value or '')

    @property
    def error_message(self) -> Optional[str]:
        return self._error_message

    @error_message.setter
    def error_message(self, value: Optional[str]):
        self._error_message = value
        self.set_property('error_message', value)

    @property
    def driver_info(self) -> Dict[str, Any]:
        return self._driver_info.copy()
        
    @property
    def driver_instance(self):
        """Get the driver instance."""
        return self._driver_instance
        
    def connect(self):
        """Establish connection to instrument."""
        try:
            from pymetr.core.connections import ConnectionFactory
            
            # Create connection
            config = {
                'type': self.get_property('connection_type'),
                'resource': self.get_property('connection_string')
            }
            self._connection = ConnectionFactory.create_connection(config)
            
            # Create driver instance
            from pymetr.core.registry import get_registry
            registry = get_registry()
            model = self.get_property('model')
            self._driver_instance = registry.create_instance(model, self._connection)
            
            # Connect signals
            self._driver_instance.property_changed.connect(self._handle_driver_property)
            self._driver_instance.error_occurred.connect(self._handle_driver_error)
            
            # Open connection
            self._connection.open()
            self.set_property('is_connected', True)
            self.connection_changed.emit(True)
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.error_occurred.emit(str(e))
            self.set_property('is_connected', False)
            self.connection_changed.emit(False)
            
    def disconnect(self):
        """Close connection to instrument."""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                self._connection = None
                self._driver_instance = None
                self.set_property('is_connected', False)
                self.connection_changed.emit(False)

    def set_driver_info(self, info: Dict[str, Any]):
        """Update driver information."""
        self._driver_info = info.copy()
        
    @property
    def parameters(self) -> Dict[str, Any]:
        return self._parameters.copy()

    def update_parameter(self, path: str, value: Any):
        """Update a single parameter value."""
        parts = path.split('.')
        current = self._parameters
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
            
        current[parts[-1]] = value
                
    def _handle_driver_property(self, path: str, value: Any):
        """Handle property changes from driver."""
        self.property_changed.emit(path, value)
        
    def _handle_driver_error(self, error: str):
        """Handle errors from driver."""
        self.error_occurred.emit(error)
        self.error_message = error