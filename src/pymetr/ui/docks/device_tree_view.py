from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QHeaderView, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from pyqtgraph.parametertree import Parameter, ParameterTree

from pymetr.models.device import Device
from pymetr.ui.views.base import BaseWidget
from pymetr.core.logging import logger

class DeviceTreeView(BaseWidget):
    """
    Widget for device control and monitoring.
    Uses a ParameterTree for property control and updates.
    """
    
    property_changed = Signal(str, str, object)  # model_id, prop_path, value
    
    def __init__(self, state, model_id: Optional[str], parent=None):
        super().__init__(state, parent)
        self.state = state
        self._parameter_tree = None
        self._parameters: Dict[str, Parameter] = {}
        self._setup_ui()

        # Listen for instrument connection signals.
        self.state.instrument_connected.connect(self._on_instrument_connected)
        
        if model_id:
            self.set_model(model_id)

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create control bar.
        control_bar = QWidget()
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(4, 4, 4, 4)
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._handle_connect_click)
        control_layout.addWidget(self.connect_button)
        
        self.status_label = QLabel()
        control_layout.addWidget(self.status_label)
        
        control_layout.addStretch()
        layout.addWidget(control_bar)
        
        # Create ParameterTree widget.
        self._parameter_tree = ParameterTree()
        self._parameter_tree.setAlternatingRowColors(False)
        header = self._parameter_tree.header()
        header.setMinimumSectionSize(100)
        header.setDefaultSectionSize(120)
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        
        self._parameter_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._parameter_tree.setMinimumWidth(200)
        self._parameter_tree.setColumnWidth(0, 120)
        self._parameter_tree.setColumnWidth(1, 120)
        layout.addWidget(self._parameter_tree)

    def _on_instrument_connected(self, device_id: str):
        logger.debug(f"DeviceTreeView received instrument_connected signal for device ID: {device_id}")
        self.set_model(device_id)

    def _handle_model_property_changed(self, model_id, model_type, prop, value):
        if prop == 'parameter_tree':
            self.update_from_model(self.model)

    def _handle_property_update(self, prop: str, value: Any):
        if prop == 'is_connected':
            self._update_connection_state(value)
        elif prop == 'error_message':
            self._update_error_state(value)
        elif prop in self._parameters:
            param = self._parameters[prop]
            param.setValue(value, blockSignal=self._handle_parameter_change)

    def _update_connection_state(self, is_connected: bool):
        self._parameter_tree.setEnabled(is_connected)
        if is_connected:
            self.connect_button.setText("Disconnect")
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: #2ECC71;")
        else:
            self.connect_button.setText("Connect")
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: #95A5A6;")

    def _update_error_state(self, error: Optional[str]):
        if error:
            self.status_label.setText(f"Error: {error}")
            self.status_label.setStyleSheet("color: #E74C3C;")

    def _handle_connect_click(self):
        if not self.model:
            return
        if self.model.get_property('is_connected'):
            self.model.disconnect()
        else:
            self.model.connect()

    def _handle_parameter_change(self, param: Parameter, value: Any):
        if self.model and not param.opts.get('readonly', False):
            prop_path = param.opts.get('property_path')
            if prop_path:
                self.model.update_parameter(prop_path, value)

    def update_from_model(self, model: Device):
        if not model:
            return
        
        logger.debug("DeviceTreeView.update_from_model: Updating view from model data.")
        # Retrieve the UI-friendly parameter tree from the device.
        instrument_config = model.get_property('parameter_tree', [])
        logger.debug("DeviceTreeView.update_from_model: Retrieved instrument_config: %s", instrument_config)
        
        # Expect instrument_config to be a list (as produced by the factory).
        if instrument_config and isinstance(instrument_config, list):
            # Use the first group as the root.
            root_data = instrument_config[0]
            logger.debug("DeviceTreeView.update_from_model: Using first group as root: %s", root_data)
        else:
            root_data = {'children': []}
            logger.debug("DeviceTreeView.update_from_model: No valid instrument_config found; using empty root.")
        
        root = Parameter.create(
            name=model.get_property('name', 'Device'),
            type='group',
            children=root_data.get('children', [])
        )
        logger.debug("DeviceTreeView.update_from_model: Created root parameter: %s", root)
        
        self._parameters.clear()
        for param in root.children():
            self._store_parameters(param)
            logger.debug("DeviceTreeView.update_from_model: Stored parameter: %s", param)
        
        self._parameter_tree.setParameters(root)
        logger.debug("DeviceTreeView.update_from_model: Set parameters in the tree widget.")
        
        root.sigTreeStateChanged.connect(self._handle_tree_state_changed)
        logger.debug("DeviceTreeView.update_from_model: Connected root sigTreeStateChanged signal.")
        
        is_connected = model.get_property('is_connected', False)
        self._update_connection_state(is_connected)
        logger.debug("DeviceTreeView.update_from_model: Updated connection state to %s.", is_connected)
        
        error = model.get_property('error_message')
        if error:
            self._update_error_state(error)
            logger.debug("DeviceTreeView.update_from_model: Updated error state with error: %s", error)

    def _store_parameters(self, param: Parameter):
        if not param.hasChildren():
            prop_path = param.opts.get('property_path')
            if prop_path:
                self._parameters[prop_path] = param
        else:
            for child in param.children():
                self._store_parameters(child)

    def _handle_tree_state_changed(self, param: Parameter, changes):
        for param, change, data in changes:
            if change == 'value':
                self._handle_parameter_change(param, data)

    def _update_parameters(self, parameters: Dict[str, Any]):
        for path, value in parameters.items():
            if path in self._parameters:
                param = self._parameters[path]
                param.setValue(value, blockSignal=self._handle_parameter_change)
