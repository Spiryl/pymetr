# app/models/device_models.py

from typing import Dict, Optional, Any, List
from pathlib import Path
from enum import Enum
from .base import BaseModel
from ..logging import logger

class ConnectionState(Enum):
    """Possible states for an device connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

class Device(BaseModel):
    """Base class for all devices including DUTs."""
    
    def __init__(self, 
                 manufacturer: Optional[str] = None,
                 model: Optional[str] = None,
                 serial_number: Optional[str] = None,
                 firmware: Optional[str] = None,
                 resource: Optional[str] = None,
                 id: Optional[str] = None):
        super().__init__(id)
        self._manufacturer = manufacturer
        self._model = model
        self._serial_number = serial_number
        self._firmware = firmware
        self._resource = resource
        self._connection_state = ConnectionState.DISCONNECTED
        self._error_message: Optional[str] = None
        self._driver_info: Dict[str, Any] = {}
        self.driver_instance = None
        self._parameters: Dict[str, Any] = {}

        logger.info(f"Created Instrument with ID: {self.id}")

    @property
    def manufacturer(self) -> Optional[str]:
        return self._manufacturer

    @manufacturer.setter
    def manufacturer(self, value: Optional[str]):
        old_value = self._manufacturer
        self._manufacturer = value

    @property
    def model(self) -> Optional[str]:
        return self._model

    @model.setter
    def model(self, value: Optional[str]):
        old_value = self._model
        self._model = value

    @property
    def serial_number(self) -> Optional[str]:
        return self._serial_number

    @serial_number.setter
    def serial_number(self, value: Optional[str]):
        old_value = self._serial_number
        self._serial_number = value

    @property
    def firmware(self) -> Optional[str]:
        return self._firmware

    @firmware.setter 
    def firmware(self, value: Optional[str]):
        old_value = self._firmware
        self._firmware = value

    @property
    def resource(self) -> Optional[str]:
        return self._resource

    @resource.setter
    def resource(self, value: Optional[str]):
        old_value = self._resource
        self._resource = value

    @property
    def connection_state(self) -> ConnectionState:
        return self._connection_state

    @connection_state.setter
    def connection_state(self, value: ConnectionState):
        old_value = self._connection_state
        self._connection_state = value

    @property
    def error_message(self) -> Optional[str]:
        return self._error_message

    @error_message.setter
    def error_message(self, value: Optional[str]):
        old_value = self._error_message
        self._error_message = value

    @property
    def driver_info(self) -> Dict[str, Any]:
        return self._driver_info.copy()

    def set_driver_info(self, info: Dict[str, Any]):
        """Update driver information."""
        old_info = self._driver_info.copy()
        self._driver_info = info.copy()

    def set_driver_instance(self, instance):
        """Set the driver instance after successful connection"""
        self.driver_instance = instance
        self.connection_state = ConnectionState.CONNECTED if instance else ConnectionState.ERROR
        
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
            
        old_value = current.get(parts[-1])
        current[parts[-1]] = value

    def set_parameters(self, parameters: Dict[str, Any]):
        """Set the complete parameter tree."""
        old_params = self._parameters.copy()
        self._parameters = parameters.copy()

    def to_dict(self) -> Dict[str, Any]:
        """Convert instrument state to a dictionary for serialization."""
        return {
            'id': self.id,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'serial_number': self.serial_number,
            'firmware': self.firmware,
            'resource': self.resource,
            'connection_state': self.connection_state.value,
            'error_message': self.error_message,
            'driver_info': self.driver_info,
            'parameters': self.parameters
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Device':
        """Create a new instrument instance from a dictionary."""
        inst = cls(
            manufacturer=data.get('manufacturer'),
            model=data.get('model'),
            serial_number=data.get('serial_number'),
            firmware=data.get('firmware'),
            resource=data.get('resource'),
            id=data.get('id')
        )
        if data.get('connection_state'):
            inst._connection_state = ConnectionState(data['connection_state'])
        inst._error_message = data.get('error_message')
        inst._driver_info = data.get('driver_info', {}).copy()
        inst._parameters = data.get('parameters', {}).copy()
        return inst