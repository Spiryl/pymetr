from typing import Dict, Type, Optional, List
from PySide6.QtWidgets import (
    QWidget, QToolBar, QLabel, QHBoxLayout, QVBoxLayout,
    QToolButton, QMenu, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction, QIcon
from pathlib import Path

from pymetr.logging import logger
from pymetr.state import ApplicationState
from .context import RibbonContext, DefaultContext, ScriptContext, PlotContext, ActionCategory, DataTableContext


class RibbonToolButton(QToolButton):
    """Enhanced tool button with better styling and interaction."""
    def __init__(self, icon_path: str, text: str, parent=None, large=False):
        super().__init__(parent)
        
        # Set text and icon
        self.setText(text)
        self.setIcon(QIcon(str(icon_path)))
        
        # Configure appearance
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setAutoRaise(True)
        
        # Explicit sizes for consistent appearance
        if large:
            self.setIconSize(QSize(32, 32))
            self.setFixedSize(64, 56)
        else:
            self.setIconSize(QSize(16, 16))
            self.setFixedSize(32, 28)
        
        # Apply styling (customize the menu indicator if desired)
        self.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 4px;
                padding: 4px;
                color: #DDDDDD;
            }
            QToolButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
            QToolButton:pressed {
                background-color: rgba(0, 0, 0, 0.2);
            }
            QToolButton:disabled {
                color: #999999;
            }
            QToolButton[popupMode="MenuButtonPopup"] {
                padding-right: 16px;
            }
            QToolButton::menu-indicator {
                /* If you have a custom arrow icon, set it here.
                   Otherwise, adjust its position and padding. */
                subcontrol-position: right center;
                subcontrol-origin: padding;
            }
        """)


class RibbonGroup(QWidget):
    """A group of related ribbon actions."""
    
    action_triggered = Signal(str)  # Emits action_id
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.buttons: Dict[str, RibbonToolButton] = {}
        
        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(2)
        
        # Button container
        self.button_container = QWidget()
        self.button_layout = QHBoxLayout(self.button_container)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(4)
        self.layout.addWidget(self.button_container)
        
        # Group title
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label)
        
        # Style
        self.setStyleSheet("""
            RibbonGroup {
                background-color: transparent;
                border-right: 1px solid #CCCCCC;
                padding: 2px;
                margin: 0px;
            }
            QLabel {
                color: #DDDDDD;
                font-size: 11px;
            }
        """)

    def add_button(self, action_id: str, name: str, icon_path: Path, 
                  menu_items=None, large=False, enabled=True) -> RibbonToolButton:
        """Add a button to the group."""
        button = RibbonToolButton(icon_path, name, self, large)
        
        # Setup menu if provided
        if menu_items:
            menu = QMenu(button)
            for item_text, (item_icon, handler) in menu_items.items():
                # Use the group's parent icons_path to resolve the icon path
                action = menu.addAction(QIcon(str(self.parent().icons_path / item_icon)), item_text)
                if handler:
                    action.triggered.connect(handler)
            button.setMenu(menu)
            button.setPopupMode(QToolButton.MenuButtonPopup)
            # Connect clicked to default menu item
            if len(menu_items) > 0:
                first_item = list(menu_items.items())[0]
                button.clicked.connect(first_item[1][1])
        else:
            # For regular buttons, connect clicked to action_triggered
            button.clicked.connect(lambda: self.action_triggered.emit(action_id))
        
        button.setEnabled(enabled)
        self.buttons[action_id] = button
        self.button_layout.addWidget(button)
        return button


class RibbonManager(QWidget):
    """Manages the ribbon UI and context switching."""
    
    action_triggered = Signal(str)  # Emits action_id
    
    def __init__(self, state: ApplicationState, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self.icons_path = Path(__file__).parent / "icons"
        
        # Setup UI
        self._setup_ui()
        
        # Track current context
        self._current_context: Optional[RibbonContext] = None
        
        # Map model types to context classes
        self._context_map: Dict[str, Type[RibbonContext]] = {
            'TestScript': ScriptContext,
            'Plot': PlotContext,
            'DataTable': DataTableContext
        }
        
        # Connect to state signals
        self.state.signals.connect('active_model_changed', self._handle_active_model)
        
        # Set to default context initially
        self._set_context(DefaultContext(self.state))
    
    def _setup_ui(self) -> None:
        """Setup ribbon UI layout."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Main ribbon container
        ribbon_container = QWidget()
        ribbon_layout = QHBoxLayout(ribbon_container)
        ribbon_layout.setContentsMargins(4, 4, 4, 4)
        ribbon_layout.setSpacing(0)
        
        # Standard section (always visible)
        self.standard_section = QWidget()
        self.standard_layout = QHBoxLayout(self.standard_section)
        self.standard_layout.setContentsMargins(0, 0, 0, 0)
        self.standard_layout.setSpacing(4)
        ribbon_layout.addWidget(self.standard_section)
        
        # Create permanent File group
        self._setup_file_group()
        
        # Create permanent Instruments group
        self._setup_instruments_group()
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("QFrame { color: #CCCCCC; }")
        ribbon_layout.addWidget(separator)
        
        # Context section
        self.context_section = QWidget()
        self.context_layout = QHBoxLayout(self.context_section)
        self.context_layout.setContentsMargins(0, 0, 0, 0)
        self.context_layout.setSpacing(4)
        ribbon_layout.addWidget(self.context_section)
        
        ribbon_layout.addStretch()
        self.layout.addWidget(ribbon_container)

    def _setup_file_group(self):
        """Setup permanent File group."""
        logger.debug("Setting up file group in ribbon")
        file_group = RibbonGroup("File", self)
        
        # New button with menu
        new_menu_items = {
            "New Script": ("new_script.png", lambda: self._execute_action("new_script")),
            "New Suite": ("new_suite.png", lambda: self._execute_action("new_suite"))
        }
        file_group.add_button("new", "New", self.icons_path / "new.png", menu_items=new_menu_items, large=True)
        
        # Open button with menu
        open_menu_items = {
            "Open Script": ("open_script.png", lambda: self._execute_action("open_script")),
            "Open Suite": ("open_suite.png", lambda: self._execute_action("open_suite"))
        }
        file_group.add_button("open", "Open", self.icons_path / "open.png", menu_items=open_menu_items, large=True)
        
        file_group.action_triggered.connect(self._handle_action)
        self.standard_layout.addWidget(file_group)
        
    def _execute_action(self, action_id: str):
        """Helper to execute actions with logging"""
        logger.info(f"Ribbon requesting execution of action: {action_id}")
        result = self.state.actions.execute(action_id)
        if not result.success:
            logger.error(f"Action {action_id} failed: {result.error}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Action Failed",
                f"Failed to execute {action_id}: {result.error}"
            )
        else:
            logger.info(f"Action {action_id} completed successfully")
        
    def _setup_instruments_group(self):
        instruments_group = RibbonGroup("Instruments", self)
        
        # The ID must match your check or vice versa
        instruments_group.add_button(
            "discover", 
            "Connect", 
            self.icons_path / "instruments.png",
            large=True
        )

        # IMPORTANT: connect the group's signal to our handler
        instruments_group.action_triggered.connect(self._handle_action)

        self.standard_layout.addWidget(instruments_group)
    
    def _set_context(self, context: RibbonContext) -> None:
        """Switch to new ribbon context."""
        self._current_context = context
        
        # Clear existing context actions
        while self.context_layout.count():
            item = self.context_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add context-specific groups
        for action in context.get_actions():
            group = RibbonGroup(action.name, self)
            icon_path = self.icons_path / f"{action.id}.png"
            
            if not icon_path.exists():
                icon_path = self.icons_path / "default.png"
            
            button = group.add_button(
                action.id, 
                action.name,
                icon_path,
                menu_items=action.menu_items,
                large=True,
                enabled=action.enabled
            )
            
            group.action_triggered.connect(self._handle_action)
            self.context_layout.addWidget(group)
            
    def _handle_action(self, action_id: str) -> None:
        """Handle all ribbon actions by executing through action manager."""
        logger.info(f"Ribbon handling action: {action_id}")
        
        if action_id == "discover":
            logger.debug("Executing discover instruments directly")
            self.state.find_instruments()
        else:
            logger.debug(f"Executing {action_id} through action manager")
            self._execute_action(action_id)

    def _handle_active_model(self, model_id: str, old_id: str) -> None:
        """Update ribbon context based on active model."""
        if not model_id:
            self._set_context(DefaultContext(self.state))
            return
            
        model = self.state.registry.get_model(model_id)
        if not model:
            return
            
        # Get appropriate context for model type
        model_type = type(model).__name__
        context_class = self._context_map.get(model_type, DefaultContext)
        self._set_context(context_class(self.state))
