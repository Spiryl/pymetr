from pyqtgraph.parametertree import Parameter, ParameterItem
from PySide6.QtWidgets import QMenu, QInputDialog, QFileDialog
from pymetr.core.logging import logger
from PySide6.QtGui import QIcon
from pathlib import Path

# TODO: fix these. 
from pymetr.services.file_services import FileService

class ModelParameterItem(ParameterItem):
    """Base class for all model parameter items."""
    
    def __init__(self, param, depth):
        super().__init__(param, depth)
        
    def contextMenuEvent(self, ev):
        """Handle right-click context menu."""
        menu = QMenu()
        
        # Add parameter-specific actions
        self.add_context_menu_actions(menu)  # This is the item's own method
        self.param.add_context_actions(menu) # This is the parameter's method
        
        menu.addSeparator()
        
        # Add rename action with edit icon
        icons_path = Path(__file__).parent.parent / 'icons'
        rename_action = menu.addAction(
            QIcon(str(icons_path / 'edit.png')), 
            "Rename"
        )
        rename_action.triggered.connect(self._handle_rename)
        
        menu.addSeparator()
        
        # Add remove action with delete icon
        remove_action = menu.addAction(
            QIcon(str(icons_path / 'delete.png')), 
            "Remove"
        )
        remove_action.triggered.connect(self.param.remove_model)
        
        menu.exec_(ev.globalPos())
        
    def _handle_rename(self):
        """Handle rename action from context menu."""
        if not hasattr(self.param, 'state') or not hasattr(self.param, 'model_id'):
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

    def _handle_export(self):
        """Handle export action."""
        if not hasattr(self.param, 'state') or not hasattr(self.param, 'model_id'):
            return
            
        path, _ = QFileDialog.getSaveFileName(
            None, "Export Data", "", "YAML Files (*.yaml)"
        )
        if path:
            FileService.export_model_data(
                self.param.model_id,
                self.param.state,
                Path(path)
            )

    def add_context_menu_actions(self, menu):
        """Add item-specific menu actions. Override in subclasses."""
        pass

    def treeWidgetChanged(self):
        """Handle tree widget changes."""
        super().treeWidgetChanged()
        # Once this item is part of a tree, set its icon in column 0:
        icon = self.param.opts.get('icon', None)
        if icon is not None:
            self.setIcon(0, icon)
            
    def cleanup(self):
        """Clean up resources. Override in subclasses."""
        pass

class ModelParameter(Parameter):
    """Base class for all model parameters."""
    itemClass = ModelParameterItem
    
    def __init__(self, **opts):
        # Store state and model_id before parent class init
        self.state = opts.get('state', None)
        self.model_id = opts.get('model_id', None)
        
        # If this is a group parameter, store model_id in name
        if opts.get('type') == 'group' and self.model_id:
            opts['name'] = self.model_id
            
        super().__init__(**opts)
        
        if not self.state:
            logger.error(f"ModelParameter: No state provided for {self.__class__.__name__}")
            
    def remove_model(self):
        """Remove the model from the state."""
        if not hasattr(self, 'state') or not hasattr(self, 'model_id'):
            return
            
        model = self.state.get_model(self.model_id)
        if model:
            # First unlink from parent if any
            parent = self.state.get_parent(self.model_id)
            if parent:
                self.state.unlink_models(parent.id, self.model_id)
            # Then remove from state
            self.state.remove_model(self.model_id)

    def add_context_actions(self, menu: QMenu) -> None:
        """
        Abstract method to add parameter-specific context menu actions.
        Must be implemented by subclasses.
        
        Args:
            menu: QMenu to add actions to
        """
        raise NotImplementedError("Subclasses must implement add_context_actions")