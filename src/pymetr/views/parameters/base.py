# base.py
from pyqtgraph.parametertree import Parameter, ParameterItem
from PySide6.QtWidgets import QMenu, QInputDialog
from PySide6.QtCore import Qt
from pymetr.core.logging import logger

class ModelParameterItem(ParameterItem):
    """Base class for all model parameter items"""
    def __init__(self, param, depth):
        super().__init__(param, depth)
        
    def contextMenuEvent(self, ev):
        """Handle right-click context menu"""
        menu = QMenu()
        
        # Add rename action
        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(self._handle_rename)
        
        menu.addSeparator()
        
        # Add remove action for all model parameters
        remove_action = menu.addAction("Remove")
        remove_action.triggered.connect(self.param.remove_model)
        
        # Let subclasses add their own menu items
        self.add_context_menu_actions(menu)
        
        menu.exec_(ev.globalPos())
        
    def _handle_rename(self):
        """Handle rename action from context menu"""
        if not self.param.state or not self.param.model_id:
            return
            
        model = self.param.state.get_model(self.param.model_id)
        if not model:
            return
            
        current_name = model.get_property('name', '')
        new_name, ok = QInputDialog.getText(
            None, 
            "Rename", 
            "Enter new name:",
            text=current_name
        )
        
        if ok and new_name:
            model.set_property('name', new_name)
        
    def add_context_menu_actions(self, menu):
        """Override in subclasses to add specific menu items"""
        pass

class ModelParameter(Parameter):
    """Base class for all model parameters"""
    itemClass = ModelParameterItem
    
    def __init__(self, **opts):
        # Store state and model_id before parent class init
        self.state = opts.get('state', None)
        self.model_id = opts.get('model_id', None)
        
        # Don't pop these from opts so they remain available to child classes
        super().__init__(**opts)
        
        if not self.state:
            logger.error(f"ModelParameter: No state provided for {self.__class__.__name__}")
            
    def remove_model(self):
        """Remove the model from the state"""
        if self.state and self.model_id:
            model = self.state.get_model(self.model_id)
            if model:
                # First unlink from parent if any
                parent = self.state.get_parent(self.model_id)
                if parent:
                    self.state.unlink_models(parent.id, self.model_id)
                # Then remove from state
                self.state.remove_model(self.model_id)