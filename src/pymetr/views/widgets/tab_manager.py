# src/pymetr/views/widgets/tab_manager.py
from typing import Dict, Optional, Type, TYPE_CHECKING
from PySide6.QtWidgets import QTabWidget, QWidget, QLabel, QVBoxLayout
from ..manager import ViewType
from .discovery_view import DiscoveryView
from pymetr.logging import logger

if TYPE_CHECKING:
    from pymetr.state import ApplicationState

class TabManager(QTabWidget):
    """Manages content tabs based on model selection"""
    
    # Map model types to their default view types
    DEFAULT_VIEWS = {
        'TestScript': ViewType.SCRIPT,
        'TestResult': ViewType.RESULT,
        'Plot': ViewType.PLOT,
        'DataTable': ViewType.DATA_TABLE
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

        # Connect to "locating_instruments"
        self.state.signals.connect("locating_instruments", self._on_locating_instruments)

        # Open welcome tab initially
        self.open_welcome_tab()

    def open_welcome_tab(self):
        """Opens the welcome tab as an HTML-like view"""
        if "welcome" in self._tabs:
            self.setCurrentWidget(self._tabs["welcome"])
            return

        # Create a simple QWidget for now (HTML rendering can be added later)
        welcome_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h1>Welcome to PyMetr</h1><p>Start by selecting a test or data table.</p>"))
        welcome_widget.setLayout(layout)

        self._tabs["welcome"] = welcome_widget
        self.addTab(welcome_widget, "🏠 Welcome")
        self.setCurrentWidget(welcome_widget)

    def _on_locating_instruments(self):
        """
        Called as soon as state.find_instruments() is triggered.
        We open the Discovery tab if it's not already open.
        """
        self.open_discovery_tab()

    def open_discovery_tab(self):
        if "discovery" in self._tabs:
            self.setCurrentWidget(self._tabs["discovery"])
            return

        from .discovery_view import DiscoveryView
        view = DiscoveryView(self.state, self)
        idx = self.addTab(view, "Discovery")
        self._tabs["discovery"] = view
        self.setCurrentIndex(idx)

    def _handle_active_model(self, model_id: str, old_id: str) -> None:
        """Open or switch to tab for active model"""
        logger.debug(f"Active model changed: {model_id} (old: {old_id})")

        if not model_id:
            logger.warning("No active model ID received.")
            return

        if model_id in self._tabs:
            logger.info(f"Switching to existing tab for model: {model_id}")
            self.setCurrentWidget(self._tabs[model_id])
            return

        model = self.state.registry.get_model(model_id)
        if not model:
            logger.error(f"Model not found in registry: {model_id}")
            return

        view_type = self.DEFAULT_VIEWS.get(type(model).__name__, None)
        if not view_type:
            logger.warning(f"No default view type for model: {model_id} ({type(model).__name__})")
            return

        new_tab = self._create_view(model_id, view_type)
        if new_tab:
            name = getattr(model, 'name', None) or model.get_property('name', 'Unnamed')
            self._tabs[model_id] = new_tab
            self.addTab(new_tab, name)
            self.setCurrentWidget(new_tab)
            logger.info(f"Opened new tab for model: {model_id}")
        else:
            logger.error(f"Failed to create view for model: {model_id}")
    
    def _create_view(self, model_id: str, view_type: ViewType) -> Optional[QWidget]:
        logger.debug(f"Creating view for model {model_id} with type {view_type}")
        if view_type == ViewType.SCRIPT:
            from .script_view import ScriptView
            return ScriptView(self.state, model_id, self)
        elif view_type == ViewType.RESULT:
            from .result_view import ResultView
            return ResultView(self.state, model_id, self)
        elif view_type == ViewType.PLOT:
            from .plot_view import PlotView
            return PlotView(self.state, model_id, self)
        elif view_type == ViewType.DATA_TABLE:
            from .table_view import TableView
            return TableView(self.state, model_id, self)
        logger.error(f"No view created for model {model_id} with type {view_type}")
        return None
    
    def _handle_tab_close(self, index: int) -> None:
        """Handle tab close button"""
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