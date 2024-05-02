import logging
logger = logging.getLogger(__name__)

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QTextEdit, QTabWidget, QLineEdit, QCompleter, QGroupBox, QLabel)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence

class ConsoleControlPanel(QWidget):
    commandIssued = Signal(str, str)  # Signal to emit the command and instrument identifier
    queryIssued = Signal(str, str)  # Signal to emit the query and instrument identifier

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        # Create the main tab widget for each instrument's console
        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget)

        # Store command history
        self.command_history = []

    def add_instrument_tab(self, instrument_name):
        # Create a new tab for the instrument
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)

        # Output log for the instrument
        output_log = QTextEdit()
        output_log.setReadOnly(True)
        tab_layout.addWidget(output_log)

        # Command entry and send button
        command_layout = QHBoxLayout()
        command_entry = QLineEdit()
        send_button = QPushButton("Send Command")
        clear_log_button = QPushButton("Clear Log")
        command_layout.addWidget(command_entry)
        command_layout.addWidget(send_button)
        command_layout.addWidget(clear_log_button)
        tab_layout.addLayout(command_layout)

        # Setup command history and autocomplete
        self.setup_command_entry(command_entry)

        # Connect the send button
        send_button.clicked.connect(lambda: self.send_command(command_entry.text(), instrument_name, output_log))

        # Connect the clear log button
        clear_log_button.clicked.connect(lambda: output_log.clear())

        # Add tab to the widget
        self.tab_widget.addTab(tab, instrument_name)

    def setup_command_entry(self, command_entry):
        # Set up completer with the history
        completer = QCompleter(self.command_history)
        completer.setCompletionMode(QCompleter.InlineCompletion)
        command_entry.setCompleter(completer)

        # Connect history update
        command_entry.returnPressed.connect(lambda: self.update_command_history(command_entry.text(), command_entry))

    def update_command_history(self, command, command_entry):
        if command and command not in self.command_history:
            self.command_history.append(command)
            command_entry.completer().model().setStringList(self.command_history)

    def send_command(self, command, instrument_name, output_log):
        if command:  # Only send if command is not empty
            if command.endswith('?'):
                self.queryIssued.emit(instrument_name, command)  # Emit queryIssued signal for queries
            else:
                self.commandIssued.emit(instrument_name, command)  # Emit commandIssued signal for regular commands

    def display_response(self, instrument_id, response):
        logger.debug(f"Displaying response for instrument with ID: {instrument_id}")
        # Find the tab for the given instrument
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == instrument_id:
                logger.debug(f"Found tab for instrument with ID: {instrument_id}")
                # Find the output log widget within the tab
                tab = self.tab_widget.widget(i)
                output_log = tab.findChild(QTextEdit)
                if output_log:
                    output_log.append(response)
                    logger.debug(f"Response displayed for instrument with ID: {instrument_id}")
                break
        else:
            logger.debug(f"No tab found for instrument with ID: {instrument_id}")
            

    def remove_tab(self, index):
        # Remove tab by index
        if 0 <= index < self.tab_widget.count():
            self.tab_widget.removeTab(index)