from typing import Dict, Any, Optional, List
from enum import Enum
from collections import deque
import importlib
import inspect
import time
import numpy as np
from PySide6.QtCore import Signal, QTimer

from pymetr.models.base import BaseModel
from pymetr.models.plot import Plot
from pymetr.models.trace import Trace
from pymetr.drivers.instruments.plugin import get_driver_info
from pymetr.core.logging import logger

class AcquisitionMode(Enum):
    SINGLE = "SINGLE"      # One-shot acquisition
    STACK = "STACK"        # Keep traces, add new ones
    CONTINUOUS = "CONTINUOUS"  # Clear and update continuously
    AVERAGE = "AVERAGE"    # Average N acquisitions then stop
    MAX_HOLD = "MAX_HOLD"  # Show live data and max envelope
    ROLLING_AVG = "ROLLING_AVG"  # Show live data and rolling average

class Device(BaseModel):
    """Device model representing a discovered instrument."""
    
    # Signals for UI updates
    connection_changed = Signal(bool)
    error_occurred = Signal(str)
    
    def __init__(self, 
                 manufacturer: Optional[str] = None,
                 model: Optional[str] = None,
                 serial_number: Optional[str] = None,
                 firmware: Optional[str] = None,
                 resource: Optional[str] = None,
                 model_id: Optional[str] = None):
        """Initialize device model with discovery information."""
        super().__init__(model_type="Device", model_id=model_id)
        
        # Internal state
        self.instrument = None  # Will hold driver instance
        self._instrument_connections = []
        self._driver_info: Dict[str, Any] = {}
        self._parameter_tree: Any = {}
        self._error_message: Optional[str] = None
        
        # Set basic device properties
        name = f"{model}-{serial_number}" if model and serial_number else "Unnamed Device"
        self.set_property('name', name)
        self.set_property('model', model or '')
        self.set_property('manufacturer', manufacturer or '')
        self.set_property('serial', serial_number or '')
        self.set_property('firmware', firmware or '')
        self.set_property('resource', resource or '')
        self.set_property('connection_string', resource or '')
        self.set_property('is_connected', False)
        
        # Acquisition settings
        self.set_property('acquisition_mode', AcquisitionMode.SINGLE.value)
        self.set_property('averaging_count', 10)
        self.set_property('is_acquiring', False)
        
        # Acquisition state
        self._acquisition_timer = QTimer()
        self._acquisition_timer.timeout.connect(self._handle_acquisition)
        self._avg_data = {}  # name -> (count, (x_data, y_data))
        self._max_hold_data = {}  # name -> (x_data, max_y_data)
        self._rolling_buffers = {}  # name -> deque of last N traces
        
        # Create default plot
        self._create_default_plot()

    @classmethod
    def from_discovery_info(cls, info: Dict[str, str]) -> 'Device':
        """Create Device instance from discovery information."""
        device = cls(
            manufacturer=info.get('manufacturer'),
            model=info.get('model'),
            serial_number=info.get('serial'),
            firmware=info.get('firmware'),
            resource=info.get('resource')
        )
        return device

    def _create_default_plot(self):
        """Create default plot for device data."""
        plot = self.state.create_model(Plot, 
            name=f"{self.get_property('model')} Plot",
            title=f"{self.get_property('model')} Data"
        )
        self.state.link_models(self.id, plot.id)
        self.set_property('default_plot_id', plot.id)

    @property
    def default_plot(self):
        """Get default plot for device data."""
        plot_id = self.get_property('default_plot_id')
        if plot_id:
            return self.state.get_model(plot_id)
        return None

    def _handle_acquisition(self):
        """Handle timer-based acquisition."""
        if not self.get_property('is_acquiring'):
            self._acquisition_timer.stop()
            return

        mode = AcquisitionMode(self.get_property('acquisition_mode'))
        plot = self.default_plot
        if not plot:
            return

        try:
            traces = self.instrument.fetch_trace()
            if not traces:
                return

            for trace in traces:
                name = trace.get_property('name')
                x_data, y_data = trace.data

                if mode == AcquisitionMode.MAX_HOLD:
                    # Update live trace
                    plot.set_trace(name, trace.data)
                    
                    # Update max hold trace
                    if name not in self._max_hold_data:
                        self._max_hold_data[name] = (x_data, y_data.copy())
                    else:
                        _, max_y = self._max_hold_data[name]
                        np.maximum(max_y, y_data, out=max_y)
                    
                    # Display max hold trace
                    max_data = (x_data, self._max_hold_data[name][1])
                    plot.set_trace(f"{name}_Max", max_data, 
                                 color='#FFA500', style='dash')

                elif mode == AcquisitionMode.ROLLING_AVG:
                    # Update rolling buffer
                    avg_count = self.get_property('averaging_count', 10)
                    if name not in self._rolling_buffers:
                        self._rolling_buffers[name] = deque(maxlen=avg_count)
                    
                    self._rolling_buffers[name].append(y_data)
                    
                    # Update live trace
                    plot.set_trace(name, trace.data)
                    
                    # Calculate and display rolling average
                    avg_y = np.mean(self._rolling_buffers[name], axis=0)
                    plot.set_trace(f"{name}_Avg", (x_data, avg_y),
                                 color='#4169E1', width=2)

                elif mode == AcquisitionMode.CONTINUOUS:
                    plot.set_trace(name, trace.data)

                elif mode == AcquisitionMode.AVERAGE:
                    if name not in self._avg_data:
                        self._avg_data[name] = (1, trace.data)
                    else:
                        count, (avg_x, avg_y) = self._avg_data[name]
                        avg_y = (avg_y * count + y_data) / (count + 1)
                        self._avg_data[name] = (count + 1, (avg_x, avg_y))

                    count, avg_data = self._avg_data[name]
                    plot.set_trace(f'{name}_avg', avg_data,
                                 color='#4169E1', width=2)

                    if count >= self.get_property('averaging_count', 10):
                        del self._avg_data[name]
                        if not self._avg_data:
                            self.stop_acquisition()

        except Exception as e:
            self.set_property('error_message', str(e))
            self.stop_acquisition()

    def _acquire_single(self):
        """Handle single/stack acquisition."""
        try:
            traces = self.instrument.fetch_trace()
            if not traces:
                return

            plot = self.default_plot
            if not plot:
                return

            mode = AcquisitionMode(self.get_property('acquisition_mode'))

            if mode == AcquisitionMode.SINGLE:
                # Get current trace names
                existing_traces = set()
                for trace in traces:
                    name = trace.get_property('name')
                    existing_traces.add(name)
                    plot.set_trace(name, trace.data)

                # Remove any traces that weren't updated
                for child in plot.get_children():
                    if (isinstance(child, Trace) and 
                        child.get_property('name') not in existing_traces):
                        self.state.remove_model(child.id)

            else:  # STACK mode
                timestamp = time.strftime('%H:%M:%S')
                for trace in traces:
                    name = f"{trace.get_property('name')}_{timestamp}"
                    plot.set_trace(name, trace.data)

        except Exception as e:
            self.set_property('error_message', str(e))
        finally:
            self.stop_acquisition()

    def start_acquisition(self):
        """Start acquisition based on current mode."""
        if not self.get_property('is_connected'):
            return

        mode = AcquisitionMode(self.get_property('acquisition_mode'))
        
        # Clear appropriate state data
        if mode == AcquisitionMode.MAX_HOLD:
            self._max_hold_data.clear()
        elif mode == AcquisitionMode.ROLLING_AVG:
            self._rolling_buffers.clear()
        elif mode == AcquisitionMode.AVERAGE:
            self._avg_data.clear()

        self.set_property('is_acquiring', True)

        if mode in [AcquisitionMode.SINGLE, AcquisitionMode.STACK]:
            self._acquire_single()
        else:
            self._acquisition_timer.start(100)

    def stop_acquisition(self):
        """Stop any ongoing acquisition."""
        self._acquisition_timer.stop()
        self.set_property('is_acquiring', False)
            
    @classmethod
    def from_discovery_info(cls, info: Dict[str, str]) -> 'Device':
        """Create Device instance from discovery information."""
        logger.debug(f"Device.from_discovery_info: Creating device from {info}")
        device = cls(
            manufacturer=info.get('manufacturer'),
            model=info.get('model'),
            serial_number=info.get('serial'),
            firmware=info.get('firmware'),
            resource=info.get('resource')
        )
        logger.debug(f"Device.from_discovery_info: Created device {device.id}")
        return device

    def _load_driver_info(self) -> None:
        """Load driver information and build parameter tree."""
        try:
            model = self.get_property('model')
            logger.debug(f"Device._load_driver_info: Starting to load driver info for model '{model}'")
            
            # Get driver info from registry
            driver_info = get_driver_info(model)
            logger.debug(f"Device._load_driver_info: Retrieved driver info: {driver_info}")
            self._driver_info = driver_info
            
            # Import driver module
            module_name = driver_info['module']
            logger.debug(f"Device._load_driver_info: Importing module '{module_name}'")
            module = importlib.import_module(module_name)
            logger.debug(f"Device._load_driver_info: Module '{module_name}' imported successfully")
            
            # Retrieve driver class
            class_name = driver_info['class']
            logger.debug(f"Device._load_driver_info: Retrieving driver class '{class_name}'")
            driver_class = getattr(module, class_name)
            logger.debug(f"Device._load_driver_info: Driver class '{class_name}' retrieved successfully")
            
            # Use InstrumentFactory to build the UI-friendly configuration.
            from pymetr.core.factory import InstrumentFactory
            factory = InstrumentFactory()
            logger.debug("Device._load_driver_info: Retrieving driver source code")
            driver_source = inspect.getsource(driver_class)
            logger.debug("Device._load_driver_info: Creating UI configuration from driver source")
            ui_config = factory.create_ui_configuration_from_source(driver_source)
            logger.debug(f"Device._load_driver_info: UI configuration: {ui_config}")
            
            # We expect ui_config to contain a 'parameter_tree' key which is a list.
            self._parameter_tree = ui_config.get('parameter_tree', [])
            logger.debug(f"Device._load_driver_info: UI parameter tree set to: {self._parameter_tree}")
            
            self.set_property('parameter_tree', self._parameter_tree)
            logger.debug("Device._load_driver_info: Parameter tree set as property")
            
        except Exception as e:
            logger.error(f"Device._load_driver_info: Error loading driver info: {e}")
            self.error_message = f"Failed to load driver: {str(e)}"

    def connect_device(self):
        """Connect device and load driver."""
        try:
            logger.debug("Device.connect_device: Initiating connection sequence")
            
            # Load driver info first
            self._load_driver_info()
            
            if not self._driver_info:
                raise ValueError("No driver info loaded")
                
            # Create and connect instrument
            from pymetr.core.registry import get_registry
            registry = get_registry()
            
            connection = self._create_connection()
            self.instrument = registry.create_driver_instance(
                self,
                connection
            )
            
            # Connect to instrument signals
            self._connect_instrument_signals()
            
            # Store parameter tree for UI
            self.set_property('parameter_tree', self._parameter_tree)
            
            # Set connection state
            self.set_property('is_connected', True)
            self.connection_changed.emit(True)
            
        except Exception as e:
            self.error_message = str(e)
            raise

    def disconnect(self):
        """Disconnect instrument."""
        try:
            if self.instrument:
                self._disconnect_instrument_signals()
                self.instrument.close()
                self.instrument = None
            self.set_property('is_connected', False)
            self.connection_changed.emit(False)
        except Exception as e:
            self.error_message = str(e)
            raise

    @property
    def driver_info(self) -> Dict[str, Any]:
        """Get driver information dictionary."""
        return self._driver_info.copy()

    @property
    def parameter_tree(self) -> Any:
        """Get parameter tree structure (UI configuration)."""
        return self._parameter_tree

    @property
    def error_message(self) -> Optional[str]:
        """Get current error message, if any."""
        return self._error_message

    @error_message.setter
    def error_message(self, value: Optional[str]):
        """Set error message and update property."""
        self._error_message = value
        self.set_property('error_message', value)
        if value:
            self.error_occurred.emit(value)

    def update_parameter(self, path: str, value: Any) -> None:
        """
        Update a parameter value in the device's state.
        """
        try:
            logger.debug(f"Device.update_parameter: Updating parameter '{path}' with value '{value}'")
            parts = path.split('.')
            current = self._parameter_tree
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                    logger.debug(f"Device.update_parameter: Created intermediate node for '{part}'")
                current = current[part]
            current[parts[-1]] = value
            logger.debug(f"Device.update_parameter: Parameter '{path}' updated to '{value}'")
            self.property_changed.emit(self.id, self.model_type, path, value)
        except Exception as e:
            logger.error(f"Device.update_parameter: Error updating parameter {path}: {e}")
            self.error_message = f"Failed to update {path}: {str(e)}"

    def set_connection_state(self, connected: bool) -> None:
        """
        Update device connection state.
        """
        if self.get_property('is_connected') != connected:
            self.set_property('is_connected', connected)
            self.connection_changed.emit(connected)
            if not connected:
                self.error_message = None

    def refresh_parameters(self) -> None:
        """
        Refresh parameter tree from driver.
        """
        if self._driver_info:
            logger.debug("Device.refresh_parameters: Refreshing parameters from driver")
            self._load_driver_info()

    def reset_state(self) -> None:
        """Reset device state to defaults."""
        self.set_connection_state(False)
        self.error_message = None
        self._parameter_tree = {}
        self.set_property('parameter_tree', self._parameter_tree)

    def _connect_instrument_signals(self):
        """Connect to instrument property changes."""
        if self.instrument:
            # Clear any existing connections
            self._disconnect_instrument_signals()
            
            # Connect property changes
            self._instrument_connections.extend([
                self.instrument.commandSent.connect(self._handle_command),
                self.instrument.responseReceived.connect(self._handle_response),
                self.instrument.exceptionOccured.connect(self._handle_error),
                self.instrument.property_changed.connect(self._handle_instrument_property)
            ])

    def _disconnect_instrument_signals(self):
        """Clean up instrument signal connections."""
        for connection in self._instrument_connections:
            try:
                connection.disconnect()
            except:
                pass
        self._instrument_connections.clear()

    def _handle_instrument_property(self, prop: str, value: Any):
        """Propagate instrument property changes to parameter tree."""
        # Update parameter tree if needed
        if prop in self._parameter_tree:
            self.update_parameter(prop, value)

    def _create_connection(self) -> 'ConnectionInterface':
        """Create appropriate connection based on resource string."""
        from pymetr.drivers.base.connections import PyVisaConnection, RawSocketConnection
        
        resource = self.get_property('resource')
        if not resource:
            raise ValueError("No resource string available")
            
        # Determine connection type from resource string
        if resource.startswith('TCPIP') and '::SOCKET' in resource:
            return RawSocketConnection(resource)
        else:
            return PyVisaConnection(resource)
        
    def cleanup(self):
        """Clean up resources."""
        try:
            if self.instrument:
                self.disconnect()
            self._disconnect_instrument_signals()
        except:
            pass
        super().cleanup()

    def _handle_command(self, command: str):
        """Handle SCPI command sent."""
        logger.debug(f"Command sent: {command}")

    def _handle_response(self, command: str, response: str):
        """Handle SCPI command response."""
        logger.debug(f"Response to {command}: {response}")

    def _handle_error(self, error: str):
        """Handle SCPI command error."""
        logger.error(f"SCPI error: {error}")
        self.error_message = error
