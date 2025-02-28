from typing import Optional, List, Any, Dict
from datetime import datetime
from PySide6.QtWidgets import QApplication

from pymetr.core.logging import logger
from pymetr.models.test import TestScript, TestStatus, TestResult, ResultStatus, TestGroup
from pymetr.models.plot import Plot
from pymetr.models.trace import Trace
from pymetr.models.marker import Marker
from pymetr.models.cursor import Cursor
from pymetr.models.table import DataTable
from pymetr.models.device import Device
from pymetr.drivers.base.connections import PyVisaConnection, RawSocketConnection
from pymetr.ui.dialogs.discovery_dialog import DiscoveryDialog
from pymetr.ui.dialogs.connection_dialog import ConnectionDialog

class TestContext:
    """
    Context object provided to test scripts, encapsulating all allowed operations
    and maintaining script state.
    """
    def __init__(self, script: TestScript, engine):
        self.script = script
        self._engine = engine
        self._state = engine.state
        self.start_time = datetime.now()
        
        # Initialize script status
        self.script.set_property('status', TestStatus.READY)
        self.script.set_property('progress', 0.0)
        
    @property
    def progress(self) -> float:
        """Get current progress."""
        return self.script.get_property('progress', 0.0)
    
    @progress.setter
    def progress(self, value: float):
        """
        Set direct script progress. This will be averaged with result progress
        if results exist.
        """
        value = max(0.0, min(100.0, float(value)))
        self.script.set_property('progress', value)
        
        # If no results exist, this is the only progress
        if not self._get_test_results():
            return
            
        # Otherwise, trigger progress aggregation
        self._update_aggregate_progress()

    @property
    def status(self) -> TestStatus:
        """Get current test status."""
        status_str = self.script.get_property('status', TestStatus.READY.name)
        return TestStatus[status_str]

    @status.setter
    def status(self, value: TestStatus):
        """Set test status."""
        if isinstance(value, str):
            value = TestStatus[value.upper()]
        self.script.set_property('status', value.name)

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return (datetime.now() - self.start_time).total_seconds()
    
    def create_result(self, name: str) -> TestResult:
        """Create a test result with progress tracking."""
        result = self._state.create_model(TestResult, name=name)
        self._state.link_models(self.script.id, result.id)
        
        # Initialize result properties
        result.set_property('status', None)  # Not reported yet
        result.set_property('progress', 0.0)
        
        self._update_aggregate_progress()
        
        return result
    
    def create_group(self, name: str) -> TestGroup:
        """Create a result group for organizing results."""
        group = self._state.create_model(TestGroup, name=name)
        self._state.link_models(self.script.id, group.id)
        return group
    
    def create_plot(self, title: str) -> Plot:
        """Create a plot linked to this test."""
        plot = self._state.create_model(Plot, title=title)
        self._state.link_models(self.script.id, plot.id)
        return plot
    
    def create_trace(self, name: str, x_data, y_data=None, **kwargs) -> Trace:
        """
        Create a trace linked to this test.
        If y_data is None and x_data is a tuple of two arrays, then unpack them.
        """
        if y_data is None and isinstance(x_data, tuple) and len(x_data) == 2:
            x_data, y_data = x_data
        trace = self._state.create_model(Trace, name=name, x_data=x_data, y_data=y_data, **kwargs)
        self._state.link_models(self.script.id, trace.id)
        return trace
    
    def create_table(self, title: str) -> DataTable:
        """Create a table linked to this test."""
        table = self._state.create_model(DataTable, title=title)
        self._state.link_models(self.script.id, table.id)
        return table

    def create_marker(self, name: str, **kwargs) -> Marker:
        """Create a marker linked to this test."""
        marker = self._state.create_model(Marker, name=name, **kwargs)
        self._state.link_models(self.script.id, marker.id)
        return marker

    def create_cursor(self, name: str, **kwargs) -> Cursor:
        """Create a cursor linked to this test."""
        cursor = self._state.create_model(Cursor, name=name, **kwargs)
        self._state.link_models(self.script.id, cursor.id)
        return cursor

    def get_result(self, name: str) -> Optional[TestResult]:
        """Find a result by name."""
        for model in self._state.get_children(self.script.id):
            if isinstance(model, TestResult) and model.get_property('name') == name:
                return model
        return None

    def get_plot(self, title: str) -> Optional[Plot]:
        """Find a plot by title."""
        for model in self._state.get_children(self.script.id):
            if isinstance(model, Plot) and model.get_property('title') == title:
                return model
        return None

    def wait(self, milliseconds: int):
        """Wait without blocking GUI."""
        self._engine.wait(milliseconds)

    # Internal methods
    def _get_test_results(self) -> List[TestResult]:
        """Get all test results created by this script."""
        return [
            model for model in self._state.get_children(self.script.id)
            if isinstance(model, TestResult)
        ]
    
    def _determine_final_status(self) -> TestStatus:
        """Determine final script status based on results."""
        results = self._get_test_results()
        
        if not results:
            return TestStatus.COMPLETE
            
        # Check all result statuses
        has_fails = any(
            result.get_property('status') == ResultStatus.FAIL.name
            for result in results
        )
        
        if has_fails:
            return TestStatus.FAIL
            
        return TestStatus.PASS
    
    def _update_aggregate_progress(self):
        """
        Update script progress based on results.
        Averages progress of all results, or uses script's direct progress
        if no results exist.
        """
        results = self._get_test_results()
        if not results:
            return  # Keep current script progress
            
        # Calculate average progress from all results
        total_progress = sum(
            result.get_property('progress', 0.0)
            for result in results
        )
        avg_progress = total_progress / len(results)
        
        # Update script progress
        self.script.set_property('progress', avg_progress)
    
    def on_script_start(self):
        """Called by engine when script starts."""
        self.script.set_property('status', TestStatus.RUNNING)
        self.start_time = datetime.now()
    
    def on_script_error(self, error: Exception):
        """Called by engine on script error."""
        self.script.set_property('status', TestStatus.ERROR)
        self.script.set_property('error', str(error))
    
    def on_script_complete(self):
        """Called by engine when script finishes."""
        try:
            final_status = self._determine_final_status()
            self.script.set_property('status', final_status)
            self.script.set_property('progress', 100.0)
        except Exception as e:
            logger.error(f"Error determining final status: {e}")
            self.script.set_property('status', TestStatus.ERROR)
            self.script.set_property('error', str(e))
    
    # Add methods for the script engine context
    @classmethod
    def get_instrument(self, model_filter: str = None, resource: str = None) -> Device:
        """
        Get or create an instrument by model or resource.
        
        Args:
            model_filter: String to match against instrument model names
            resource: Specific resource string (e.g., "TCPIP::192.168.1.10::5025::SOCKET")
        
        Returns:
            Device model with connected instrument driver
        """
        # Check if we already have a matching device
        devices = self._state.get_models_by_type(Device)
        
        # If resource is provided, look for exact match
        if resource:
            for device in devices:
                if (device.get_property('resource') == resource and 
                    device.get_property('is_connected')):
                    return device
        
        # If model filter is provided, look for matching model
        elif model_filter:
            for device in devices:
                if (model_filter.lower() in device.get_property('model').lower() and 
                    device.get_property('is_connected')):
                    return device
        
        # No matching connected device, need to discover or create
        if resource:
            # Direct resource connection without discovery
            return self._create_direct_connection(resource)
        else:
            # Show discovery dialog and let user select
            return self._discover_and_connect(model_filter)
    
    def _create_direct_connection(self, resource: str) -> Device:
        """Create a direct connection to a resource without discovery."""
        # Parse resource to determine connection type
        connection_type = "visa"  # Default
        if "::SOCKET" in resource:
            connection_type = "socket"
        elif "ASRL" in resource:
            connection_type = "serial"
        
        # Create device info
        info = {
            'resource': resource,
            'model': f"Device at {resource}",
            'manufacturer': 'Unknown',
            'serial': 'N/A',
            'firmware': 'N/A',
            'connection_type': connection_type
        }
        
        # Create and connect device
        try:
            device = self._state.connect_instrument(info)
            return device
        except Exception as e:
            logger.error(f"Error connecting to {resource}: {e}")
            raise RuntimeError(f"Failed to connect to {resource}: {e}")
    
    def _discover_and_connect(self, model_filter: str = None) -> Device:
        """Show discovery dialog and connect to selected instrument."""
        # Get parent window for dialog
        parent = None
        if QApplication.instance():
            parent = QApplication.activeWindow()
        
        # Show discovery dialog
        from pymetr.ui.dialogs.discovery_dialog import DiscoveryDialog
        from PySide6.QtWidgets import QDialog
        
        dialog = DiscoveryDialog(self._state, model_filter, parent)
        result = dialog.exec()
        
        if result == QDialog.Accepted and dialog.result_info:
            # User selected an instrument, connect to it
            try:
                device = self._state.connect_instrument(dialog.result_info)
                return device
            except Exception as e:
                logger.error(f"Error connecting to selected instrument: {e}")
                raise RuntimeError(f"Failed to connect to instrument: {e}")
        else:
            # User canceled
            raise RuntimeError("No instrument selected")
    
    def create_connection(self, connection_type: str, **kwargs) -> Any:
        """
        Create a raw connection of the specified type.
        
        Args:
            connection_type: Type of connection ('visa', 'socket', 'serial', etc.)
            **kwargs: Connection parameters (resource, host, port, etc.)
        
        Returns:
            ConnectionInterface instance
        """
        if connection_type.lower() == 'visa':
            if 'resource' not in kwargs:
                raise ValueError("Resource string required for VISA connection")
            return PyVisaConnection(kwargs['resource'])
        
        elif connection_type.lower() == 'socket':
            if 'host' not in kwargs:
                raise ValueError("Host required for socket connection")
            
            port = kwargs.get('port', 5025)
            timeout = kwargs.get('timeout', 5.0)
            
            return RawSocketConnection(host=kwargs['host'], port=port, timeout=timeout)
        
        elif connection_type.lower() == 'serial':
            # Placeholder for SerialConnection
            # You'd need to implement SerialConnection in your connections.py file
            raise NotImplementedError("Serial connection not implemented yet")
        
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")
    
    def create_driver(self, driver_name: str, connection) -> Any:
        """
        Create a driver instance with the given connection.
        
        Args:
            driver_name: Name of the driver class or model (e.g., 'Dsox1204g')
            connection: ConnectionInterface instance
        
        Returns:
            Driver instance
        """
        # Use registry to create driver
        from pymetr.core.registry import get_registry
        registry = get_registry()
        
        try:
            # Create driver instance
            # Pass the model name as a string - our updated registry will handle this
            driver = registry.create_driver_instance(driver_name, connection)
            
            if not driver:
                raise RuntimeError(f"Failed to create driver for '{driver_name}'")
                
            return driver
        except Exception as e:
            logger.error(f"Error creating driver '{driver_name}': {e}")
            raise RuntimeError(f"Failed to create driver: {e}")
    
    def send_scpi_command(self, device: Device, command: str) -> str:
        """
        Send a raw SCPI command to a device.
        
        Args:
            device: Device model
            command: SCPI command string
        
        Returns:
            Response string if command is a query, else empty string
        """
        if not device or not device.instrument:
            raise ValueError("Device not connected")
        
        # Log the command
        logger.debug(f"Sending SCPI command to {device.get_property('name')}: {command}")
        
        # Send command
        if command.endswith('?'):
            # It's a query
            return device.instrument.query(command)
        else:
            # It's a write
            device.instrument.write(command)
            return ""
    
    def show_manual_connection_dialog(self) -> Device:
        """
        Show dialog for manual connection to an instrument.
        
        Returns:
            Device model with connected instrument
        """
        # Get parent window for dialog
        parent = None
        if QApplication.instance():
            parent = QApplication.activeWindow()
        
        # Show connection dialog
        from pymetr.ui.dialogs.connection_dialog import ConnectionDialog
        from PySide6.QtWidgets import QDialog
        
        dialog = ConnectionDialog(parent)
        result = dialog.exec()
        
        if result == QDialog.Accepted and dialog.result_info:
            # User provided connection info
            try:
                # Create device
                device = self._state.connect_instrument(dialog.result_info)
                return device
            except Exception as e:
                logger.error(f"Error connecting to instrument: {e}")
                raise RuntimeError(f"Failed to connect to instrument: {e}")
        else:
            # User canceled
            raise RuntimeError("Connection canceled")