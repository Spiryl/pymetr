# views/tabs/device_tab.py
from pathlib import Path
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPlainTextEdit, 
    QLineEdit, QPushButton
)
from PySide6.QtGui import QIcon

from pymetr.models.device import AcquisitionMode, Device
from pymetr.models.trace import Trace  # For type checking
from .base import BaseTab
from ..widgets.group_view import GroupView
from ..widgets.toolbar import TabToolbar
from ..widgets.scpi_console import SCPIConsole
from pymetr.core.logging import logger

class DeviceTab(BaseTab):
    """
    Device tab with toolbar controls and SCPI console.
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

    def _handle_connection_changed(self, connected: bool):
        """Handle device connection state changes."""
        self._update_control_states(connected)

    def _handle_error(self, error: str):
        """Handle device errors."""
        self.state.set_error(error)

    def _get_icon(self, name: str) -> QIcon:
        """Get icon from resources."""
        icon_file = self.TOOLBAR_ICONS.get(name)
        if icon_file:
            icon_path = str(Path(__file__).parent.parent / 'icons' / icon_file)
            return QIcon(icon_path)
        return QIcon()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Setup enhanced toolbar
        self._setup_toolbar()
        
        # Main content uses group view
        self.content_view = GroupView(self.state, self.model_id, self)
        layout.addWidget(self.content_view)

        # Add SCPI console at bottom
        self.console = SCPIConsole(self.state, self.model_id, self)
        layout.addWidget(self.console)

    def _setup_toolbar(self):
        """Setup device-specific toolbar controls."""
        # Add connection controls
        self.toolbar.addButton("Connect", self._get_icon('connect'), 
                             self._handle_connect)
        self.toolbar.addButton("Disconnect", self._get_icon('disconnect'), 
                             self._handle_disconnect)
        self.toolbar.addSeparator()

        # Add acquisition controls
        self.mode_combo = self.toolbar.addComboBox(
            "Mode", 
            [mode.value for mode in AcquisitionMode],
            self._handle_mode_change
        )
        self.toolbar.addButton("Acquire", self._get_icon('acquire'), 
                             self._handle_acquire)
        self.toolbar.addButton("Stop", self._get_icon('stop'), 
                             self._handle_stop)
        self.toolbar.addSeparator()

        # Add IEEE 488.2 controls
        self.toolbar.addButton("Reset (*RST)", self._get_icon('reset'),
                             self._handle_reset)
        self.toolbar.addButton("Clear (*CLS)", self._get_icon('clear'),
                             self._handle_clear)
        self.toolbar.addButton("Save", self._get_icon('save'),
                             self._handle_save)
        self.toolbar.addButton("Preset", self._get_icon('preset'),
                             self._handle_preset)
        
    def _handle_connect(self):
        """Handle connect button."""
        try:
            model = self.state.get_model(self.model_id)
            if model:
                model.connect()
                self.toolbar.get_button("Connect").setEnabled(False)
                self.toolbar.get_button("Disconnect").setEnabled(True)
                # Enable other controls
                self._update_control_states(True)
        except Exception as e:
            self.state.set_error(str(e))

    def _handle_disconnect(self):
        """Handle disconnect button."""
        try:
            model = self.state.get_model(self.model_id)
            if model:
                model.disconnect()
                self.toolbar.get_button("Connect").setEnabled(True)
                self.toolbar.get_button("Disconnect").setEnabled(False)
                # Disable other controls
                self._update_control_states(False)
        except Exception as e:
            self.state.set_error(str(e))

    def _handle_mode_change(self, mode: str):
        """Handle acquisition mode change."""
        try:
            model = self.state.get_model(self.model_id)
            if model:
                model.set_property('acquisition_mode', mode)
                # Update button states based on mode
                is_continuous = mode in ['CONTINUOUS', 'AVERAGE']
                self.toolbar.get_button("Stop").setEnabled(is_continuous)
        except Exception as e:
            self.state.set_error(str(e))

    def _handle_acquire(self):
        """Handle acquire button."""
        try:
            model = self.state.get_model(self.model_id)
            if model:
                model.start_acquisition()
                # Update button states
                self.toolbar.get_button("Acquire").setEnabled(False)
                self.toolbar.get_button("Stop").setEnabled(True)
                self.mode_combo.setEnabled(False)
        except Exception as e:
            self.state.set_error(str(e))

    def _handle_stop(self):
        """Handle stop button."""
        try:
            model = self.state.get_model(self.model_id)
            if model:
                model.stop_acquisition()
                # Reset button states
                self.toolbar.get_button("Acquire").setEnabled(True)
                self.toolbar.get_button("Stop").setEnabled(False)
                self.mode_combo.setEnabled(True)
        except Exception as e:
            self.state.set_error(str(e))

    def _handle_reset(self):
        """Handle *RST command."""
        try:
            model = self.state.get_model(self.model_id)
            if model and model.instrument:
                model.instrument.reset()
                self.state.set_info("Instrument reset complete")
        except Exception as e:
            self.state.set_error(str(e))

    def _handle_clear(self):
        """Handle *CLS command."""
        try:
            model = self.state.get_model(self.model_id)
            if model and model.instrument:
                model.instrument.clear_status_registers()
                self.state.set_info("Status registers cleared")
        except Exception as e:
            self.state.set_error(str(e))

    def _handle_save(self):
        """Handle *SAV command."""
        try:
            model = self.state.get_model(self.model_id)
            if model and model.instrument:
                # Could add dialog for save location
                model.instrument.write("*SAV 1")
                self.state.set_info("Instrument state saved")
        except Exception as e:
            self.state.set_error(str(e))

    def _handle_preset(self):
        """Handle preset command."""
        try:
            model = self.state.get_model(self.model_id)
            if model and model.instrument:
                model.instrument.write("*RST;*CLS")
                self.state.set_info("Instrument preset complete")
        except Exception as e:
            self.state.set_error(str(e))

    def _update_control_states(self, enabled: bool):
        """Update enabled state of controls."""
        self.mode_combo.setEnabled(enabled)
        self.toolbar.get_button("Acquire").setEnabled(enabled)
        self.toolbar.get_button("Stop").setEnabled(False)  # Always start disabled
        self.toolbar.get_button("Reset").setEnabled(enabled)
        self.toolbar.get_button("Clear").setEnabled(enabled)
        self.toolbar.get_button("Save").setEnabled(enabled)
        self.toolbar.get_button("Preset").setEnabled(enabled)
        self.console.setEnabled(enabled)

    def cleanup(self):
        """Clean up resources."""
        try:
            model = self.state.get_model(self.model_id)
            if isinstance(model, Device):
                model.connection_changed.disconnect(self._handle_connection_changed)
                model.error_occurred.disconnect(self._handle_error)
        except:
            pass
        super().cleanup()