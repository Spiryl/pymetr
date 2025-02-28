from typing import Optional, Callable, Any
from PySide6.QtWidgets import (
    QToolBar, QWidget, QToolButton, 
    QMenu, QWidgetAction, QFrame,
    QHBoxLayout, QLabel, QSizePolicy, QComboBox
)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, Signal


class ToolBarButton(QToolButton):
    """Enhanced toolbar button with better styling."""
    def __init__(self, icon=None, text="", parent=None):
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        if icon:
            self.setIcon(icon)
        self.setText(text)


class ToolBarSeparator(QFrame):
    """Vertical separator for toolbar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.VLine)


class TabToolbar(QToolBar):
    """Enhanced toolbar with modern styling and better widget handling."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFloatable(False)
        self.setMovable(False)
        self.setStyleSheet("""
            QToolBar {
                background: transparent;
                border: none;
                spacing: 8px;
                padding: 4px;
            }

            QToolButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 6px;
                color: #f5f5f5;
            }

            QToolButton:hover {
                background: rgba(255, 132, 0, 0.2);
            }

            QToolButton:pressed {
                background: #ff8400;
                color: #000000;
            }
        """)

    def addButton(self, text, icon=None, callback: Optional[Callable] = None):
        """Add a button with optional icon and callback."""
        button = ToolBarButton(icon, text, self)
        if callback:
            button.clicked.connect(callback)
        self.addWidget(button)
        return button

    def addToggleButton(self, text, icon=None, checked=False, callback: Optional[Callable] = None):
        """
        Add a toggle button with optional icon, initial state, and callback.
        """
        button = ToolBarButton(icon, text, self)
        button.setCheckable(True)
        button.setChecked(checked)
        if callback:
            button.toggled.connect(callback)
        self.addWidget(button)
        return button

    def addDropdown(self, text, icon=None):
        """Add a dropdown button."""
        button = ToolBarButton(icon, text, self)
        button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(button)
        button.setMenu(menu)
        self.addWidget(button)
        return menu

    def addWidget(self, widget):
        """Add a widget with proper styling."""
        action = QWidgetAction(self)
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(widget)
        action.setDefaultWidget(container)
        super().addAction(action)
        return action

    def addSeparator(self):
        """Add a vertical separator."""
        sep = ToolBarSeparator(self)
        self.addWidget(sep)
        return sep

    def addStretch(self):
        """Add a stretch to push items to the right."""
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(spacer)
        return spacer

    def addComboBox(self, label: str, items: list, callback: Optional[Callable] = None):
        """
        Add a combobox with an accompanying label to the toolbar.
        
        Args:
            label (str): Label text for the combobox.
            items (list): List of items to populate the combobox.
            callback (Callable, optional): Function to call when the current text changes.
            
        Returns:
            QComboBox: The created combobox widget.
        """
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label_widget = QLabel(label)
        layout.addWidget(label_widget)
        combo = QComboBox()
        combo.addItems(items)
        if callback:
            combo.currentTextChanged.connect(callback)
        layout.addWidget(combo)
        self.addWidget(container)
        return combo
