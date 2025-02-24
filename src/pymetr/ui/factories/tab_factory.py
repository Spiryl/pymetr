# src/pymetr/ui/factories/tab_factory.py
from typing import Optional, Dict, Type, Any

from PySide6.QtWidgets import QWidget, QDockWidget

from pymetr.ui.views.base import BaseWidget
from pymetr.ui.tabs.script_tab import ScriptTab
from pymetr.ui.tabs.result_tab import ResultTab
from pymetr.ui.tabs.plot_tab import PlotTab
from pymetr.ui.tabs.table_tab import TableTab
from pymetr.ui.tabs.welcome_tab import WelcomeTab
from pymetr.core.state import ApplicationState
from pymetr.core.logging import logger

class TabFactory:
    """
    Factory for creating tabs and content views based on model type.
    Centralizes view class resolution across the application.
    """
    
    # Registry mapping model types to view/tab classes
    _view_registry: Dict[str, Type[BaseWidget]] = {
        "TestScript": ScriptTab,
        "TestResult": ResultTab,
        "Plot": PlotTab,
        "DataTable": TableTab
    }
    
    @classmethod
    def register_view(cls, model_type: str, view_class: Type[BaseWidget]) -> None:
        """Register a view class for a model type."""
        cls._view_registry[model_type] = view_class
    
    @classmethod
    def create_view(cls, 
                  state: ApplicationState, 
                  model_id: str,
                  parent: Optional[QWidget] = None) -> Optional[BaseWidget]:
        """
        Create an appropriate view for a model.
        
        Args:
            state: Application state
            model_id: ID of the model
            parent: Parent widget
            
        Returns:
            A view instance or None if no view class is registered for the model type
        """
        if not state:
            logger.error("Cannot create view: state is None")
            return None
            
        # Get the model
        model = state.get_model(model_id)
        if not model:
            logger.error(f"Cannot create view: model {model_id} not found")
            return None
            
        # Get model type and find view class
        model_type = type(model).__name__
        view_class = cls._view_registry.get(model_type)
        
        if not view_class:
            logger.warning(f"No view class registered for model type: {model_type}")
            return None
            
        try:
            return view_class(state, model_id, parent)
        except Exception as e:
            logger.error(f"Error creating view for {model_id}: {e}")
            return None
    
    @classmethod
    def create_content_dock(cls,
                         state: ApplicationState,
                         model_id: str,
                         parent: QWidget) -> Optional[QDockWidget]:
        """
        Create a dock widget containing a view for the given model.
        
        Args:
            state: Application state
            model_id: ID of the model
            parent: Parent widget
            
        Returns:
            A dock widget or None if view creation failed
        """
        # Create the view
        view = cls.create_view(state, model_id, parent)
        if not view:
            return None
            
        # Get model name for dock title
        model = state.get_model(model_id)
        dock_title = model.get_property('name', str(model_id))
        
        # Create and return the dock
        dock = QDockWidget(dock_title, parent)
        dock.setWidget(view)
        
        return dock
    
    @classmethod
    def create_welcome(cls, state: ApplicationState, parent: QWidget) -> WelcomeTab:
        """Create a welcome tab/view."""
        return WelcomeTab(state, parent)