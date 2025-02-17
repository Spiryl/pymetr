from typing import Dict, Any, Optional
from pathlib import Path
from PySide6.QtWidgets import QHeaderView, QSizePolicy, QVBoxLayout, QAbstractItemView
from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtGui import QIcon
import pyqtgraph.parametertree as pt
from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.parametertree import registerParameterType

# Import parameter types
from ..parameters.trace_parameter import TraceParameter
from ..parameters.plot_parameter import PlotParameter
from ..parameters.marker_parameter import MarkerParameter
from ..parameters.cursor_parameter import CursorParameter
from ..parameters.data_table_parameter import DataTableParameter
from ..parameters.test_script_parameter import TestScriptParameter
from ..parameters.test_result_parameter import TestResultParameter
from ..parameters.base import ModelParameter

from ..widgets.base import BaseWidget
from pymetr.core.logging import logger

# Import model classes
from pymetr.models import (
    BaseModel,
    TestScript,
    TestResult,
    TestGroup,
    Plot,
    Trace,
    Cursor,
    Marker,
    DataTable,
    Measurement
)

class ModelTestView(BaseWidget):
    """
    Tree view for displaying and managing hierarchical model data.
    
    Displays models like TestScript, TestResult, Plot, etc. as interactive
    tree nodes with appropriate icons and custom parameter widgets.
    
    Key behaviors:
    - Shows model hierarchy with type-specific icons and controls
    - Synchronizes selection with active model/view
    - Provides context menus for model operations
    - Supports keyboard navigation
    """
    
    # Register custom parameter types
    registerParameterType('trace', TraceParameter)
    registerParameterType('plot', PlotParameter)
    registerParameterType('marker', MarkerParameter)
    registerParameterType('cursor', CursorParameter)
    registerParameterType('datatable', DataTableParameter)
    registerParameterType('testscript', TestScriptParameter)
    registerParameterType('testresult', TestResultParameter)
    
    selection_changed = Signal(str)  # Emits selected model_id
    
    # Define icons for different model types with filenames
    MODEL_ICONS = {
        'TestScript': 'script.png',        # Script icon 
        'TestResult': 'result.png',        # Result checkmark
        'TestGroup': 'folder.png',         # Folder icon
        'Plot': 'chart.png',               # Chart/plot icon
        'Trace': 'waves.png',              # Waveform icon
        'Cursor': 'cursor.png',            # Cursor crosshair
        'Marker': 'markers.png',           # Marker/pin icon
        'DataTable': 'table.png',          # Table grid icon
        'Measurement': 'measure.png',      # Measurement icon
        'Device': 'instruments.png',       # Device/instrument icon
        'default': 'file_open.png'         # Default file icon
    }

    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        
        # Set up layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create and configure tree
        self.tree = ParameterTree(self)
        self.tree.setAlternatingRowColors(False)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection) 


        # Configure header
        header = self.tree.header()
        header.setMinimumSectionSize(120)
        header.setDefaultSectionSize(150)
        header.setStretchLastSection(True)

        header.setVisible(False)  # Was true
        
        # Set size policies
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Create root parameter
        self.root = Parameter.create(name='Session', type='group', children=[])
        self.tree.setParameters(self.root, showTop=False)
        
        layout.addWidget(self.tree)
        
        # Track items and state
        self._items: Dict[str, Parameter] = {}
        self._updating_from_tab = False
        self._hide_passed = False
        
        # Connect signals
        self._connect_signals()
        
    def _connect_signals(self):
        """Connect to state and tree signals."""
        # Tree selection
        self.tree.itemSelectionChanged.connect(self._handle_selection_changed)
        
        # State signals
        self.state.model_registered.connect(self._handle_model_registered)
        self.state.models_linked.connect(self._handle_models_linked)
        self.state.model_changed.connect(self._handle_model_changed)
        self.state.model_removed.connect(self._handle_model_removed)

    def _get_icon(self, model_type: str) -> QIcon:
        """Get the appropriate icon for a model type."""
        icon_file = self.MODEL_ICONS.get(model_type, self.MODEL_ICONS['default'])
        icon_path = str(Path(__file__).parent.parent / 'icons' / icon_file)
        return QIcon(icon_path)

    def _create_parameter_for_model(self, model: BaseModel) -> Parameter:
        """Create appropriate parameter type for model."""
        model_type = type(model).__name__
        human_name = model.get_property('name', 'Unnamed')
        icon = self._get_icon(model_type)
        
        # For consistency, use model.id as the internal name and model_id,
        # and human_name as the title.
        param_opts = {
            'name': model.id,      # internal id
            'title': human_name,   # human readable
            'state': self.state,
            'model_id': model.id,
            'expanded': False,
            'removable': False,  # removal via context menu
            'renamable': False,   # renaming via context menu
            'icon': icon
        }
        
        if isinstance(model, TestScript):
            param_opts['expanded'] = True
            return TestScriptParameter(**param_opts)
        elif isinstance(model, TestResult):
            return TestResultParameter(**param_opts)
        elif isinstance(model, DataTable):
            return DataTableParameter(**param_opts)
        elif isinstance(model, Plot):
            return PlotParameter(**param_opts)
        elif isinstance(model, Trace):
            return TraceParameter(**param_opts)
        elif isinstance(model, Cursor):
            return CursorParameter(**param_opts)
        elif isinstance(model, Marker):
            return MarkerParameter(**param_opts)

        # For any other model type, create a group parameter and set its model_id
        param_opts['type'] = 'group'
        param_opts['name'] = model.id  # Store model_id in name
        return Parameter.create(**param_opts)

    def _create_parameter_change_handler(self, model_id: str):
        """Create handler for parameter value changes."""
        def handle_changes(param, changes):
            model = self.state.get_model(model_id)
            if not model:
                return
                
            for param, change, data in changes:
                if change == 'value':
                    prop_name = param.name()
                    if prop_name != 'name':  # Prevent "Unnamed" updates
                        if model.get_property(prop_name) != data:
                            logger.debug(f"Parameter change: {model_id}.{prop_name} = {data}")
                            model.set_property(prop_name, data)
                            
        return handle_changes

    def _find_viewable_parent(self, model_id: str) -> Optional[BaseModel]:
        """Find first parent that has a view."""
        parent = self.state.get_parent(model_id)
        while parent:
            # Add Marker and Cursor to this check
            if isinstance(parent, (Plot, TestScript, TestResult, TestGroup, Marker, Cursor)):
                return parent
            parent = self.state.get_parent(parent.id)
        return None

    def _find_param_item(self, tree_item, model_id):
        """Recursively find the tree item for a parameter by model_id."""
        try:
            if hasattr(tree_item, 'param'):
                param = tree_item.param
                
                # First check model_id attribute
                if hasattr(param, 'model_id') and param.model_id == model_id:
                    return tree_item
                    
                # Then check parameter name (for group parameters)
                if param.name() == model_id:
                    return tree_item

            # Recursively check children
            for i in range(tree_item.childCount()):
                child = tree_item.child(i)
                result = self._find_param_item(child, model_id)
                if result:
                    return result
                    
        except Exception as e:
            logger.error(f"Error finding parameter item: {e}")
            
        return None

    def _update_item_visibility(self, item: Parameter):
        """Update item visibility based on status."""
        if not isinstance(item, TestResultParameter):
            return
            
        should_hide = (
            self._hide_passed and 
            item.status() == 'Pass' and 
            not any(isinstance(child, TestResultParameter) for child in item.children())
        )
        
        if hasattr(item, 'setVisible'):
            item.setVisible(not should_hide)

    def _handle_selection_changed(self):
        """Handle tree selection changes."""
        if self._updating_from_tab:
            return

        selected = self.tree.selectedItems()
        if not selected or not selected[0].param:
            return

        try:
            self._updating_from_tab = True
            param = selected[0].param
            
            # Get model_id either from param attribute or param name
            model_id = None
            if hasattr(param, 'model_id'):
                model_id = param.model_id
            else:
                # For group/simple parameters, the name stores the model_id
                model_id = param.name()
                
            model = self.state.get_model(model_id)
            if not model:
                return

            # For non-viewable models or parameters, find closest parent with a view
            if not isinstance(model, (Plot, DataTable, TestScript, TestResult, TestGroup)):
                model = self._find_viewable_parent(model_id)
                if not model:
                    return

            # Show the view without affecting tree focus
            model.show()
            self.selection_changed.emit(model.id)
        finally:
            self._updating_from_tab = False

    @Slot(str)
    def _handle_model_registered(self, model_id: str):
        """Create appropriate parameter item for newly registered model."""
        logger.debug(f"ModelTestView: Registering model {model_id}")
        model = self.state.get_model(model_id)
        if not model:
            return
        
        try:
            # Create parameter
            param = self._create_parameter_for_model(model)
            if param:
                self._items[model_id] = param
                self.root.addChild(param)
                logger.debug(f"Added tree item for {model_id}")
                
                # Connect parameter change handler
                if isinstance(param, ModelParameter):
                    param.sigTreeStateChanged.connect(
                        self._create_parameter_change_handler(model_id)
                    )
                
                # Update visibility if it's a test result
                if isinstance(param, TestResultParameter):
                    self._update_item_visibility(param)
                    
        except Exception as e:
            logger.error(f"Error creating tree item for {model_id}: {e}")

    @Slot(str, str)
    def _handle_models_linked(self, parent_id: str, child_id: str):
        """Update tree structure when models are linked."""
        if parent_id in self._items and child_id in self._items:
            parent_param = self._items[parent_id]
            child_param = self._items[child_id]
            
            # Remove from current parent if any
            if child_param.parent():
                child_param.remove()
            
            # Add to new parent
            parent_param.addChild(child_param)
            logger.debug(f"Linked tree items {child_id} -> {parent_id}")

    def _handle_model_changed(self, model_id: str, prop: str, value: Any):
        """Handle model property changes."""
        if model_id not in self._items:
            logger.debug(f"Model {model_id} not found in items")
            return
                
        param = self._items[model_id]
        model = self.state.get_model(model_id)
        if not model:
            logger.debug(f"Could not get model for {model_id}")
            return
        
        try:
            # Handle test parameters
            if isinstance(param, (TestScriptParameter, TestResultParameter)):
                try:
                    if prop == 'status':
                        param.setStatus(value)
                        self._update_item_visibility(param)
                    elif prop == 'progress' and isinstance(param, TestScriptParameter):
                        param.setValue(value)
                except Exception as e:
                    logger.error(f"Error updating test parameter {model_id}.{prop}: {e}")
                return
            
            # Handle plot parameters            
            elif isinstance(param, PlotParameter):
                try:
                    param.handle_property_update(prop, value)
                    # Update trace count if needed
                    if param.items and param.items[0]:
                        param.items[0].update_trace_count()
                except Exception as e:
                    logger.error(f"Error updating plot parameter {model_id}.{prop}: {e}")
                return
            
            # Handle trace parameters
            elif isinstance(param, TraceParameter):
                try:
                    param.handle_property_update(prop, value)
                    # Update any dependent plots
                    parent_id = self.state.get_parent(model_id)
                    if parent_id in self._items:
                        parent_param = self._items[parent_id]
                        if isinstance(parent_param, PlotParameter) and parent_param.items:
                            parent_param.items[0].update_trace_count()
                except Exception as e:
                    logger.error(f"Error updating trace parameter {model_id}.{prop}: {e}")
                return
            
            # Handle marker parameters
            elif isinstance(param, MarkerParameter):
                try:
                    param.handle_property_update(prop, value)
                    # Update status widget if needed
                    if param.items and param.items[0]:
                        param.items[0].update_status()
                except Exception as e:
                    logger.error(f"Error updating marker parameter {model_id}.{prop}: {e}")
                return
            
            # Handle cursor parameters
            elif isinstance(param, CursorParameter):
                try:
                    param.handle_property_update(prop, value)
                    # Update status widget if needed
                    if param.items and param.items[0]:
                        param.items[0].update_status()
                except Exception as e:
                    logger.error(f"Error updating cursor parameter {model_id}.{prop}: {e}")
                return
            
            # Handle any other model parameters
            elif isinstance(param, ModelParameter):
                try:
                    for child in param.children():
                        if child.name() == prop:
                            child.setValue(value)
                            break
                except Exception as e:
                    logger.error(f"Error updating general parameter {model_id}.{prop}: {e}")
        
        except Exception as e:
            logger.error(f"Error updating parameter {model_id}.{prop}: {e}")
            logger.exception(e)  # Log full traceback for debugging

    def _handle_model_removed(self, model_id: str):
        """Clean up when a model is removed."""
        if model_id in self._items:
            param = self._items[model_id]
            
            # Recursively cleanup child parameters
            def cleanup_parameter(p):
                try:
                    # Clean up children first
                    for child in p.children():
                        cleanup_parameter(child)
                    
                    # Clean up the parameter's item if it exists
                    if hasattr(p, 'items') and p.items:
                        for item in p.items:
                            if hasattr(item, 'cleanup'):
                                item.cleanup()
                    
                except Exception as e:
                    logger.error(f"Error cleaning up parameter {p.name()}: {e}")
            
            try:
                # Clean up the parameter and its children
                cleanup_parameter(param)
                
                # Remove from tree
                param.remove()
                
                # Remove from storage
                del self._items[model_id]
                
                logger.debug(f"Removed tree item for {model_id}")
                
            except Exception as e:
                logger.error(f"Error removing tree item for {model_id}: {e}")
