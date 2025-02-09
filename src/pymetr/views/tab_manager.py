from typing import Dict, Optional, Type
from PySide6.QtWidgets import QTabWidget, QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Slot

from pymetr.views.widgets.base import BaseWidget
from pymetr.models.test import TestScript, TestResult
from pymetr.core.logging import logger

class WelcomeTab(BaseWidget):
    """Welcome tab showing initial application state."""
    
    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "<h1>Welcome to PyMetr</h1>"
            "<p>Start by opening a script or connecting an instrument.</p>"
            "<p>Use the ribbon actions above to get started.</p>"
        ))

class TabManager(QTabWidget):
    """
    Manages content tabs and their relationship to models.
    Handles view creation and tab lifecycle.
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
        
        # Open welcome tab
        self.show_welcome()
        
    def show_welcome(self):
        """Show the welcome tab."""
        if 'welcome' not in self._tabs:
            welcome = WelcomeTab(self.state, self)
            self._tabs['welcome'] = welcome
            self.addTab(welcome, '🏠 Welcome')
        self.setCurrentWidget(self._tabs['welcome'])
        
    def _get_view_class(self, model) -> Optional[Type[BaseWidget]]:
        """Get appropriate view class for model type."""
        from pymetr.views.widgets.script_view import ScriptView
        from pymetr.views.widgets.result_view import ResultView
        from pymetr.views.widgets.plot_view import PlotView
        from pymetr.views.widgets.table_view import TableView
        
        model_type = type(model).__name__
        view_map = {
            'TestScript': ScriptView,
            'TestResult': ResultView,
            'Plot': PlotView,
            'DataTable': TableView
        }
        return view_map.get(model_type)
        
    def _create_view(self, model_id: str) -> Optional[BaseWidget]:
        """Create appropriate view for model."""
        model = self.state.get_model(model_id)
        if not model:
            return None
            
        view_class = self._get_view_class(model)
        if not view_class:
            logger.warning(f"No view class for model type: {type(model).__name__}")
            return None
            
        try:
            return view_class(self.state, model_id, self)
        except Exception as e:
            logger.error(f"Error creating view for {model_id}: {e}")
            return None

    def _get_tab_title(self, model_id: str) -> str:
        """Get display title for tab."""
        model = self.state.get_model(model_id)
        if model:
            return model.get_property('name', str(model_id))
        return str(model_id)
                
    def open_tab(self, model_id: str) -> None:
        """Open or switch to tab for model."""
        # Check if already open
        if model_id in self._tabs:
            self.setCurrentWidget(self._tabs[model_id])
            return True
            
        # Create new view
        view = self._create_view(model_id)
        if not view:
            return False
            
        # Add new tab with proper title
        self._tabs[model_id] = view
        title = self._get_tab_title(model_id)
        self.addTab(view, title)
        self.setCurrentWidget(view)
        logger.debug(f"TabManager: Opened new tab for {model_id} with title {title}")
        return True
        
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
            del self._tabs[model_id]
            
            # If last tab, show welcome
            if not self._tabs:
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
            
    def open_discovery(self):
        """Open the instrument discovery tab."""
        if 'discovery' in self._tabs:
            self.setCurrentWidget(self._tabs['discovery'])
            return
            
        from pymetr.views.widgets.discovery_view import DiscoveryView
        view = DiscoveryView(self.state, self)
        self._tabs['discovery'] = view
        self.addTab(view, '🔍 Discovery')
        self.setCurrentWidget(view)
        
    def get_current_view(self) -> Optional[BaseWidget]:
        """Get the currently active view."""
        widget = self.currentWidget()
        return widget if isinstance(widget, BaseWidget) else None