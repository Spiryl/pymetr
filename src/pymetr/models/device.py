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
    acquire_requested = Signal(str)  # device_id
    connection_changed = Signal(bool)
    error_occurred = Signal(str)
    
    def __init__(self, 
                manufacturer: Optional[str] = None,
                model: Optional[str] = None,
                serial_number: Optional[str] = None,
                firmware: Optional[str] = None,
                resource: Optional[str] = None,
                model_id: Optional[str] = None,
                state=None):  # Add state parameter
        """Initialize device model with discovery information."""
        # Generate a proper name using model and serial number
        name = f"{model}-{serial_number}" if model and serial_number else "Unnamed Device"
        
        super().__init__(model_type="Device", model_id=model_id, state=state, name=name)
        
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


    # Claude made me do it!
    def __getattr__(self, name):
        """Delegate to instrument driver if attribute not found."""
        if self.instrument and hasattr(self.instrument, name):
            return getattr(self.instrument, name)
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")

    @classmethod
    def from_discovery_info(cls, info: Dict[str, str], state=None) -> 'Device':
        """Create Device instance from discovery information."""
        logger.debug(f"Device.from_discovery_info: Creating device from {info}")
        device = cls(
            manufacturer=info.get('manufacturer'),
            model=info.get('model'),
            serial_number=info.get('serial'),
            firmware=info.get('firmware'),
            resource=info.get('resource'),
            state=state  # Pass state explicitly
        )
        logger.debug(f"Device.from_discovery_info: Created device {device.id}")
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
        
        # Emit signal for instrument to respond
        self.acquire_requested.emit(self.id)

        if mode in [AcquisitionMode.SINGLE, AcquisitionMode.STACK]:
            self._acquire_single()
        else:
            self._acquisition_timer.start(100)

    def stop_acquisition(self):
        """Stop any ongoing acquisition."""
        self._acquisition_timer.stop()
        self.set_property('is_acquiring', False)

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
            
            # Find the actual path to the driver file
            try:
                driver_file_path = inspect.getfile(driver_class)
                logger.debug(f"Device._load_driver_info: Found driver file at: {driver_file_path}")
                
                # Use InstrumentFactory to build the UI-friendly configuration.
                from pymetr.ui.factories.instrument_factory import InstrumentFactory
                factory = InstrumentFactory()
                logger.debug("Device._load_driver_info: Creating UI configuration from driver file")
                ui_config = factory.create_instrument_data_from_driver(driver_file_path)
                logger.debug(f"Device._load_driver_info: UI configuration: {ui_config}")
            except (TypeError, ValueError) as e:
                # Fall back to getsource if getfile fails
                logger.warning(f"Could not get file path for driver class: {e}, falling back to getsource")
                driver_source = inspect.getsource(driver_class)
                from pymetr.ui.factories.instrument_factory import InstrumentFactory
                factory = InstrumentFactory()
                ui_config = factory.create_ui_configuration_from_source(driver_source)
            
            # We expect ui_config to contain a 'parameter_tree' key which is a list.
            self._parameter_tree = ui_config.get('parameter_tree', [])
            logger.debug(f"Device._load_driver_info: UI parameter tree set to: {self._parameter_tree}")
            
            self.set_property('parameter_tree', self._parameter_tree)
            logger.debug("Device._load_driver_info: Parameter tree set as property")
            
        except Exception as e:
            logger.error(f"Device._load_driver_info: Error loading driver info: {e}", exc_info=True)
            self.error_message = f"Failed to load driver: {str(e)}"

    def connect_device(self):
        """Connect device and load driver."""
        try:
            logger.debug("Device.connect_device: Initiating connection sequence")
            
            # Load driver info first
            self._load_driver_info()
            
            # Create and connect instrument
            from pymetr.core.registry import get_registry
            registry = get_registry()
            
            # Create connection
            connection = self._create_connection()
            
            # Explicitly open connection before passing to driver
            try:
                connection.open()
                logger.debug("Device.connect_device: Connection opened successfully")
            except Exception as e:
                logger.error(f"Device.connect_device: Failed to open connection: {e}")
                raise ConnectionError(f"Failed to open connection: {e}")
            
            # Try to create a driver instance
            try:
                # Pass self (the Device object) to the registry
                self.instrument = registry.create_driver_instance(
                    self,  # Using self as the Device object
                    connection
                )
            except Exception as driver_error:
                # If driver creation fails, fall back to generic SCPIInstrument
                logger.warning(f"Failed to create specific driver: {driver_error}. Falling back to generic SCPIInstrument.")
                from pymetr.drivers.base.instrument import SCPIInstrument
                self.instrument = SCPIInstrument(connection)
                # Set a flag to indicate we're using a generic driver
                self.set_property('using_generic_driver', True)
            
            if not self.instrument:
                connection.close()  # Clean up the connection
                raise RuntimeError("Failed to create instrument driver")
                
            # Check connection by querying IDN
            try:
                # Try different IDN query methods
                if hasattr(self.instrument, 'query'):
                    idn = self.instrument.query("*IDN?")
                    logger.debug(f"Connected to instrument: {idn}")
                else:
                    logger.warning("No query method found on instrument")
            except Exception as e:
                logger.warning(f"IDN check failed, but continuing: {e}")
            
            # Connect to instrument signals - with careful checking
            self._connect_instrument_signals()
            
            # Set connection state
            self.set_property('is_connected', True)
            self.connection_changed.emit(True)
            
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Device.connect_device error: {e}")
            raise

    def disconnect(self):
        """Disconnect instrument with improved cleanup."""
        try:
            # First disconnect signals
            self._disconnect_instrument_signals()
            
            # Then disconnect the instrument
            if self.instrument:
                logger.debug("Device.disconnect: Closing instrument connection")
                try:
                    # Try to close the connection if supported
                    if hasattr(self.instrument, 'close'):
                        self.instrument.close()
                    # Some drivers might have the connection directly accessible
                    elif hasattr(self.instrument, 'connection') and hasattr(self.instrument.connection, 'close'):
                        self.instrument.connection.close()
                except Exception as e:
                    logger.warning(f"Error during instrument close: {e}")
                
                # Clear the reference regardless of close success/failure
                self.instrument = None
                
            # Update state
            self.set_property('is_connected', False)
            self.connection_changed.emit(False)
            logger.info("Device disconnected successfully")
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Error during disconnect: {e}")
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

    def update_parameter(self, path: str, value: Any, validate: bool = True) -> None:
        """
        Update a parameter value in the device's state and optionally validate.
        
        Args:
            path: Path in format "subsystem[index].property"
            value: New value to set
            validate: If True, query the device after setting to validate
        """
        try:
            logger.debug(f"Device.update_parameter: Updating parameter '{path}' with value '{value}'")
            
            # Parse path with support for indexed subsystems
            import re
            match = re.match(r'(\w+)(?:\[(\d+)\])?\.(\w+)', path)
            if not match:
                raise ValueError(f"Invalid property path format: {path}")
                
            subsystem_name, index_str, prop_name = match.groups()
            
            # Get the subsystem
            if not hasattr(self.instrument, subsystem_name):
                raise ValueError(f"Subsystem '{subsystem_name}' not found")
                
            subsystem = getattr(self.instrument, subsystem_name)
            
            # Handle indexed subsystems
            if index_str is not None:
                index = int(index_str)
                if not isinstance(subsystem, (list, tuple)) or index >= len(subsystem):
                    raise ValueError(f"Invalid index {index} for subsystem {subsystem_name}")
                subsystem = subsystem[index]
            
            # Set the property value
            if hasattr(subsystem, prop_name):
                # This will use the property descriptor's __set__ method
                setattr(subsystem, prop_name, value)
                
                # If validation is requested, read back the value
                if validate:
                    # Use the property descriptor's __get__ method (issues a query)
                    updated_value = getattr(subsystem, prop_name)
                    # Update UI with the actual device value
                    self.property_changed.emit(self.id, self.model_type, path, updated_value)
            else:
                raise ValueError(f"Property '{prop_name}' not found in subsystem {subsystem_name}")
                
            logger.debug(f"Device.update_parameter: Successfully updated {path} to {value}")
            
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
        """Connect to instrument signals with extra care for different implementations."""
        if self.instrument:
            # Clear any existing connections
            self._disconnect_instrument_signals()
            
            try:
                # Only try to connect signals that are actually available
                if hasattr(self.instrument, 'commandSent'):
                    signal = self.instrument.commandSent
                    if hasattr(signal, 'connect'):
                        self._instrument_connections.append(
                            signal.connect(self._handle_command)
                        )
                        logger.debug("Connected to commandSent signal")

                if hasattr(self.instrument, 'responseReceived'):
                    signal = self.instrument.responseReceived
                    if hasattr(signal, 'connect'):
                        self._instrument_connections.append(
                            signal.connect(self._handle_response)
                        )
                        logger.debug("Connected to responseReceived signal")

                if hasattr(self.instrument, 'exceptionOccured'):
                    signal = self.instrument.exceptionOccured
                    if hasattr(signal, 'connect'):
                        self._instrument_connections.append(
                            signal.connect(self._handle_error)
                        )
                        logger.debug("Connected to exceptionOccured signal")
                        
                self.append_output("Connected to instrument signals", "response")
            except Exception as e:
                logger.error(f"Error connecting to instrument signals: {e}")
                # Don't let signal connection problems prevent device creation

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
