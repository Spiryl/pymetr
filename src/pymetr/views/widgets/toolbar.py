# views/widgets/toolbar.py
from typing import Optional, Callable, Any
from PySide6.QtWidgets import (
    QToolBar, QWidget, QToolButton, 
    QMenu, QWidgetAction, QFrame,
    QHBoxLayout, QLabel, QSizePolicy, 
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
        self.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                padding: 4px 8px;
                color: #D4D4D4;
            }
            QToolButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
            QToolButton:pressed {
                background: rgba(255, 255, 255, 0.2);
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)

class ToolBarSeparator(QFrame):
    """Vertical separator for toolbar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.VLine)
        self.setStyleSheet("""
            QFrame {
                color: #404040;
                margin-top: 4px;
                margin-bottom: 4px;
            }
        """)

class ModernToolBar(QToolBar):
    """Enhanced toolbar with modern styling and better widget handling."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QToolBar {
                background: #2D2D2D;
                border: none;
                border-bottom: 1px solid #1E1E1E;
                spacing: 2px;
                padding: 2px;
            }
        """)
        self.setFloatable(False)
        self.setMovable(False)

    def addButton(self, text, icon=None, callback=None):
        """Add a button with optional icon and callback."""
        button = ToolBarButton(icon, text, self)
        if callback:
            button.clicked.connect(callback)
        self.addWidget(button)
        return button

    def addDropdown(self, text, icon=None):
        """Add a dropdown button."""
        button = ToolBarButton(icon, text, self)
        button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(button)
        menu.setStyleSheet("""
            QMenu {
                background: #2D2D2D;
                border: 1px solid #404040;
                padding: 4px;
            }
            QMenu::item {
                padding: 4px 8px;
                color: #D4D4D4;
            }
            QMenu::item:selected {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        button.setMenu(menu)
        self.addWidget(button)
        return menu

    def addWidget(self, widget):
        """Add a widget with proper styling."""
        action = QWidgetAction(self)
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(2, 0, 2, 0)
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

