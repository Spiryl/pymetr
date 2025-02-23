# views/widgets/scpi_console.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QPlainTextEdit
)
from PySide6.QtCore import Qt, QEvent
from pymetr.views.widgets.base import BaseWidget
from pymetr.core.logging import logger

class SCPIConsole(QWidget):
    """
    Interactive SCPI console showing instrument communication with command history.
    Provides real-time display of commands, responses, and errors.
    """
    def __init__(self, state, model_id, parent=None):
        super().__init__(parent)
        self.state = state
        self.model_id = model_id
        self.command_history = []
        self.history_index = 0
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Command input area
        input_layout = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter SCPI command...")
        self.command_input.returnPressed.connect(self._send_command)
        input_layout.addWidget(self.command_input)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self._send_command)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)

        # Console output
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(1000)  # Limit scrollback
        self.console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: "Consolas", monospace;
            }
        """)
        layout.addWidget(self.console)

    def _connect_signals(self):
        """Connect to instrument communication signals."""
        model = self.state.get_model(self.model_id)
        if model and model.instrument:
            model.instrument.commandSent.connect(self._handle_command)
            model.instrument.responseReceived.connect(self._handle_response)
            model.instrument.exceptionOccured.connect(self._handle_error)

    def _handle_command(self, command: str):
        """Log sent command."""
        self.console.appendHtml(
            f'<span style="color: #569CD6">&gt; {command}</span>'
        )

    def _handle_response(self, command: str, response: str):
        """Log command response."""
        self.console.appendHtml(
            f'<span style="color: #608B4E">&lt; {response}</span>'
        )

    def _handle_error(self, error: str):
        """Log communication error."""
        self.console.appendHtml(
            f'<span style="color: #F14C4C">! {error}</span>'
        )

    def eventFilter(self, obj, event):
        """Handle command history navigation."""
        if obj == self.command_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:
                self._history_previous()
                return True
            elif event.key() == Qt.Key_Down:
                self._history_next()
                return True
        return super().eventFilter(obj, event)

    def _history_previous(self):
        """Navigate command history backwards."""
        if not self.command_history:
            return
        if self.history_index > 0:
            self.history_index -= 1
            self.command_input.setText(self.command_history[self.history_index])

    def _history_next(self):
        """Navigate command history forwards."""
        if not self.command_history:
            return
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.command_input.setText(self.command_history[self.history_index])
        else:
            self.history_index = len(self.command_history)
            self.command_input.clear()

    def _send_command(self):
        command = self.command_input.text().strip()
        if not command:
            return

        try:
            # Add to history if unique
            if not self.command_history or command != self.command_history[-1]:
                self.command_history.append(command)
                if len(self.command_history) > 50:  # Limit history size
                    self.command_history.pop(0)
            self.history_index = len(self.command_history)

            model = self.state.get_model(self.model_id)
            if model and model.instrument:
                if command.endswith('?'):
                    response = model.instrument.query(command)
                else:
                    model.instrument.write(command)
            self.command_input.clear()

        except Exception as e:
            self._handle_error(str(e))