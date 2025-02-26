import logging
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QComboBox, 
                               QLabel, QToolButton)
from PySide6.QtGui import QIcon

class LogLevelSelector(QWidget):
    """
    Widget for selecting log level and toggling console visibility.
    """
    levelChanged = Signal(int)  # Emits the new log level
    consoleToggled = Signal(bool)  # Emits when console visibility changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Add label
        self.label = QLabel("Log:")
        layout.addWidget(self.label)
        
        # Add log level selector
        self.level_combo = QComboBox()
        self.level_combo.addItem("DEBUG", logging.DEBUG)
        self.level_combo.addItem("INFO", logging.INFO)
        self.level_combo.addItem("WARNING", logging.WARNING)
        self.level_combo.addItem("ERROR", logging.ERROR)
        self.level_combo.setCurrentIndex(1)  # Default to INFO
        self.level_combo.setToolTip("Select logging level")
        self.level_combo.currentIndexChanged.connect(self._on_level_changed)
        layout.addWidget(self.level_combo)
        
        # Add console toggle button
        self.console_button = QToolButton()
        self.console_button.setText("🔍")  # Magnifying glass emoji
        self.console_button.setToolTip("Toggle console visibility")
        self.console_button.setCheckable(True)
        self.console_button.setChecked(False)
        self.console_button.clicked.connect(self._on_console_toggled)
        layout.addWidget(self.console_button)
        
        # Set layout
        self.setLayout(layout)
        
        # Emit initial level
        self.levelChanged.emit(logging.INFO)
    
    def _on_level_changed(self, index):
        """Handle log level change."""
        level = self.level_combo.currentData()
        self.levelChanged.emit(level)
    
    def _on_console_toggled(self, checked):
        """Handle console toggle."""
        self.consoleToggled.emit(checked)
        
    def set_level(self, level):
        """Set the current log level."""
        for i in range(self.level_combo.count()):
            if self.level_combo.itemData(i) == level:
                self.level_combo.setCurrentIndex(i)
                break
                
    def set_console_visible(self, visible):
        """Set console button state."""
        self.console_button.setChecked(visible)