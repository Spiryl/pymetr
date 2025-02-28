from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PySide6.QtGui import QFont, QColor, QTextCursor
from pymetr.ui.views.base import BaseWidget

class DeviceView(BaseWidget):
    """Widget for displaying device output and status messages."""
    
    def __init__(self, state, model_id: str, parent=None):
        super().__init__(state, parent)
        self._model_id = model_id  # Store as instance variable instead of property
        self._setup_ui()
        self._connect_model_signals()  # Connect to the initial model
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        # Use a fixed-width font for clarity
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        self.output.setFont(font)
        
        layout.addWidget(self.output)
    
    def _connect_model_signals(self):
        """Connect to model signals."""
        model = self.state.get_model(self._model_id)
        if model:
            # Connect to property changes
            model.property_changed.connect(self._handle_property_change)
            
            # Initial connection check
            is_connected = model.get_property('is_connected', False)
            if is_connected and hasattr(model, 'instrument') and model.instrument:
                self._connect_instrument_signals(model)
    
    def _connect_instrument_signals(self, model):
        """Connect to instrument signals if available."""
        if not model or not hasattr(model, 'instrument') or not model.instrument:
            return
            
        # Connect to instrument signals if available
        try:
            instrument = model.instrument
            
            if hasattr(instrument, 'commandSent'):
                instrument.commandSent.connect(self._handle_command_sent)
            
            if hasattr(instrument, 'responseReceived'):
                instrument.responseReceived.connect(self._handle_response_received)
            
            if hasattr(instrument, 'exceptionOccured'):
                instrument.exceptionOccured.connect(self._handle_exception)
                
            self.append_output("Connected to instrument signals", "response")
        except Exception as e:
            self.append_output(f"Error connecting to signals: {e}", "error")
    
    def set_model(self, model_id: str):
        """Set the model and connect to its signals."""
        # Store the model ID
        self._model_id = model_id
        # Connect to the model signals
        self._connect_model_signals()
    
    def _handle_property_change(self, model_id: str, model_type: str, prop: str, value: object):
        """Handle property changes from the model."""
        if model_id != self._model_id:
            return
            
        # If connection state changed to connected, connect to instrument signals
        if prop == 'is_connected' and value is True:
            model = self.state.get_model(model_id)
            if model:
                self._connect_instrument_signals(model)
    
    def _handle_command_sent(self, command: str):
        """Handle command sent signal from instrument."""
        self.append_output(f"▶ {command}", "command")
    
    def _handle_response_received(self, command: str, response: str):
        """Handle response received signal from instrument."""
        self.append_output(f"◀ {response}", "response")
    
    def _handle_exception(self, error: str):
        """Handle exception signal from instrument."""
        self.append_output(f"⚠ {error}", "error")
    
    def append_output(self, text: str, style: str = "normal"):
        """Append text to the output area with styling."""
        # Default color: gray
        color = QColor("#CCCCCC")
        if style == "command":
            color = QColor("#ff8400")  # orange for commands
        elif style == "response":
            color = QColor("#4BFF36")  # green for responses
        elif style == "error":
            color = QColor("#FF9535")  # red for errors
            # colors = ["#02FEE4", "#4BFF36", "#FF9535", "#F23CA6", "#5E57FF"]
        self.output.setTextColor(color)
        self.output.append(text)
        self.output.moveCursor(QTextCursor.End)