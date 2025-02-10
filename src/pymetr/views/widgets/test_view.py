from typing import Dict, Any
from PySide6.QtWidgets import QHeaderView, QSizePolicy, QVBoxLayout
from PySide6.QtCore import Signal, Slot

import pyqtgraph.parametertree as pt
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree import registerParameterType

from ..parameters.trace_parameter import TraceParameter
registerParameterType("trace", TraceParameter)

from ..parameters.test_script_parameter import TestScriptParameter
registerParameterType("testscript", TestScriptParameter)

from pymetr.views.widgets.base import BaseWidget
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
    A ParameterTree-based view that displays hierarchical models:
      - TestScript/TestResult/TestGroup
      - Plot/Trace
      - Cursor/Marker
      - DataTable
      - Measurement
    Each model is presented as a parameter node with properties that can be viewed/edited.
    """
    
    selection_changed = Signal(str)  # Emits the selected model_id
    
    MODEL_ICONS = {
        'TestScript': '🖋️',
        'TestResult': '🧪',
        'TestGroup': '📂',
        'Plot': '📈',
        'Trace': '🌊',
        'Cursor': '🔀',
        'Marker': '📍',
        'DataTable': '📋',
        'Measurement': '📊',
        'Device': '🔌',
        'default': '📄'
    }
    
    STATUS_ICONS = {
        "Pass": "✅",
        "Fail": "❌",
        "Error": "⚠️",
        "Running": "🔄",
        "Not Run": "⭕"
    }

    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        
        # Set up layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create ParameterTree
        self.tree = pt.ParameterTree(self)
        self.tree.setAlternatingRowColors(False)
        
        # Configure header
        header = self.tree.header()
        header.setMinimumSectionSize(120)
        header.setDefaultSectionSize(150)
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setVisible(True)
        
        # Set size policies
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Create a hidden root parameter
        self.root = Parameter.create(name='Session', type='group', children=[])
        self.tree.setParameters(self.root, showTop=False)
        
        layout.addWidget(self.tree)
        
        # Track items in a dict: {model_id -> Parameter item}
        self._items: Dict[str, Parameter] = {}
        
        # Connect to tree selection
        self.tree.itemSelectionChanged.connect(self._handle_selection_changed)
   
        # Connect to ApplicationState signals
        self.state.model_registered.connect(self._handle_model_registered)
        self.state.models_linked.connect(self._handle_models_linked)
        self.state.model_changed.connect(self._handle_model_changed)

    def _find_viewable_parent(self, model_id: str):
        """Find the first parent that has a view (Plot, TestScript, etc.)"""
        parent_model = self.state.get_parent(model_id)
        while parent_model:
            if isinstance(parent_model, (Plot, TestScript, TestResult, TestGroup)):
                return parent_model
            parent_model = self.state.get_parent(parent_model.id)
        return None

    def _handle_selection_changed(self):
        """When the user clicks a parameter item, update the active model."""
        selected = self.tree.selectedItems()
        if not selected or not selected[0].param:
            self.state.set_active_model(None)
            self.selection_changed.emit("")
            return
        
        param = selected[0].param
        # if not hasattr(param, 'model_id'):
        #     self.state.set_active_model(None)
        #     self.selection_changed.emit("")
        #     return
            
        # Get the model for this parameter
        model = self.state.get_model(param.model_id)
        if not model:
            return
            
        # If it's a viewable type, set it as active
        if isinstance(model, (Plot, TestScript, TestResult, TestGroup)):
            self.state.set_active_model(model.id)
            self.selection_changed.emit(model.id)
            return
            
        # If not, find a viewable parent
        parent_model = self._find_viewable_parent(model.id)
        if parent_model:
            self.state.set_active_model(parent_model.id)
            self.selection_changed.emit(parent_model.id)
        else:
            self.state.set_active_model(None)
            self.selection_changed.emit("")

    @Slot(str)
    def _handle_model_registered(self, model_id: str):
        """Handle new model registration -> create a Parameter item."""
        logger.debug(f"ModelTestView: Registering model {model_id}")
        model = self.state.get_model(model_id)
        if not model:
            return
        
        try:
            # Create appropriate parameter node based on model type
            if isinstance(model, TestScript):
                item = self._create_test_script_item(model)
            elif isinstance(model, TestResult):
                item = self._create_test_result_item(model)
            elif isinstance(model, TestGroup):
                item = self._create_test_group_item(model)
            elif isinstance(model, Plot):
                item = self._create_plot_item(model)
            elif isinstance(model, Trace):
                item = self._create_trace_item(model)
            elif isinstance(model, Cursor):
                item = self._create_cursor_item(model)
            elif isinstance(model, Marker):
                item = self._create_marker_item(model)
            elif isinstance(model, DataTable):
                item = self._create_table_item(model)
            elif isinstance(model, Measurement):
                item = self._create_measurement_item(model)
            else:
                item = self._create_default_item(model)
            
            if item:
                self._items[model_id] = item
                self.root.addChild(item)
                logger.debug(f"Added tree item for {model_id}")
                
        except Exception as e:
            logger.error(f"Error creating tree item for {model_id}: {e}")

    @Slot(str, str)
    def _handle_models_linked(self, parent_id: str, child_id: str):
        """Handle model relationship changes in the tree structure."""
        if parent_id in self._items and child_id in self._items:
            parent_item = self._items[parent_id]
            child_item = self._items[child_id]
            
            # If the child already has a parent, remove it first
            if child_item.parent():
                child_item.remove()
            
            parent_item.addChild(child_item)
            logger.debug(f"Linked tree items {child_id} -> {parent_id}")

    def _create_parameter_change_handler(self, model_id: str):
        """Create a handler function for parameter changes."""
        def handle_param_change(param, changes):
            model = self.state.get_model(model_id)
            if not model:
                return
                
            for param, change, data in changes:
                if change == 'value':
                    try:
                        # Update the model property
                        prop_name = param.name()
                        if model.get_property(prop_name) != data:
                            logger.debug(f"Parameter change: {model_id}.{prop_name} = {data}")
                            model.set_property(prop_name, data)
                    except Exception as e:
                        logger.error(f"Error handling parameter change: {e}")
        
        return handle_param_change
    
    def _create_test_script_item(self, model: TestScript) -> Parameter:
        """Create a test script parameter with run/stop functionality."""
        icon = self.MODEL_ICONS.get('TestScript', '🖋️')
        name = model.get_property('name', 'Unnamed')
        progress = model.get_property('progress', 0)
        status = model.get_property('status', 'Not Run')
        
        param = TestScriptParameter(
            name=name,
            title=f"{icon} {name}",
            value=progress,
            status=status,
            state=self.state,  # Make sure this is passed
            model_id=model.id  # And this
        )
        
        # Connect parameter changes to model updates
        param.sigTreeStateChanged.connect(self._create_parameter_change_handler(model.id))
        return param

    def _create_test_result_item(self, model: TestResult) -> Parameter:
        """Create a test result parameter with status indicators."""
        icon = self.MODEL_ICONS.get('TestResult', '🧪')
        name = model.get_property('name', 'Unnamed')
        status = model.get_property('status', 'Not Run')
        status_icon = self.STATUS_ICONS.get(status, "⭕")
        
        children = []
        created_time = model.get_property('created_time', None)
        if created_time:
            children.append(dict(
                name='created',
                type='str',
                value=created_time.strftime('%H:%M:%S'),
                readonly=True
            ))
        
        param = Parameter.create(
            name=name,
            type='group',
            title=f"{icon} {name} [{status_icon}]",
            children=children
        )
        param.model_id = model.id
        return param

    def _create_test_group_item(self, model: TestGroup) -> Parameter:
        """Create a test group parameter."""
        icon = self.MODEL_ICONS.get('TestGroup', '📂')
        name = model.get_property('name', 'Unnamed')
        
        param = Parameter.create(
            name=name,
            type='group',
            title=f"{icon} {name}",
            children=[],
            expanded=True
        )
        param.model_id = model.id
        return param

    def _create_plot_item(self, model: Plot) -> Parameter:
        """Create a plot parameter with its properties."""
        icon = self.MODEL_ICONS.get('Plot', '📈')
        title = model.get_property('title', 'Untitled')
        
        param = Parameter.create(
            name=title,
            type='group',
            title=f"{icon} {title}",
            expanded=False,
            children=[
                dict(
                    name='grid_enabled',
                    type='bool',
                    value=model.get_property('grid_enabled', True)
                ),
                dict(
                    name='legend_enabled',
                    type='bool',
                    value=model.get_property('legend_enabled', True)
                ),
                dict(
                    name='x_label',
                    type='str',
                    value=model.get_property('x_label', '')
                ),
                dict(
                    name='y_label',
                    type='str',
                    value=model.get_property('y_label', '')
                ),
                dict(
                    name='x_unit',
                    type='str',
                    value=model.get_property('x_unit', '')
                ),
                dict(
                    name='y_unit',
                    type='str',
                    value=model.get_property('y_unit', '')
                )
            ]
        )
        param.model_id = model.id
        
        # Connect parameter changes to model updates
        param.sigTreeStateChanged.connect(self._create_parameter_change_handler(model.id))
        return param
    
    def _create_trace_item(self, model: Trace) -> Parameter:
        """Create a trace parameter with styling properties."""
        icon = self.MODEL_ICONS.get('Trace', '🌊')
        name = model.get_property('name', 'Trace')
        
        param = TraceParameter(
            name=name,
            title=f"{icon} {name}",
            expanded=False,
            state=self.state,
            model_id=model.id
        )
        
        # Connect parameter changes to model updates
        param.sigTreeStateChanged.connect(self._create_parameter_change_handler(model.id))
        return param

    def _create_cursor_item(self, model: Cursor) -> Parameter:
        """Create a cursor parameter."""
        icon = self.MODEL_ICONS.get('Cursor', '🔀')
        axis = model.get_property('axis', 'x')
        pos = model.get_property('position', 0.0)
        
        param = Parameter.create(
            name='Cursor',
            type='group',
            title=f"{icon} {axis.upper()}-Cursor @ {pos}",
            expanded=False,
            children=[
                dict(
                    name='axis',
                    type='list',
                    values=['x', 'y'],
                    value=axis
                ),
                dict(
                    name='position',
                    type='float',
                    value=pos,
                    step=0.1
                ),
                dict(
                    name='color',
                    type='color',
                    value=model.get_property('color', '#ffff00')
                ),
                dict(
                    name='style',
                    type='list',
                    values=['solid', 'dash', 'dot', 'dash-dot'],
                    value=model.get_property('style', 'solid')
                ),
                dict(
                    name='width',
                    type='int',
                    value=model.get_property('width', 1),
                    limits=(1, 10)
                ),
                dict(
                    name='visible',
                    type='bool',
                    value=model.get_property('visible', True)
                )
            ]
        )
        param.model_id = model.id
        param.sigTreeStateChanged.connect(self._create_parameter_change_handler(model.id))
        return param

    def _create_marker_item(self, model: Marker) -> Parameter:
        """Create a marker parameter."""
        icon = self.MODEL_ICONS.get('Marker', '📍')
        x = model.get_property('x', 0.0)
        y = model.get_property('y', 0.0)
        label = model.get_property('label', '')
        
        param = Parameter.create(
            name='Marker',
            type='group',
            title=f"{icon} {label or 'Marker'} ({x:.3f}, {y:.3f})",
            expanded=False,
            children=[
                dict(
                    name='x',
                    type='float',
                    value=x,
                    step=0.1
                ),
                dict(
                    name='y',
                    type='float',
                    value=y,
                    step=0.1
                ),
                dict(
                    name='label',
                    type='str',
                    value=label
                ),
                dict(
                    name='color',
                    type='color',
                    value=model.get_property('color', '#ffff00')
                ),
                dict(
                    name='size',
                    type='int',
                    value=model.get_property('size', 8),
                    limits=(1, 20)
                ),
                dict(
                    name='symbol',
                    type='list',
                    values=['o', 't', 's', 'd'],
                    value=model.get_property('symbol', 'o')
                ),
                dict(
                    name='visible',
                    type='bool',
                    value=model.get_property('visible', True)
                )
            ]
        )
        param.model_id = model.id
        param.sigTreeStateChanged.connect(self._create_parameter_change_handler(model.id))
        return param

    def _create_table_item(self, model: DataTable) -> Parameter:
        """Create a table parameter."""
        icon = self.MODEL_ICONS.get('DataTable', '📋')
        title = model.get_property('title', 'Untitled')
        
        children = [
            dict(
                name='columns',
                type='str',
                value=str(model.get_columns()),
                readonly=True
            ),
            dict(
                name='rows',
                type='str',
                value=str(len(model.get_data())),
                readonly=True
            )
        ]
        
        param = Parameter.create(
            name=title,
            type='group',
            title=f"{icon} {title}",
            children=children
        )
        param.model_id = model.id
        return param
    
    @Slot(str, str, object)
    def _handle_model_changed(self, model_id: str, prop: str, value: Any):
        """Handle model property changes."""
        if model_id not in self._items:
            return
            
        item = self._items[model_id]
        model = self.state.get_model(model_id)
        if not model:
            return
            
        try:
            # Handle special cases first
            if isinstance(model, TestScript):
                if prop == 'progress' and hasattr(item, 'setValue'):
                    item.setValue(float(value))
                elif prop == 'status' and hasattr(item, 'setOpts'):
                    item.setOpts(status=value)
                elif prop == 'name':
                    icon = self.MODEL_ICONS.get('TestScript', '📄')
                    item.setOpts(title=f"{icon} {value}")
            
            elif isinstance(model, TestResult):
                if prop == 'status' or prop == 'name':
                    icon = self.MODEL_ICONS.get('TestResult', '🧪')
                    status = model.get_property('status', 'Not Run')
                    name = model.get_property('name', 'Unnamed')
                    status_icon = self.STATUS_ICONS.get(status, "⭕")
                    item.setOpts(title=f"{icon} {name} [{status_icon}]")
            
            elif isinstance(model, Plot):
                if prop == 'title':
                    icon = self.MODEL_ICONS.get('Plot', '📈')
                    item.setOpts(title=f"{icon} {value}")
                    
            elif isinstance(model, Trace):
                if prop == 'name':
                    icon = self.MODEL_ICONS.get('Trace', '🌊')
                    item.setOpts(title=f"{icon} {value}")
            
            # Update parameter value if it exists
            for child in item.children():
                if child.name() == prop:
                    with item.treeChangeBlocker():
                        child.setValue(value)
                    break
                        
        except Exception as e:
            logger.error(f"Error handling model change: {e}")

    def cleanup_parameter(self, param):
        """Properly clean up a parameter and its children"""
        if hasattr(param, 'children'):
            for child in param.children():
                self.cleanup_parameter(child)
        if hasattr(param, 'widget') and param.widget:
            param.widget.deleteLater()
            param.widget = None

    def _handle_model_removed(self, model_id: str):
        """Handle model removal"""
        if model_id in self._items:
            param = self._items[model_id]
            self.cleanup_parameter(param)
            param.remove()
            del self._items[model_id]