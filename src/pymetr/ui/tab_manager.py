from typing import Dict, Optional
from PySide6.QtWidgets import QTabWidget, QWidget
from PySide6.QtCore import Slot

from pymetr.ui.views.base import BaseWidget
from pymetr.ui.factories.tab_factory import TabFactory
from pymetr.models.test import TestScript
from pymetr.core.logging import logger

class TabManager(QTabWidget):
    """
    Manages content tabs and their relationship to models.
    Handles tab creation, tab lifecycle, and synchronization with ApplicationState.
    """
    
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setTabsClosable(True)
        
        # Track open tabs
        self._tabs: Dict[str, BaseWidget] = {}
        
        # Connect signals
        self.tabCloseRequested.connect(self._handle_tab_close)
        self.currentChanged.connect(self._handle_current_changed)
        
        # Connect to state
        self.state.model_registered.connect(self._handle_model_registered)
        self.state.active_model_changed.connect(self._handle_active_model)
        self.state.model_changed.connect(self._handle_model_changed)
        self.state.model_removed.connect(self._handle_model_removed)
        
        # Open welcome tab
        self.show_welcome()
        
    def show_welcome(self):
        """Show the welcome tab."""
        if 'welcome' not in self._tabs:
            welcome = TabFactory.create_welcome(self.state, self)
            self._tabs['welcome'] = welcome
            self.addTab(welcome, '🏠 Welcome')
        self.setCurrentWidget(self._tabs['welcome'])
        
    def open_tab(self, model_id: str) -> bool:
        """Open or switch to tab for model."""
        # Check if already open
        if model_id in self._tabs:
            self.setCurrentWidget(self._tabs[model_id])
            return True
            
        # Create new view
        view = TabFactory.create_view(self.state, model_id, self)
        if not view:
            return False
            
        # Add new tab with proper title
        self._tabs[model_id] = view
        title = self._get_tab_title(model_id)
        index = self.addTab(view, title)
        self.setCurrentIndex(index)
        logger.debug(f"TabManager: Opened new tab for {model_id} with title {title}")
        return True
    
    def _get_tab_title(self, model_id: str) -> str:
        """Get display title for tab."""
        model = self.state.get_model(model_id)
        if model:
            # Try to get name from model
            name = model.get_property('name')
            if name:
                return name
                
            # If no name, try to get from parent (for plots in results)
            parent = self.state.get_parent(model_id)
            if parent:
                parent_name = parent.get_property('name')
                if parent_name:
                    return f"{parent_name} - {type(model).__name__}"
                    
        return str(model_id)
        
    @Slot(str)
    def _handle_model_registered(self, model_id: str):
        """Handle new model registration."""
        model = self.state.get_model(model_id)
        if isinstance(model, TestScript):
            # Auto-open scripts
            self.open_tab(model_id)
            
    @Slot(str)
    def _handle_active_model(self, model_id: str):
        """Handle active model changes."""
        if model_id:
            self.open_tab(model_id)
        else:
            self.show_welcome()
    
    @Slot(str)
    def _handle_model_removed(self, model_id: str):
        """Handle model removal."""
        if model_id in self._tabs:
            # Find tab index
            tab_idx = self.indexOf(self._tabs[model_id])
            if tab_idx >= 0:
                self.removeTab(tab_idx)
                
            # Clean up view if needed
            view = self._tabs.pop(model_id)
            if hasattr(view, 'cleanup'):
                view.cleanup()
                
            # Show welcome if no tabs remain
            if not self._tabs or len(self._tabs) == 1 and 'welcome' in self._tabs:
                self.show_welcome()

    @Slot(str, str, object)
    def _handle_model_changed(self, model_id: str, prop: str, value: object):
        """Handle model property changes."""
        if prop == 'name' and model_id in self._tabs:
            # Update tab title
            tab_idx = self.indexOf(self._tabs[model_id])
            if tab_idx >= 0:
                self.setTabText(tab_idx, value)
                logger.debug(f"TabManager: Updated tab title for {model_id} to {value}")

    @Slot(int)
    def _handle_tab_close(self, index: int):
        """Handle tab close button clicks."""
        widget = self.widget(index)
        model_id = None
        
        # Find model_id for widget
        for mid, tab in self._tabs.items():
            if tab == widget:
                model_id = mid
                break
                
        if model_id:
            # Remove tab
            self.removeTab(index)
            
            # Clean up view if needed
            view = self._tabs.pop(model_id, None)
            if view and hasattr(view, 'cleanup'):
                view.cleanup()
            
            # If last tab, show welcome
            if not self._tabs or (len(self._tabs) == 1 and 'welcome' in self._tabs):
                self.show_welcome()
                
    @Slot(int)
    def _handle_current_changed(self, index: int):
        """Handle tab selection changes."""
        widget = self.widget(index)
        
        # Find model_id for widget
        model_id = None
        for mid, tab in self._tabs.items():
            if tab == widget:
                model_id = mid
                break
                
        # Update active model
        if model_id and model_id != 'welcome':
            self.state.set_active_model(model_id)
            
    def get_current_view(self) -> Optional[BaseWidget]:
        """Get the currently active view."""
        widget = self.currentWidget()
        return widget if isinstance(widget, BaseWidget) else None
    
    def closeEvent(self, event):
        # Iterate through all open tabs and call cleanup if available.
        for widget in self._tabs.values():
            if hasattr(widget, 'cleanup'):
                widget.cleanup()
        self._tabs.clear()  # Clear the dictionary to release references.
        super().closeEvent(event)