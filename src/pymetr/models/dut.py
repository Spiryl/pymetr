# app/models/device_models.py

from typing import Dict, Optional, Any, List
from pathlib import Path
import logging

from .device import Device, ConnectionState
logger = logging.getLogger(__name__)
    
class DUT(Device):
    """Device Under Test - extends Instrument with test-specific attributes."""
    
    def __init__(self,
                 manufacturer: Optional[str] = None,
                 model: Optional[str] = None,
                 serial_number: Optional[str] = None,
                 firmware: Optional[str] = None,
                 resource: Optional[str] = None,
                 data_directory: Optional[Path] = None,
                 id: Optional[str] = None):
        
        super().__init__(
            manufacturer=manufacturer,
            model=model,
            serial_number=serial_number,
            firmware=firmware,
            resource=resource,
            id=id
        )
        self._data_directory = data_directory
        self._configuration: Dict[str, Any] = {}

        logger.info(f"Created DUT with ID: {self.id}")

    @property
    def data_directory(self) -> Optional[Path]:
        return self._data_directory

    @data_directory.setter
    def data_directory(self, value: Optional[Path]):
        old_value = self._data_directory
        self._data_directory = value
        self.notify_change("data_directory_changed", {
            "dut_id": self.id,
            "old_value": str(old_value) if old_value else None,
            "new_value": str(value) if value else None
        })

    @property
    def configuration(self) -> Dict[str, Any]:
        return self._configuration.copy()

    def set_config_value(self, key: str, value: Any):
        """Update a single configuration value."""
        old_value = self._configuration.get(key)
        self._configuration[key] = value
        self.notify_change("configuration_changed", {
            "dut_id": self.id,
            "key": key,
            "old_value": old_value,
            "new_value": value
        })

    def update_configuration(self, updates: Dict[str, Any]):
        """Update multiple configuration values at once."""
        old_values = {}
        for key, value in updates.items():
            old_values[key] = self._configuration.get(key)
            self._configuration[key] = value

        self.notify_change("configuration_bulk_changed", {
            "dut_id": self.id,
            "old_values": old_values,
            "new_values": updates
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert DUT state to a dictionary, including base Instrument fields."""
        data = super().to_dict()
        data.update({
            'data_directory': str(self.data_directory) if self.data_directory else None,
            'configuration': self.configuration
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DUT':
        """Create a new DUT instance from a dictionary."""
        dut = cls(
            manufacturer=data.get('manufacturer'),
            model=data.get('model'),
            serial_number=data.get('serial_number'),
            firmware=data.get('firmware'),
            resource=data.get('resource'),
            data_directory=Path(data['data_directory']) if data.get('data_directory') else None,
            id=data.get('id')
        )
        if data.get('connection_state'):
            dut._connection_state = ConnectionState(data['connection_state'])
        dut._error_message = data.get('error_message')
        dut._driver_info = data.get('driver_info', {}).copy()
        dut._parameters = data.get('parameters', {}).copy()
        dut._configuration = data.get('configuration', {}).copy()
        return dut