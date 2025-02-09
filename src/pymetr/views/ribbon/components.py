from PySide6.QtWidgets import (
    QWidget, QToolButton, QMenu, QLabel, 
    QHBoxLayout, QVBoxLayout, QFrame
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from pathlib import Path

from pymetr.core.actions import Action
from pymetr.core.logging import logger

class RibbonButton(QToolButton):
    """Enhanced tool button with improved styling."""
    
    def __init__(self, action: Action, handler, state, parent=None, large=False):
        super().__init__(parent)
        self.action = action
        self.state = state  # Store state reference
        
        # Setup appearance
        self.setText(action.name)
        icon_path = Path(__file__).parent.parent / "icons" / action.icon
        self.setIcon(QIcon(str(icon_path)))
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setAutoRaise(True)
        
        # Set size
        if large:
            self.setIconSize(QSize(32, 32))
            self.setFixedSize(64, 56)
        else:
            self.setIconSize(QSize(16, 16))
            self.setFixedSize(32, 28)
            
        # Setup menu if needed
        if action.menu_items:
            menu = QMenu(self)
            for item_id, menu_item in action.menu_items.items():
                item_icon = QIcon(str(Path(__file__).parent.parent / "icons" / menu_item.icon))
                item_action = menu.addAction(item_icon, menu_item.text)
                item_action.triggered.connect(
                    lambda checked, h=menu_item.handler: h(self.state)
                )
            self.setMenu(menu)
            self.setPopupMode(QToolButton.MenuButtonPopup)
        
        # Connect main action
        self.clicked.connect(lambda: handler(action.id))
        
        # Set tooltip
        if action.tooltip:
            self.setToolTip(action.tooltip)
            
        # Set enabled state
        self.setEnabled(action.enabled)
        
        # Apply styling
        self.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 4px;
                padding: 4px;
                color: #DDDDDD;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QToolButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QToolButton:disabled {
                color: #999999;
            }
        """)

class RibbonGroup(QWidget):
    """Group of related ribbon actions."""
    
    def __init__(self, name: str, state, parent=None):
        super().__init__(parent)
        self.name = name
        self.state = state
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Button container
        self.button_container = QWidget()
        self.button_layout = QHBoxLayout(self.button_container)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(4)
        layout.addWidget(self.button_container)
        
        # Group label
        label = QLabel(name)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        # Styling
        self.setStyleSheet("""
            RibbonGroup {
                background-color: transparent;
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                margin: 0px;
            }
            QLabel {
                color: #DDDDDD;
                font-size: 11px;
            }
        """)
        
    def add_button(self, action: Action, handler, large=True) -> RibbonButton:
        """Add an action button to the group."""
        button = RibbonButton(action, handler, self.state, self, large)
        self.button_layout.addWidget(button)
        return button

class RibbonBar(QWidget):
    """Container for ribbon groups."""
    
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        
        # Permanent section
        self.permanent = QWidget()
        self.permanent_layout = QHBoxLayout(self.permanent)
        self.permanent_layout.setContentsMargins(0, 0, 0, 0)
        self.permanent_layout.setSpacing(4)
        layout.addWidget(self.permanent)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("QFrame { color: rgba(255, 255, 255, 0.1); }")
        layout.addWidget(separator)
        
        # Context section
        self.context = QWidget()
        self.context_layout = QHBoxLayout(self.context)
        self.context_layout.setContentsMargins(0, 0, 0, 0)
        self.context_layout.setSpacing(4)
        layout.addWidget(self.context)
        
        layout.addStretch()
        
        # Styling
        self.setStyleSheet("""
            RibbonBar {
                background-color: #2D2D2D;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
    def add_permanent_group(self, name: str) -> RibbonGroup:
        """Add a permanent group to the ribbon."""
        group = RibbonGroup(name, self.state, self)
        self.permanent_layout.addWidget(group)
        return group
        
    def add_context_group(self, name: str) -> RibbonGroup:
        """Add a context-specific group to the ribbon."""
        group = RibbonGroup(name, self.state, self)
        self.context_layout.addWidget(group)
        return group
        
    def clear_context(self):
        """Remove all context-specific groups."""
        while self.context_layout.count():
            item = self.context_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()