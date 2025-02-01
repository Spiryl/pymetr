# src/pymetr/views/widgets/tab_manager.py
from typing import Dict, Optional, Type
from PySide6.QtWidgets import QTabWidget, QWidget
from ..manager import ViewType

class TabManager(QTabWidget):
    """Manages content tabs based on model selection"""
    
    # Map model types to their default view types
    DEFAULT_VIEWS = {
        'TestScript': ViewType.SCRIPT,
        'TestResult': ViewType.RESULT,
        'Plot': ViewType.PLOT,
        'Instrument': ViewType.INSTRUMENT
    }
    
    def __init__(self, state: 'ApplicationState', parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self.setTabsClosable(True)
        
        # Track open tabs by model_id
        self._tabs: Dict[str, QWidget] = {}
        
        # Connect to tab close button
        self.tabCloseRequested.connect(self._handle_tab_close)
        
        # Connect to state signals
        self.state.signals.connect('active_model_changed', self._handle_active_model)
        self.state.signals.connect('model_deleted', self._handle_model_deleted)
        
    def _handle_active_model(self, model_id: str, old_model_id: str) -> None:
        """Handle active model changes from tree selection"""
        if not model_id:
            return
            
        # Check if tab already exists
        if model_id in self._tabs:
            # Switch to existing tab
            tab_index = self.indexOf(self._tabs[model_id])
            self.setCurrentIndex(tab_index)
            return
            
        # Create new tab for model
        model = self.state.registry.get_model(model_id)
        if not model:
            return
            
        # Get default view type for model
        model_type = type(model).__name__
        view_type = self.DEFAULT_VIEWS.get(model_type)
        if not view_type:
            return
            
        # Create appropriate view
        view = self._create_view(model_id, view_type)
        if view:
            # Add new tab
            tab_name = f"{model.get_property('name', 'Unnamed')} ({model_type})"
            self._tabs[model_id] = view
            self.addTab(view, tab_name)
            self.setCurrentWidget(view)
    
    def _create_view(self, model_id: str, view_type: ViewType) -> Optional[QWidget]:
        """Create appropriate view widget for model"""
        # This will be expanded as we add more view types
        if view_type == ViewType.SCRIPT:
            from .script_view import ScriptView
            return ScriptView(self.state, model_id, self)
        elif view_type == ViewType.RESULT:
            from .result_view import ResultView
            return ResultView(self.state, model_id, self)
        elif view_type == ViewType.PLOT:
            from .plot_view import PlotView
            return PlotView(self.state, model_id, self)
        return None
    
    def _handle_tab_close(self, index: int) -> None:
        """Handle tab close button clicked"""
        widget = self.widget(index)
        for model_id, tab in self._tabs.items():
            if tab == widget:
                self.removeTab(index)
                del self._tabs[model_id]
                break
    
    def _handle_model_deleted(self, model_id: str) -> None:
        """Handle model deletion"""
        if model_id in self._tabs:
            widget = self._tabs[model_id]
            index = self.indexOf(widget)
            if index >= 0:
                self.removeTab(index)
            del self._tabs[model_id]