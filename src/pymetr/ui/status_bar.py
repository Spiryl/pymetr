from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QStatusBar, QLabel, QHBoxLayout, QWidget, QProgressBar
from PySide6.QtGui import QColor

from pymetr.ui.components.color_picker import ColorPicker
from pymetr.services.theme_service import ThemeService
from pymetr.core.logging import logger

class StatusBar(QStatusBar):
    """
    Application status bar with theme controls, message display, and status indicators.
    
    Connects to ApplicationState signals to display:
    - Status messages
    - Progress updates
    - Error and warning messages
    - Theme controls
    """
    
    def __init__(self, state):
        super().__init__()
        self.state = state
        
        # Initialize theme service
        self.theme_service = ThemeService.get_instance()
        
        # Create sections
        self._setup_message_section()
        self._setup_progress_section()
        self._setup_theme_section()
        self._setup_status_section()
        self._setup_log_section()
        
        # Connect to state signals
        self._connect_state_signals()
        
        # Timer for temporary messages
        self._message_timer = QTimer(self)
        self._message_timer.setSingleShot(True)
        self._message_timer.timeout.connect(self._clear_message)
        
        # Connect to theme service
        self.theme_service.accent_color_changed.connect(self._on_accent_color_changed)
        self.theme_service.theme_changed.connect(self._on_theme_changed)
        
    def _setup_message_section(self):
        """Set up the message display section."""
        self.message_label = QLabel()
        self.message_label.setMinimumWidth(300)
        self.addWidget(self.message_label, 1)  # Stretch to take available space
        
    def _setup_progress_section(self):
        """Set up the progress bar section."""
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setMinimumWidth(150)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setVisible(False)  # Hidden by default
        
        self.addPermanentWidget(self.progress_bar)
        
    def _setup_theme_section(self):
        """Set up the theme control section."""
        # Get current theme from service
        current_theme = self.theme_service.get_current_theme()
        
        # Create color picker with theme toggle
        self.color_picker = ColorPicker(
            self.theme_service.get_accent_color(),
            current_theme,
            self
        )
        self.color_picker.colorChanged.connect(self._on_color_picker_changed)
        self.color_picker.themeChanged.connect(self._on_theme_picker_changed)
        
        # Add to status bar
        self.addPermanentWidget(self.color_picker)
        
    def _setup_status_section(self):
        """Set up the status indicators section."""
        # Create status indicators container
        self.status_widget = QWidget()
        status_layout = QHBoxLayout(self.status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(10)
        
        # Add status indicators
        # Example: Connection status
        self.connection_status = QLabel("Not Connected")
        status_layout.addWidget(self.connection_status)
        
        # Add widget to status bar
        self.addPermanentWidget(self.status_widget)
        
    def _connect_state_signals(self):
        """Connect to state signals."""
        # Connect to status signals
        self.state.status_info.connect(self._on_info_changed)
        self.state.status_warning.connect(self._on_warning_changed)
        self.state.status_error.connect(self._on_error_changed)
        self.state.status_changed.connect(self._on_status_changed)
        self.state.status_progress.connect(self._on_progress_changed)
        
        # Connect to instrument signals
        self.state.instrument_connected.connect(self._on_instrument_connected)
        
    def _on_info_changed(self, message):
        """Handle info message changes."""
        self._show_message(message, "info")
        
    def _on_warning_changed(self, message):
        """Handle warning message changes."""
        self._show_message(message, "warning")
        
    def _on_error_changed(self, message):
        """Handle error message changes."""
        self._show_message(message, "error")
        
    def _on_status_changed(self, message):
        """Handle general status message changes."""
        self._show_message(message, "status")
        
    def _on_progress_changed(self, percent, message):
        """Handle progress updates."""
        # Update progress bar
        self.progress_bar.setValue(int(percent))
        
        # Show progress bar if not visible
        if not self.progress_bar.isVisible() and percent > 0:
            self.progress_bar.setVisible(True)
            
        # Hide progress bar when complete
        if percent >= 100:
            QTimer.singleShot(1000, self._hide_progress_bar)
            
        # Show message if provided
        if message:
            self._show_message(message, "status")
    
    def _hide_progress_bar(self):
        """Hide the progress bar."""
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        
    def _on_instrument_connected(self, device_id):
        """Handle instrument connection."""
        device = self.state.get_model(device_id)
        if device:
            model = device.get_property('model')
            name = device.get_property('name') or model
            self.update_connection_status(True, name)
            
    def _show_message(self, message, level="info"):
        """
        Show a message with appropriate styling.
        
        Args:
            message: Message to display
            level: Message level (info, warning, error, status)
        """
        if not message:
            self._clear_message()
            return
            
        # Set style based on level
        if level == "warning":
            self.message_label.setStyleSheet("color: #FFC107;")  # Yellow
        elif level == "error":
            self.message_label.setStyleSheet("color: #F44336;")  # Red
        elif level == "info":
            accent_color = self.theme_service.get_accent_color().name()
            self.message_label.setStyleSheet(f"color: {accent_color};")
        else:
            self.message_label.setStyleSheet("")  # Default
            
        # Set message
        self.message_label.setText(message)
        
        # Start timer to clear message after delay (longer for errors)
        timeout = 8000 if level == "error" else 5000
        self._message_timer.start(timeout)
        
    def _clear_message(self):
        """Clear the current message."""
        self.message_label.setText("")
        self.message_label.setStyleSheet("")
        
    def update_connection_status(self, connected, device_name=None):
        """
        Update the connection status indicator.
        
        Args:
            connected: Whether connected to a device
            device_name: Name of the connected device
        """
        if connected and device_name:
            self.connection_status.setText(f"Connected: {device_name}")
            self.connection_status.setStyleSheet("color: #4CAF50;")  # Green
        else:
            self.connection_status.setText("Not Connected")
            self.connection_status.setStyleSheet("")
            
    def _on_color_picker_changed(self, color):
        """Handle color picker changes."""
        logger.debug(f"StatusBar: Color picker changed to {color.name()}")
        self.theme_service.set_accent_color(color)
        
    def _on_theme_picker_changed(self, theme):
        """Handle theme picker changes."""
        logger.debug(f"StatusBar: Theme changed to {theme}")
        self.theme_service.set_theme(theme)
        
    def _on_accent_color_changed(self, color):
        """Handle accent color changes from theme service."""
        # Update color picker if needed (to prevent loops)
        if self.color_picker.color() != color:
            self.color_picker.setColor(color)
            
    def _on_theme_changed(self, theme):
        """Handle theme changes from theme service."""
        # Update theme button if needed (to prevent loops)
        if self.color_picker.theme() != theme:
            self.color_picker.setTheme(theme)

    def _setup_log_section(self):
        """Set up the logging controls section."""
        from pymetr.ui.components.log_level_selector import LogLevelSelector
        from pymetr.core.logging import set_log_level
        
        # Create log level selector
        self.log_controls = LogLevelSelector(self)
        self.log_controls.levelChanged.connect(self._on_log_level_changed)
        self.log_controls.consoleToggled.connect(self._on_console_toggled)
        
        # Add to status bar
        self.addPermanentWidget(self.log_controls)

    def _on_log_level_changed(self, level):
        """Handle log level change."""
        # Update logger level
        from pymetr.core.logging import set_log_level
        set_log_level(level)
        
        # Update console dock if it exists
        if hasattr(self, '_console_dock') and self._console_dock:
            self._console_dock.set_log_level(level)
        
        # Update state or settings
        import logging
        level_name = logging.getLevelName(level)
        self.state.set_info(f"Log level set to {level_name}")

    def _on_console_toggled(self, visible):
        """Handle console visibility toggle."""
        if not hasattr(self, '_main_window'):
            # Find main window
            parent = self.parent()
            while parent and not hasattr(parent, 'addDockWidget'):
                parent = parent.parent()
            
            if parent:
                self._main_window = parent
            else:
                return
        
        # Create console dock if it doesn't exist
        if not hasattr(self, '_console_dock') or not self._console_dock:
            from pymetr.ui.docks.console_dock import ConsoleDock
            self._console_dock = ConsoleDock(self._main_window)
            self._main_window.addDockWidget(Qt.BottomDockWidgetArea, self._console_dock)
        
        # Toggle visibility
        self._console_dock.setVisible(visible)