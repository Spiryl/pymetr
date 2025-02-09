from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QHeaderView, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from pyqtgraph.parametertree import Parameter, ParameterTree

from pymetr.models.device import Device
from pymetr.views.widgets.base import BaseWidget
from pymetr.core.visitor import InstrumentVisitor
from pymetr.core.factory import InstrumentFactory
from pymetr.core.logging import logger

class DeviceView(BaseWidget):
    """
    Widget for device control and monitoring.
    Uses parameter tree for property control and updates.
    """
    
    property_changed = Signal(str, str, object)  # model_id, prop_path, value
    
    def __init__(self, state, model_id: Optional[str] = None, parent=None):
        super().__init__(state, parent)
        self._parameter_tree = None
        self._parameters: Dict[str, Parameter] = {}
        self._setup_ui()
        if model_id:
            self.set_model(model_id)

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create control bar
        control_bar = QWidget()
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(4, 4, 4, 4)
        
        # Connect/Disconnect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._handle_connect_click)
        control_layout.addWidget(self.connect_button)
        
        # Status label
        self.status_label = QLabel()
        control_layout.addWidget(self.status_label)
        
        control_layout.addStretch()
        layout.addWidget(control_bar)
        
        # Create parameter tree widget
        self._parameter_tree = ParameterTree()
        self._parameter_tree.setAlternatingRowColors(False)
        header = self._parameter_tree.header()
        header.setMinimumSectionSize(100)
        header.setDefaultSectionSize(120)
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        
        # Set size policy
        self._parameter_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._parameter_tree.setMinimumWidth(200)  # Minimum width for the tree itself
        
        # Enable column resize
        self._parameter_tree.setColumnWidth(0, 120)  # Initial width for first column
        self._parameter_tree.setColumnWidth(1, 120)  # Initial width for second column
        layout.addWidget(self._parameter_tree)
        
        # Apply styling
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #1E1E1E;
                alternate-background-color: #252525;
                color: #D4D4D4;
            }
            QTreeWidget::item:selected {
                background-color: #264F78;
            }
            QPushButton {
                padding: 4px 12px;
                background-color: #0E639C;
                border: none;
                border-radius: 2px;
                color: white;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:pressed {
                background-color: #0D5789;
            }
            QPushButton:disabled {
                background-color: #2D2D2D;
                color: #666666;
            }
            QLabel {
                color: #D4D4D4;
            }
        """)

    def _handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        if prop == 'is_connected':
            self._update_connection_state(value)
        elif prop == 'error_message':
            self._update_error_state(value)
        elif prop == 'parameters':
            self._update_parameters(value)
        elif prop in self._parameters:
            param = self._parameters[prop]
            param.setValue(value, blockSignal=self._handle_parameter_change)

    def _update_connection_state(self, is_connected: bool):
        """Update UI based on connection state."""
        self._parameter_tree.setEnabled(is_connected)
        
        if is_connected:
            self.connect_button.setText("Disconnect")
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: #2ECC71;")  # Green
        else:
            self.connect_button.setText("Connect")
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: #95A5A6;")  # Gray
            
    def _update_error_state(self, error: Optional[str]):
        """Update UI to show error state."""
        if error:
            self.status_label.setText(f"Error: {error}")
            self.status_label.setStyleSheet("color: #E74C3C;")  # Red
            
    def _handle_connect_click(self):
        """Handle connect/disconnect button clicks."""
        if not self.model:
            return
            
        if self.model.get_property('is_connected'):
            self.model.disconnect()
        else:
            self.model.connect()

    def _handle_parameter_change(self, param: Parameter, value: Any):
        """Handle parameter value changes."""
        if self.model and not param.opts.get('readonly', False):
            prop_path = param.opts.get('property_path')
            if prop_path:
                self.model.update_parameter(prop_path, value)

    def update_from_model(self, model: Device):
        """Update view from model data."""
        if not model:
            return
            
        # Create parameter structure from model
        if model.driver_info:
            factory = InstrumentFactory()
            instrument_data = factory.create_instrument_data_from_driver(model.driver_info.get('module'))
            
            # Create root parameter
            root = Parameter.create(
                name=model.get_property('name', 'Device'),
                type='group',
                children=instrument_data.get('parameter_tree', [])
            )
            
            # Store parameters
            self._parameters.clear()
            for param in root.children():
                self._store_parameters(param)
                
            # Set parameters in tree
            self._parameter_tree.setParameters(root)
            
            # Connect signals
            root.sigTreeStateChanged.connect(self._handle_tree_state_changed)
            
        # Update initial state
        self._update_connection_state(model.get_property('is_connected', False))
        error = model.get_property('error_message')
        if error:
            self._update_error_state(error)
        self._update_parameters(model.parameters)
        
    def _store_parameters(self, param: Parameter):
        """Recursively store parameters for lookup."""
        if not param.hasChildren():
            prop_path = param.opts.get('property_path')
            if prop_path:
                self._parameters[prop_path] = param
        else:
            for child in param.children():
                self._store_parameters(child)

    def _handle_tree_state_changed(self, param: Parameter, changes):
        """Handle parameter tree state changes."""
        for param, change, data in changes:
            if change == 'value':
                self._handle_parameter_change(param, data)

    def _update_parameters(self, parameters: Dict[str, Any]):
        """Update all parameters from model state."""
        for path, value in parameters.items():
            if path in self._parameters:
                param = self._parameters[path]
                param.setValue(value, blockSignal=self._handle_parameter_change)