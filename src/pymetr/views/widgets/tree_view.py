# src/pymetr/views/widgets/tree_view.py
from typing import Dict, Optional, Any, TYPE_CHECKING
from PySide6.QtWidgets import QWidget, QHeaderView, QSizePolicy
from PySide6.QtCore import Signal
import pyqtgraph.parametertree as pt
from pyqtgraph.parametertree import Parameter, registerParameterType

# Import the new test runner parameter so that its type is registered.
from pymetr.views.widgets.test_runner_parameter import TestRunnerParameter

if TYPE_CHECKING:
    from pymetr.state import ApplicationState
    from pymetr.models.base import BaseModel

from ..manager import ViewType
from pymetr.logging import logger

# --------------------------------------------------
# 1. (Removed old colored progress bar widget and parameter item)
#    We now use the TestRunnerParameter imported above.
# --------------------------------------------------

# --------------------------------------------------
# 2. Optionally, if you need a custom tree item for non-test types,
#    you can keep ModelTreeItem or similar logic.
# --------------------------------------------------
class ModelTreeItem(pt.Parameter):
    """Parameter tree item with model information."""
    def __init__(self, model_id: str, model_type: str, name: str, **kwargs):
        if model_type == 'TestScript':
            # For TestScript models, use the new testrunner parameter type.
            kwargs['type'] = 'testrunner'
            # Initialize progress (value) to 0 if not provided.
            kwargs.setdefault('value', 0)
            # Add status info to options.
            kwargs.setdefault('status', 'Not Run')
            # Optionally, add a status icon to the name.
            status_icons = {
                "Pass": "✅",
                "Fail": "❌",
                "Error": "⚠️",
                "Running": "⏳",
                "Not Run": "☢️"
            }
            name = f"{name} [{status_icons.get(kwargs['status'], '⏳')}]"
        else:
            kwargs['type'] = 'group'
        super().__init__(name=name, **kwargs)
        self.model_id = model_id
        self.model_type = model_type

# --------------------------------------------------
# 3. The updated ModelTreeView
# --------------------------------------------------
class ModelTreeView(pt.ParameterTree):
    """Tree view using PyQtGraph's ParameterTree."""
    
    selection_changed = Signal(str)  # Emits model_id
    
    MODEL_ICONS = {
        'TestScript': '🖋️',
        'TestResult': '🧪',
        'Plot': '📈',
        'DataTable': '🔬',
        'default': '📄'
    }
    
    def __init__(self, state: 'ApplicationState', parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self.view_id = f"tree_view_{id(self)}"
        
        logger.debug("Initializing ModelTreeView")
        
        # Create a root parameter for the tree.
        self.root = pt.Parameter.create(name='Test Tree Explorer', type='group', children=[])
        self.setParameters(self.root)
        
        # Configure the header so that:
        # - Column 0 (name) is interactive (draggable/resizable)
        # - Column 1 (value) will stretch to fill extra space.
        header = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setMinimumSectionSize(150)
        
        # Ensure the tree itself expands to fill its container.
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlternatingRowColors(False)
        
        self._item_map: Dict[str, pt.Parameter] = {}
        
        self.state.views.register_view(self.view_id, ViewType.TREE, None)
        
        self.state.signals.connect('model_created', self._handle_model_created)
        self.state.signals.connect('model_deleted', self._handle_model_deleted)
        self.state.signals.connect('models_linked', self._handle_models_linked)
        self.state.signals.connect('models_unlinked', self._handle_models_unlinked)
        self.state.signals.connect('model_changed', self._handle_model_changed)
        
        self.itemSelectionChanged.connect(self._handle_selection_changed)

    def _create_model_item(self, model: 'BaseModel') -> Parameter:
        model_type = type(model).__name__
        icon = self.MODEL_ICONS.get(model_type, self.MODEL_ICONS['default'])
        # Retrieve the display name from the model.
        display_name = getattr(model, 'name', model.get_property('name', 'Unnamed'))
        
        if model_type == 'TestScript':
            # Use the new custom "testrunner" parameter type.
            param_item = Parameter.create(
                name=model.id,                  # internal identifier: model ID
                title=f"{icon} {display_name}", # user-friendly display text
                type='testrunner',              # new custom parameter type
                value=getattr(model, 'progress', 0),
                status=getattr(model, 'status', 'Not Run')
            )
            # Hook up the run signal so that clicking the action button triggers a run.
            # This assumes that self.state.engine is your Engine instance.
            param_item.sigRunClicked.connect(
                lambda param: self.state.engine.run_test_script(param.name())
            )
        else:
            param_item = Parameter.create(
                name=model.id,                  # internal identifier
                title=f"{icon} {display_name}", # display string for the user
                type='group'
            )
        
        return param_item

    def _handle_model_created(self, model_id: str, model_type: str) -> None:
        """Handle new model creation."""
        model = self.state.registry.get_model(model_id)
        if model:
            item = self._create_model_item(model)
            self._item_map[model_id] = item
            self.root.addChild(item)
            logger.info(f"Model created: {model_id} ({model_type})")

    def _handle_model_changed(self, model_id: str, property_name: str, value: Any) -> None:
        if model_id in self._item_map:
            item = self._item_map[model_id]
            model = self.state.registry.get_model(model_id)
            logger.debug(f"_handle_model_changed: model_id: {model_id}, property: {property_name}, value: {value} (type: {type(value)})")
            
            if property_name == 'name':
                icon = self.MODEL_ICONS.get(type(model).__name__, self.MODEL_ICONS['default'])
                item.setName(f"{icon} {value}")
            
            elif property_name == 'progress' and type(model).__name__ == 'TestScript':
                try:
                    new_value = int(value)
                except Exception as e:
                    logger.error(f"Error converting progress value {value} to int: {e}")
                    new_value = 0
                item.setValue(new_value)
                logger.debug(f"Updated progress: {new_value}")
            
            elif property_name == 'status' and type(model).__name__ == 'TestScript':
                logger.debug(f"Updating status on item: setting to {value}")
                # If the parameter has a dedicated setStatus method (as in TestRunnerParameter), use it.
                if hasattr(item, 'setStatus'):
                    item.setStatus(value)
                else:
                    item.setOpts(status=value)
    
    def _handle_models_linked(self, parent_id: str, child_id: str) -> None:
        if parent_id in self._item_map and child_id in self._item_map:
            parent_item = self._item_map[parent_id]
            child_item = self._item_map[child_id]
            
            if child_item.parent():
                child_item.remove()
            parent_item.addChild(child_item)
            logger.info(f"Linked models: {parent_id} -> {child_id}")

    def _handle_selection_changed(self) -> None:
        selected = self.selectedItems()
        
        if not selected:
            self.state.set_active_model(None)
            self.selection_changed.emit("")
            return

        param_item = selected[0]
        param = param_item.param

        if param is None:
            self.state.set_active_model(None)
            self.selection_changed.emit("")
            return

        # Use param.name() to retrieve the model ID.
        model_id = param.name()
        self.state.set_active_model(model_id)
        self.selection_changed.emit(model_id)

    def _handle_model_deleted(self, model_id: str) -> None:
        if model_id in self._item_map:
            item = self._item_map[model_id]
            item.remove()
            del self._item_map[model_id]
            logger.info(f"Model deleted: {model_id}")
    
    def _handle_models_unlinked(self, parent_id: str, child_id: str) -> None:
        if child_id in self._item_map:
            child_item = self._item_map[child_id]
            if child_item.parent():
                child_item.remove()
                self.root.addChild(child_item)
                logger.info(f"Unlinked models: {parent_id} -> {child_id}")
