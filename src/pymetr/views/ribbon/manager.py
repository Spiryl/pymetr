# src/pymetr/views/ribbon/manager.py
from typing import Dict, Type, Optional
from PySide6.QtWidgets import QWidget, QToolBar, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from pymetr.state import ApplicationState
from .context import RibbonContext, DefaultContext, ScriptContext, PlotContext, ActionCategory

class RibbonManager(QWidget):
    """Manages the ribbon UI and context switching"""
    
    action_triggered = Signal(str)  # Emits action_id
    
    def __init__(self, state: 'ApplicationState', parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        
        # Setup UI
        self._setup_ui()
        
        # Track current context
        self._current_context: Optional[RibbonContext] = None
        
        # Map model types to context classes
        self._context_map: Dict[str, Type[RibbonContext]] = {
            'TestScript': ScriptContext,
            'Plot': PlotContext
        }
        
        # Connect to state signals
        self.state.signals.connect('active_model_changed', self._handle_active_model)
    
    def _setup_ui(self) -> None:
        """Setup ribbon UI layout"""
        self.setLayout(QVBoxLayout(self))
        
        # Title bar
        self.title_bar = QWidget(self)
        self.title_bar.setLayout(QHBoxLayout())
        self.title_label = QLabel(self.title_bar)
        self.title_bar.layout().addWidget(self.title_label)
        self.layout().addWidget(self.title_bar)
        
        # Create toolbars for each category
        self.toolbars: Dict[ActionCategory, QToolBar] = {}
        for category in ActionCategory:
            toolbar = QToolBar(self)
            self.toolbars[category] = toolbar
            self.layout().addWidget(toolbar)
    
    def _handle_active_model(self, model_id: str, old_model_id: str) -> None:
        """Update ribbon context based on active model"""
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
    
    def _set_context(self, context: RibbonContext) -> None:
        """Switch to new ribbon context"""
        self._current_context = context
        
        # Update title
        self.title_label.setText(context.get_title())
        
        # Clear existing actions
        for toolbar in self.toolbars.values():
            toolbar.clear()
        
        # Add new actions
        for action in context.get_actions():
            toolbar = self.toolbars[action.category]
            qaction = QAction(action.icon, action.name, toolbar)
            qaction.setToolTip(action.tooltip)
            qaction.setEnabled(action.enabled)
            qaction.setCheckable(action.checkable)
            qaction.setChecked(action.checked)
            
            # Connect action
            qaction.triggered.connect(
                lambda checked, aid=action.id: self._handle_action(aid)
            )
            
            toolbar.addAction(qaction)
    
    def _handle_action(self, action_id: str) -> None:
        """Handle ribbon action triggered"""
        if self._current_context and self._current_context.can_execute(action_id):
            self.action_triggered.emit(action_id)