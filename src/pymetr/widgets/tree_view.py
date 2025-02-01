# src/pymetr/views/widgets/tree_view.py
from typing import Dict, Optional, Any
from PySide6.QtWidgets import QWidget, QTreeWidget, QTreeWidgetItem
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal

class ModelTreeItem(QTreeWidgetItem):
    """Custom tree item that knows about its model"""
    def __init__(self, model_id: str, model_type: str, name: str, icon: str):
        super().__init__([f"{icon} {name}"])
        self.model_id = model_id
        self.model_type = model_type

class ModelTreeView(QTreeWidget):
    """Tree view for displaying model hierarchy"""
    
    # Custom signal for selection changes
    selection_changed = Signal(str)  # Emits model_id
    
    # Define icons/symbols for each model type
    MODEL_ICONS = {
        'TestScript': '📝',  # Script
        'TestResult': '📊',  # Result
        'Plot': '📈',       # Plot
        'Instrument': '🔧',  # Instrument
        'Measurement': '📏',  # Measurement
        'default': '📄'     # Default icon
    }
    
    def __init__(self, state: 'ApplicationState', parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self.view_id = f"tree_view_{id(self)}"
        
        # Configure tree widget
        self.setHeaderLabel("Models")
        self.setColumnCount(1)
        
        # Register this view
        self.state.views.register_view(
            self.view_id, 
            ViewType.TREE, 
            None  # Tree view doesn't have a single model
        )
        
        # Track items by model ID
        self._item_map: Dict[str, ModelTreeItem] = {}
        
        # Connect to state signals
        self.state.signals.connect('model_created', self._handle_model_created)
        self.state.signals.connect('model_deleted', self._handle_model_deleted)
        self.state.signals.connect('models_linked', self._handle_models_linked)
        self.state.signals.connect('models_unlinked', self._handle_models_unlinked)
        self.state.signals.connect('model_changed', self._handle_model_changed)
        
        # Connect tree selection to state
        self.itemSelectionChanged.connect(self._handle_selection_changed)
    
    def _create_item_for_model(self, model: 'BaseModel') -> ModelTreeItem:
        """Create a tree item for a model"""
        model_type = type(model).__name__
        icon = self.MODEL_ICONS.get(model_type, self.MODEL_ICONS['default'])
        name = model.get_property('name', 'Unnamed')
        
        return ModelTreeItem(
            model_id=model.id,
            model_type=model_type,
            name=name,
            icon=icon
        )
    
    def _handle_model_created(self, model_id: str, model_type: str) -> None:
        """Handle new model creation"""
        model = self.state.registry.get_model(model_id)
        if model:
            item = self._create_item_for_model(model)
            self._item_map[model_id] = item
            self.addTopLevelItem(item)
    
    def _handle_model_deleted(self, model_id: str) -> None:
        """Handle model deletion"""
        if model_id in self._item_map:
            item = self._item_map[model_id]
            parent = item.parent() or self.invisibleRootItem()
            parent.removeChild(item)
            del self._item_map[model_id]
    
    def _handle_models_linked(self, parent_id: str, child_id: str) -> None:
        """Handle model relationship creation"""
        if parent_id in self._item_map and child_id in self._item_map:
            parent_item = self._item_map[parent_id]
            child_item = self._item_map[child_id]
            
            # Remove from current parent
            current_parent = child_item.parent() or self.invisibleRootItem()
            current_parent.removeChild(child_item)
            
            # Add to new parent
            parent_item.addChild(child_item)
    
    def _handle_models_unlinked(self, parent_id: str, child_id: str) -> None:
        """Handle model relationship removal"""
        if child_id in self._item_map:
            child_item = self._item_map[child_id]
            if child_item.parent():
                child_item.parent().removeChild(child_item)
                self.addTopLevelItem(child_item)
    
    def _handle_model_changed(self, model_id: str, property_name: str, value: Any) -> None:
        """Handle model property changes"""
        if model_id in self._item_map and property_name == 'name':
            item = self._item_map[model_id]
            model = self.state.registry.get_model(model_id)
            if model:
                icon = self.MODEL_ICONS.get(type(model).__name__, self.MODEL_ICONS['default'])
                item.setText(0, f"{icon} {value}")
    
    def _handle_selection_changed(self) -> None:
        """Handle tree selection change"""
        selected_items = self.selectedItems()
        if selected_items:
            item = selected_items[0]
            if isinstance(item, ModelTreeItem):
                self.state.set_active_model(item.model_id)
                self.selection_changed.emit(item.model_id)
        else:
            self.state.set_active_model(None)
            self.selection_changed.emit("")