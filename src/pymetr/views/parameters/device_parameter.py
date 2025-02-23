# views/parameters/device_parameter.py
from typing import Optional, Any, Dict
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QMenu
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QBrush, QPen

from pyqtgraph.parametertree import Parameter
from pymetr.models.device import Device, AcquisitionMode
from pymetr.core.logging import logger
from .base import ModelParameter, ModelParameterItem, ParameterWidget

class LEDIndicator(QLabel):
    """Simple LED status indicator."""
    def __init__(self, size=12, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = QColor("#333333")  # Default off color
        
    def set_state(self, state: str):
        """Set LED color based on state."""
        colors = {
            'off': "#333333",
            'green': "#2ECC71",
            'blue': "#3498DB",
            'red': "#E74C3C"
        }
        self._color = QColor(colors.get(state, colors['off']))
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw LED circle
        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawEllipse(1, 1, self.width()-2, self.height()-2)

class DeviceInfoWidget(ParameterWidget):
    """Widget showing device status with LED indicators."""
    
    def __init__(self, param, parent=None):
        super().__init__(param, parent)
        self._setup_ui()
        self._connect_signals()
        
    def _connect_signals(self):
        """Connect to device signals."""
        device = self.param.state.get_model(self.param.model_id)
        if device:
            device.connection_changed.connect(
                lambda connected: self.queue_update(is_connected=connected)
            )
            device.error_occurred.connect(
                lambda error: self.queue_update(error_message=error)
            )

    def cleanup(self):
        """Clean up signal connections."""
        try:
            device = self.param.state.get_model(self.param.model_id)
            if device:
                device.connection_changed.disconnect()
                device.error_occurred.disconnect()
        except:
            pass
        super().cleanup()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Connection LED
        self.conn_led = LEDIndicator()
        layout.addWidget(self.conn_led)
        
        # Status LED  
        self.status_led = LEDIndicator()
        layout.addWidget(self.status_led)
        
        # Connect/Disconnect button
        self.conn_button = QPushButton("Connect")
        self.conn_button.setCheckable(True)
        self.conn_button.clicked.connect(self._handle_connection)
        layout.addWidget(self.conn_button)
        
        layout.addStretch()
    
    def _handle_connection(self, checked):
        """Handle connect/disconnect button."""
        device = self.param.state.get_model(self.param.model_id)
        if device:
            if checked:
                device.connect()
                self.conn_button.setText("Disconnect")
            else:
                device.disconnect() 
                self.conn_button.setText("Connect")
    
    def _process_pending_update(self):
        updates = self._pending_updates.copy()
        self._pending_updates.clear()
        
        # Update connection status
        if 'is_connected' in updates:
            is_connected = updates['is_connected']
            self.conn_led.set_state('blue' if is_connected else 'off')
            self.conn_button.setChecked(is_connected)
            self.conn_button.setText("Disconnect" if is_connected else "Connect")
            
        # Update error status
        if 'error_message' in updates:
            error_msg = updates['error_message']
            self.status_led.set_state('red' if error_msg else 'green')
            if error_msg:
                self.setToolTip(error_msg)
            else:
                self.setToolTip("")

class DeviceParameter(ModelParameter):
    """Parameter for device control and monitoring."""
    
    itemClass = ModelParameterItem
    
    def __init__(self, **opts):
        opts['type'] = 'device'
        super().__init__(**opts)
        
        # Get model through state
        device = self.state.get_model(self.model_id) if self.state else None
        self.setupParameters(device)
    
    def setupParameters(self, device):
        """Set up device parameters."""
        def get_prop(name, default):
            return device.get_property(name, default) if device else default

        # Device Info group
        info_group = {
            'name': 'Device Info',
            'type': 'group',
            'children': [
                dict(name='model', type='str', 
                     value=get_prop('model', ''), readonly=True),
                dict(name='manufacturer', type='str', 
                     value=get_prop('manufacturer', ''), readonly=True),
                dict(name='serial', type='str', 
                     value=get_prop('serial', ''), readonly=True),
                dict(name='firmware', type='str', 
                     value=get_prop('firmware', ''), readonly=True),
                dict(name='resource', type='str', 
                     value=get_prop('resource', ''), readonly=True)
            ]
        }
        
        # Acquisition settings
        settings_group = {
            'name': 'Settings',
            'type': 'group',
            'children': [
                dict(name='acquisition_mode', type='list',
                     value=get_prop('acquisition_mode', AcquisitionMode.SINGLE.value),
                     limits=[mode.value for mode in AcquisitionMode]),
                dict(name='averaging_count', type='int',
                     value=get_prop('averaging_count', 10),
                     limits=(2, 1000))
            ]
        }
        
        # Add each parameter group
        for group_dict in [info_group, settings_group]:
            param = Parameter.create(**group_dict)
            self.addChild(param)
            
            # Only connect change handlers for settings
            if group_dict['name'] == 'Settings':
                for child in param.children():
                    child.sigValueChanged.connect(self._handle_parameter_change)

    def handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        try:
            # Update parameter values
            for group in self.children():
                for param in group.children():
                    if param.name() == prop:
                        param.setValue(value)
                        break
            
            # Update status widget
            if hasattr(self, 'widget'):
                self.widget.queue_update(**{prop: value})
                
        except Exception as e:
            logger.error(f"Error handling property update: {e}")

    def _handle_parameter_change(self, param, value):
        """Handle parameter changes by updating model through state."""
        device = self.state.get_model(self.model_id)
        if device:
            device.set_property(param.name(), value)