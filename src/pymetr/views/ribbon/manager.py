from typing import Dict, List, Type, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QToolButton
from PySide6.QtCore import Signal

from pymetr.core.actions import Action, ActionCategory, STANDARD_ACTIONS
from pymetr.views.ribbon.components import RibbonBar, RibbonGroup
from pymetr.core.logging import logger

class RibbonManager(QWidget):
    """
    Manages ribbon UI and context switching.
    Provides action handling and dynamic UI updates.
    """
    
    action_triggered = Signal(str)  # action_id
    
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create ribbon
        self.ribbon = RibbonBar(state, self)
        layout.addWidget(self.ribbon)
        
        # Setup permanent actions
        self._setup_permanent_actions()
        
        # Track current context
        self._current_context: Optional[str] = None
        
        # Connect to state
        self.state.active_model_changed.connect(self._handle_active_model)
        
        # Set default context
        self._set_context('default')
        
    def _setup_permanent_actions(self):
        """Setup permanent ribbon groups and actions."""
        # File group
        file_group = self.ribbon.add_permanent_group("File")
        file_group.add_button(
            STANDARD_ACTIONS['new_script'],
            self._handle_action
        )
        file_group.add_button(
            STANDARD_ACTIONS['open_script'],
            self._handle_action
        )
        file_group.add_button(
            STANDARD_ACTIONS['save_script'],
            self._handle_action
        )
        
        # Instrument group
        instrument_group = self.ribbon.add_permanent_group("Instruments")
        instrument_group.add_button(
            STANDARD_ACTIONS['discover_instruments'],
            self._handle_action
        )
        
    def _set_context(self, context_type: str):
        """Set the current ribbon context."""
        if context_type == self._current_context:
            return
            
        self._current_context = context_type
        self.ribbon.clear_context()
        
        if context_type == 'script':
            # Add script-specific actions
            run_group = self.ribbon.add_context_group("Run")
            run_group.add_button(
                STANDARD_ACTIONS['run_script'],
                self._handle_action
            )
            run_group.add_button(
                STANDARD_ACTIONS['stop_script'],
                self._handle_action
            )
            
        elif context_type == 'plot':
            # Add plot-specific actions
            plot_group = self.ribbon.add_context_group("Plot")
            # Add plot actions when we implement them
            
        elif context_type == 'data':
            # Add data table actions
            data_group = self.ribbon.add_context_group("Data")
            # Add data actions when we implement them
    
    def _handle_action(self, action_id: str):
        """Execute an action."""
        logger.debug(f"RibbonManager: Handling action {action_id}")
        
        action = STANDARD_ACTIONS.get(action_id)
        if not action:
            logger.error(f"RibbonManager: Unknown action: {action_id}")
            return
            
        try:
            logger.debug(f"RibbonManager: Found action {action.name}")
            # Check if action can be executed
            if not action.can_execute(self.state):
                logger.warning(f"RibbonManager: Action {action_id} cannot be executed in current state")
                return
                
            logger.debug(f"RibbonManager: Executing action {action_id}")
            # Execute the action
            action.handler(self.state)
            logger.info(f"RibbonManager: Action {action_id} executed successfully")
            
        except Exception as e:
            logger.error(f"Error executing action {action_id}: {e}")
            QMessageBox.warning(
                self,
                "Action Failed",
                f"Failed to execute {action.name}: {str(e)}"
            )
    
    def _handle_active_model(self, model_id: str):
        """Update ribbon context based on active model."""
        if not model_id:
            self._set_context('default')
            return
            
        # Get model type
        model = self.state.get_model(model_id)
        if not model:
            return
            
        # Map model types to contexts
        model_type = type(model).__name__
        context_map = {
            'TestScript': 'script',
            'Plot': 'plot',
            'DataTable': 'data'
        }
        
        self._set_context(context_map.get(model_type, 'default'))
        
    def update_action_state(self, action_id: str, enabled: bool = True):
        """Update an action's enabled state."""
        if action_id in STANDARD_ACTIONS:
            STANDARD_ACTIONS[action_id].enabled = enabled
            # Update button state if in current context
            self._refresh_action_states()
            
    def _refresh_action_states(self):
        """Refresh all visible action states."""
        for group in self.ribbon.findChildren(RibbonGroup):
            for button in group.findChildren(QToolButton):
                if hasattr(button, 'action'):
                    button.setEnabled(button.action.enabled)