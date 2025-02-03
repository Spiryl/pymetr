from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox
)
from PySide6.QtCore import Signal, Qt
from pyqtgraph.parametertree import Parameter, ParameterTree

from pymetr.factories.instrument_factory import InstrumentFactory
from pymetr.models.device import Device
from pymetr.drivers.base import Subsystem, Property
from pymetr.logging import logger

class InstrumentDock(QDockWidget):
    """
    A dock widget that manages SCPI instruments and their UI representation.
    Maps parameter tree items directly to driver properties using SCPI paths.
    """
    traceDataReady = Signal(object)

    def __init__(self, state, parent=None):
        super().__init__("Instruments", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.state = state
        self.instruments: Dict[str, Dict[str, Any]] = {}

        # Main container
        container = QWidget(self)
        self.setWidget(container)
        self.layout = QVBoxLayout(container)
        container.setLayout(self.layout)

        # Connect to state signals
        self.state.signals.connect("instrument_connected", self._on_instrument_connected)

    def _on_instrument_connected(self, device_id: str):
        """Handle new instrument connection"""
        device_model = self.state.registry.get_model(device_id)
        if not device_model:
            logger.error(f"No Device found for ID '{device_id}'")
            return

        if device_id in self.instruments:
            logger.info(f"Device {device_id} already tracked")
            return

        self._setup_instrument(device_model, device_id)

    def _setup_instrument(self, device_model: Device, unique_id: str):
        """Set up UI representation of an instrument"""
        try:
            # Get driver info
            driver_info = device_model.driver_info
            if not driver_info:
                raise ValueError("No driver_info in Device model")

            # Make sure we have a driver instance
            if not device_model.driver_instance:
                raise ValueError("No driver instance - connection may have failed")

            driver_path = self._resolve_driver_path(driver_info)
            logger.debug(f"Loading driver from: {driver_path}")

            # Parse driver metadata
            instrument_data = InstrumentFactory().create_instrument_data_from_driver(driver_path)
            if not instrument_data:
                raise ValueError(f"No data returned from factory for {driver_path}")

            # Create container for this instrument
            instrument_widget = QWidget()
            instrument_layout = QVBoxLayout(instrument_widget)

            # Create parameter tree
            param_tree = self._create_parameter_tree(instrument_data, unique_id)
            tree_widget = ParameterTree()
            tree_widget.setParameters(param_tree, showTop=False)
            instrument_layout.addWidget(tree_widget)

            # Add GUI method buttons
            buttons_widget = self._create_gui_buttons(instrument_data, device_model)
            if buttons_widget:
                instrument_layout.addWidget(buttons_widget)

            self.layout.addWidget(instrument_widget)

            # Store references
            self.instruments[unique_id] = {
                'device': device_model,
                'widget': instrument_widget,
                'param_tree': param_tree,
                'tree_widget': tree_widget,
            }

            # Connect signals
            param_tree.sigTreeStateChanged.connect(
                lambda param, changes: self._on_tree_changes(unique_id, changes)
            )

            # Connect driver signals if available
            if hasattr(device_model, 'driver_instance'):
                driver = device_model.driver_instance
                if hasattr(driver, 'traceDataReady'):
                    driver.traceDataReady.connect(self.traceDataReady.emit)

            # Initial sync
            self._synchronize_parameters(unique_id)

            # Connect to property change signals
            driver = device_model.driver_instance
            self._connect_property_signals(driver, unique_id)

        except Exception as e:
            logger.error(f"Failed to setup device '{unique_id}': {e}", exc_info=True)
            QMessageBox.critical(self, "Instrument Error",
                               f"Could not setup instrument {unique_id}\n{e}")

    def _connect_property_signals(self, driver, unique_id: str):
        """Connect to property change signals in the driver"""
        def on_property_changed(path: str, value: Any):
            """Handle property value changes"""
            param = self.instruments[unique_id]['param_tree'].child(path)
            if param:
                param.setValue(value, blockSignal=self._on_tree_changes)

        # Connect to the driver's property_changed signal
        if hasattr(driver, 'property_changed'):
            driver.property_changed.connect(
                lambda p, v: on_property_changed(p, v)
            )

    def _handle_property_change(self, unique_id: str, property_path: str, value):
        """Handle property changes from the driver"""
        if unique_id not in self.instruments:
            return
            
        param_tree = self.instruments[unique_id]['param_tree']
        param = param_tree.child(property_path)  # Assuming property_path matches parameter name
        
        if param is not None:
            # Block signals to prevent recursion
            param.sigValueChanged.disconnect(self._on_tree_changes)
            try:
                param.setValue(value)
            finally:
                param.sigValueChanged.connect(self._on_tree_changes)

    def _create_parameter_tree(self, instrument_data: dict, unique_id: str) -> Parameter:
        """Create parameter tree with SCPI paths as parameter names"""
        def create_param_dict(prop_info: dict) -> dict:
            """Convert property info to parameter dict"""
            return {
                'name': prop_info['property_path'],    # SCPI path as name
                'title': prop_info['name'],            # Display name
                'type': self._convert_type(prop_info.get('type', 'str')),
                'value': prop_info.get('value'),
                'limits': prop_info.get('limits'),
                'readonly': prop_info.get('readonly', False),
                'suffix': prop_info.get('suffix'),
                'siPrefix': prop_info.get('siPrefix', False),
            }

        def build_tree(data: list) -> list:
            """Recursively build parameter tree structure"""
            tree = []
            for group in data:
                group_dict = {
                    'name': group['name'],     # Group name for internal use
                    'title': group['name'],    # Display name (could be different)
                    'type': 'group',
                    'children': []
                }

                # Process children
                for child in group.get('children', []):
                    if child.get('type') == 'group':
                        group_dict['children'].extend(build_tree([child]))
                    else:
                        param_dict = create_param_dict(child)
                        if param_dict:  # Skip if conversion failed
                            group_dict['children'].append(param_dict)

                tree.append(group_dict)
            return tree

        # Create the main parameter group
        return Parameter.create(
            name=unique_id,
            type='group',
            children=build_tree(instrument_data['parameter_tree'])
        )

    def _create_gui_buttons(self, instrument_data: dict, device_model: Device) -> Optional[QWidget]:
        """Create buttons for GUI methods defined in the driver"""
        if not instrument_data.get('gui_methods'):
            return None

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        for method_name, method_info in instrument_data['gui_methods'].items():
            button = QPushButton(method_name.replace('_', ' ').title())
            button.clicked.connect(lambda checked, m=method_name: 
                                 self._execute_gui_method(device_model, m))
            layout.addWidget(button)

        return container

    def _on_tree_changes(self, unique_id: str, changes):
        """Handle parameter tree changes"""
        for param, change, data in changes:
            if change == 'value':
                scpi_path = param.name()  # This is the property path
                try:
                    device = self.instruments[unique_id]['device']
                    driver = device.driver_instance
                    
                    # Use Python's operator.attrgetter to access nested properties
                    path_parts = scpi_path.split('.')
                    current = driver
                    
                    # Handle indexed access like channel[1]
                    for part in path_parts:
                        if '[' in part:
                            name, idx = part.split('[')
                            idx = int(idx.strip(']'))
                            current = getattr(current, name)[idx]
                        else:
                            current = getattr(current, part)
                    
                    # Set the property value
                    current = data  # This triggers the property setter
                    
                    logger.debug(f"Updated '{scpi_path}' to '{data}' on device '{unique_id}'")
                except Exception as e:
                    logger.error(f"Failed to update '{scpi_path}' with '{data}': {e}")

    def _synchronize_parameters(self, unique_id: str):
        """Synchronize parameter values with device state"""
        device = self.instruments[unique_id]['device']
        driver = device.driver_instance
        param_tree = self.instruments[unique_id]['param_tree']

        def sync_param(param):
            if not param.hasChildren():
                try:
                    path = param.name()  # This is the property path (e.g. "channel[1].frequency")
                    current = driver
                    
                    # Split path and traverse object hierarchy
                    parts = path.split('.')
                    for part in parts:
                        # Handle indexed access like channel[1]
                        if '[' in part:
                            name, idx = part.split('[')
                            idx = int(idx.strip(']'))
                            # Access the subsystem list and get indexed item
                            subsys = getattr(current, name)
                            current = subsys[idx]
                        else:
                            current = getattr(current, part)
                    
                    # Get the value (triggers property getter)
                    try:
                        value = current
                        param.setValue(value, blockSignal=self._on_tree_changes)
                        logger.debug(f"Synced '{path}' to {value}")
                    except Exception as e:
                        logger.error(f"Error getting value for '{path}': {e}")
                        
                except AttributeError as e:
                    logger.error(f"Sync failed for '{param.name()}': {e}")
                except Exception as e:
                    logger.error(f"Sync failed for '{param.name()}': {e}")
            else:
                for child in param.children():
                    sync_param(child)

        for param in param_tree.children():
            sync_param(param)

    def _execute_gui_method(self, device: Device, method_name: str):
        """Execute a GUI method on the device"""
        try:
            if hasattr(device, 'driver_instance'):
                method = getattr(device.driver_instance, method_name)
                method()
        except Exception as e:
            logger.error(f"Failed to execute GUI method '{method_name}': {e}")
            QMessageBox.warning(self, "Method Error",
                              f"Failed to execute {method_name}: {e}")

    @staticmethod
    def _convert_type(prop_type: str) -> str:
        """Convert property types to parameter types"""
        type_map = {
            'valueproperty': 'float',
            'selectproperty': 'list',
            'switchproperty': 'bool',
            'stringproperty': 'str',
        }
        return type_map.get(prop_type.lower(), prop_type)

    @staticmethod
    def _resolve_driver_path(driver_info: dict) -> str:
        """Convert driver_info to absolute path"""
        module = driver_info.get("module", "")
        if module.endswith(".py"):
            module = module[:-3]
        path = module.replace(".", "/") + ".py"
        return f"src/pymetr/{path}"  # Adjust base path as needed