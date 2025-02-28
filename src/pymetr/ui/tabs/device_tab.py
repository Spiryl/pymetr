from pathlib import Path
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from pymetr.models.device import AcquisitionMode, Device
from .base import BaseTab
from pymetr.ui.views.device_view import DeviceView  # New view replacing the old SCPIConsole
from pymetr.core.logging import logger

class DeviceTab(BaseTab):
    """
    Device tab that wraps a DeviceView with additional toolbar commands,
    command entry area, and device-specific controls.
    """
    
    # Icon mapping for toolbar
    TOOLBAR_ICONS = {
        'connect': 'connect.png',
        'disconnect': 'disconnect.png',
        'acquire': 'acquire.png',
        'stop': 'stop.png',
        'reset': 'reset.png',
        'clear': 'clear.png',
        'save': 'save.png',
        'preset': 'preset.png'
    }
    
    def __init__(self, state, model_id: str, parent=None):
        super().__init__(state, model_id, parent)
        # Connect to device signals
        model = self.state.get_model(model_id)
        if isinstance(model, Device):
            model.connection_changed.connect(self._handle_connection_changed)
            model.error_occurred.connect(self._handle_error)
    
    def _get_icon(self, name: str) -> QIcon:
        icon_file = self.TOOLBAR_ICONS.get(name)
        if icon_file:
            icon_path = str(Path(__file__).parent.parent / 'icons' / icon_file)
            return QIcon(icon_path)
        return QIcon()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Setup enhanced toolbar with extra commands
        self._setup_toolbar()
        
        # Create a splitter to hold the plot and device view
        from PySide6.QtWidgets import QSplitter
        self.splitter = QSplitter(Qt.Vertical)
        
        # Get the device's default plot view
        model = self.state.get_model(self._model_id)
        if isinstance(model, Device):
            plot_id = model.get_property('default_plot_id')
            if plot_id:
                from pymetr.ui.views.plot.plot_view import PlotView
                self.plot_view = PlotView(self.state, plot_id, self)
                self.splitter.addWidget(self.plot_view)
        
        # Main content area: use DeviceView 
        self.device_view = DeviceView(self.state, self._model_id, self)
        self.splitter.addWidget(self.device_view)
        
        # Add splitter to layout
        layout.addWidget(self.splitter)
        
        # Command entry area for SCPI commands (Write/Read/Query)
        cmd_layout = QHBoxLayout()
        cmd_layout.setContentsMargins(6, 6, 6, 6)
        cmd_layout.setSpacing(4)
        
        self.cmd_entry = QLineEdit()
        self.cmd_entry.setPlaceholderText("Enter SCPI command...")
        self.cmd_entry.returnPressed.connect(self._handle_query)
        cmd_layout.addWidget(self.cmd_entry, 1)
        
        self.write_btn = QPushButton("Write")
        self.write_btn.clicked.connect(self._handle_write)
        cmd_layout.addWidget(self.write_btn)
        
        self.read_btn = QPushButton("Read")
        self.read_btn.clicked.connect(self._handle_read)
        cmd_layout.addWidget(self.read_btn)
        
        self.query_btn = QPushButton("Query")
        self.query_btn.clicked.connect(self._handle_query)
        cmd_layout.addWidget(self.query_btn)
        
        layout.addLayout(cmd_layout)
    
    def _setup_toolbar(self):
        # Connection controls
        self.toolbar.addButton("Connect", self._get_icon('connect'), self._handle_connect)
        self.toolbar.addButton("Disconnect", self._get_icon('disconnect'), self._handle_disconnect)
        self.toolbar.addSeparator()
        
        # Acquisition controls
        self.mode_combo = self.toolbar.addComboBox(
            "Mode",
            [mode.value for mode in AcquisitionMode],
            self._handle_mode_change
        )
        self.toolbar.addButton("Acquire", self._get_icon('acquire'), self._handle_acquire)
        self.toolbar.addButton("Stop", self._get_icon('stop'), self._handle_stop)
        self.toolbar.addSeparator()
        
        # IEEE 488.2 controls
        self.toolbar.addButton("Reset (*RST)", self._get_icon('reset'), self._handle_reset)
        self.toolbar.addButton("Clear (*CLS)", self._get_icon('clear'), self._handle_clear)
        self.toolbar.addButton("Save", self._get_icon('save'), self._handle_save)
        self.toolbar.addButton("Preset", self._get_icon('preset'), self._handle_preset)
    
    def _handle_connect(self):
        """Handle connect button with more robust error handling."""
        try:
            model = self.state.get_model(self.model_id)
            if model:
                # Use connect_device() consistently 
                self.device_view.append_output("Connecting to instrument...", "command")
                model.connect_device()
                self.toolbar.get_button("Connect").setEnabled(False)
                self.toolbar.get_button("Disconnect").setEnabled(True)
                self._update_control_states(True)
                self.device_view.append_output("Connected successfully", "response")
        except Exception as e:
            self.state.set_error(str(e))
            self.device_view.append_output(f"Connection failed: {str(e)}", "error")
    
    def _handle_disconnect(self):
        try:
            model = self.state.get_model(self.model_id)
            if model:
                model.disconnect()
                self.toolbar.get_button("Connect").setEnabled(True)
                self.toolbar.get_button("Disconnect").setEnabled(False)
                self._update_control_states(False)
        except Exception as e:
            self.state.set_error(str(e))
    
    def _handle_mode_change(self, mode: str):
        try:
            model = self.state.get_model(self.model_id)
            if model:
                model.set_property('acquisition_mode', mode)
                is_continuous = mode in ['CONTINUOUS', 'AVERAGE']
                self.toolbar.get_button("Stop").setEnabled(is_continuous)
        except Exception as e:
            self.state.set_error(str(e))
    
    def _handle_acquire(self):
        try:
            model = self.state.get_model(self.model_id)
            if model:
                model.start_acquisition()
                self.toolbar.get_button("Acquire").setEnabled(False)
                self.toolbar.get_button("Stop").setEnabled(True)
                self.mode_combo.setEnabled(False)
        except Exception as e:
            self.state.set_error(str(e))
    
    def _handle_stop(self):
        try:
            model = self.state.get_model(self.model_id)
            if model:
                model.stop_acquisition()
                self.toolbar.get_button("Acquire").setEnabled(True)
                self.toolbar.get_button("Stop").setEnabled(False)
                self.mode_combo.setEnabled(True)
        except Exception as e:
            self.state.set_error(str(e))
    
    def _handle_reset(self):
        try:
            model = self.state.get_model(self.model_id)
            if model and model.instrument:
                model.instrument.reset()
                self.state.set_info("Instrument reset complete")
        except Exception as e:
            self.state.set_error(str(e))
    
    def _handle_clear(self):
        try:
            model = self.state.get_model(self.model_id)
            if model and model.instrument:
                model.instrument.clear_status_registers()
                self.state.set_info("Status registers cleared")
        except Exception as e:
            self.state.set_error(str(e))
    
    def _handle_save(self):
        try:
            model = self.state.get_model(self.model_id)
            if model and model.instrument:
                model.instrument.write("*SAV 1")
                self.state.set_info("Instrument state saved")
        except Exception as e:
            self.state.set_error(str(e))
    
    def _handle_preset(self):
        try:
            model = self.state.get_model(self.model_id)
            if model and model.instrument:
                model.instrument.write("*RST;*CLS")
                self.state.set_info("Instrument preset complete")
        except Exception as e:
            self.state.set_error(str(e))
    
    def _handle_write(self):
        command = self.cmd_entry.text().strip()
        if not command:
            return
        model = self.state.get_model(self.model_id)
        if model and hasattr(model, 'instrument') and model.instrument:
            try:
                model.instrument.write(command)
            except Exception as e:
                self.device_view.append_output(f"Error: {str(e)}", "error")
        else:
            self.device_view.append_output("No instrument connected", "error")
        self.cmd_entry.clear()
    
    def _handle_read(self):
        model = self.state.get_model(self.model_id)
        if model and hasattr(model, 'instrument') and model.instrument:
            try:
                model.instrument.read()
            except Exception as e:
                self.device_view.append_output(f"Error: {str(e)}", "error")
        else:
            self.device_view.append_output("No instrument connected", "error")
    
    def _handle_query(self):
        command = self.cmd_entry.text().strip()
        if not command:
            return
        model = self.state.get_model(self.model_id)
        if model and hasattr(model, 'instrument') and model.instrument:
            try:
                model.instrument.query(command)
            except Exception as e:
                self.device_view.append_output(f"Error: {str(e)}", "error")
        else:
            self.device_view.append_output("No instrument connected", "error")
        self.cmd_entry.clear()
    
    def _update_control_states(self, enabled: bool):
        self.mode_combo.setEnabled(enabled)
        self.toolbar.get_button("Acquire").setEnabled(enabled)
        self.toolbar.get_button("Stop").setEnabled(False)  # Always start disabled
        self.toolbar.get_button("Reset (*RST)").setEnabled(enabled)
        self.toolbar.get_button("Clear (*CLS)").setEnabled(enabled)
        self.toolbar.get_button("Save").setEnabled(enabled)
        self.toolbar.get_button("Preset").setEnabled(enabled)
        self.device_view.setEnabled(enabled)
    
    def _handle_connection_changed(self, connected: bool):
        self._update_control_states(connected)
    
    def _handle_error(self, error: str):
        self.state.set_error(error)
    
    def cleanup(self):
        try:
            model = self.state.get_model(self.model_id)
            if isinstance(model, Device):
                model.connection_changed.disconnect(self._handle_connection_changed)
                model.error_occurred.disconnect(self._handle_error)
        except Exception as e:
            logger.error(f"Cleanup error in DeviceTab: {e}")
        super().cleanup()
