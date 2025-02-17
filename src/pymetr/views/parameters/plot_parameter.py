from typing import Any
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QMenu
from PySide6.QtCore import Qt

from pyqtgraph.parametertree import Parameter
from .base import ModelParameter, ModelParameterItem
from pymetr.core.logging import logger
from pymetr.models.trace import Trace

class PlotStatusWidget(QWidget):
    """Widget showing plot info and trace count."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.info_label = QLabel()
        layout.addWidget(self.info_label)
        
    def update_info(self, trace_count: int):
        """Update plot info display."""
        self.info_label.setText(f"{trace_count} traces")

class PlotParameterItem(ModelParameterItem):
    """Tree item for plot parameters with trace count display."""
    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.hideWidget = False
        self.widget = None
        
    def makeWidget(self):
        self.widget = PlotStatusWidget()
        self.update_trace_count()
        return self.widget
        
    def update_trace_count(self):
        """Update the trace count display if widget exists."""
        if hasattr(self, 'widget') and self.widget and hasattr(self.param, 'state') and hasattr(self.param, 'model_id'):
            model = self.param.state.get_model(self.param.model_id)
            if model:
                trace_count = len([c for c in model.get_children() if isinstance(c, Trace)])
                self.widget.update_info(trace_count)
                
    def treeWidgetChanged(self):
        """Called when this item is added or removed from a tree."""
        super().treeWidgetChanged()
        if not hasattr(self, 'widget') or not self.widget:
            self.widget = self.makeWidget()
        tree = self.treeWidget()
        if tree is not None:
            tree.setItemWidget(self, 1, self.widget)

class PlotParameter(ModelParameter):
    """
    Parameter tree item for Plot models.
    
    Structure:
    - Plot Parameter
      └─ Settings (group)
         ├─ Basic Settings (direct parameters)
         ├─ Display (group)
         ├─ Axis (group)
         └─ Range (group)
    
    Key Implementation Pattern:
    1. Single "Settings" group containing all parameters
    2. Basic settings at top level of Settings group
    3. Other settings organized in subgroups
    4. Direct Parameter.create() usage with signal connections
    5. Direct value usage without wrapping
    """
    
    itemClass = PlotParameterItem
    
    def __init__(self, **opts):
        # Get model properties from opts
        model = None
        if opts.get('state') and opts.get('model_id'):
            model = opts['state'].get_model(opts['model_id'])

        opts['type'] = 'plot'
        super().__init__(**opts)
        
        # Create settings structure - basic settings at top level of Settings group
        settings_children = [
            # Basic settings directly in Settings group
            dict(name='title', type='str', value=model.get_property('title', '') if model else ''),
            dict(name='x_label', type='str', value=model.get_property('x_label', '') if model else ''),
            dict(name='y_label', type='str', value=model.get_property('y_label', '') if model else ''),
            dict(name='x_unit', type='str', value=model.get_property('x_unit', '') if model else ''),
            dict(name='y_unit', type='str', value=model.get_property('y_unit', '') if model else ''),
            
            # Display settings subgroup
            dict(
                name='Display',
                type='group',
                children=[
                    dict(name='grid_enabled', type='bool', value=model.get_property('grid_enabled', True) if model else True),
                    dict(name='legend_enabled', type='bool', value=model.get_property('legend_enabled', True) if model else True),
                    dict(name='roi_visible', type='bool', value=model.get_property('roi_visible', True) if model else True),
                    dict(
                        name='legend_position', 
                        type='list', 
                        value=model.get_property('legend_position', 'right') if model else 'right',
                        limits=['right', 'top', 'bottom', 'left']
                    )
                ]
            ),
            
            # Axis settings subgroup
            dict(
                name='Axis',
                type='group',
                children=[
                    dict(name='x_log', type='bool', value=model.get_property('x_log', False) if model else False),
                    dict(name='y_log', type='bool', value=model.get_property('y_log', False) if model else False),
                    dict(name='x_inverted', type='bool', value=model.get_property('x_inverted', False) if model else False),
                    dict(name='y_inverted', type='bool', value=model.get_property('y_inverted', False) if model else False)
                ]
            ),
            
            # Range settings subgroup
            dict(
                name='Range',
                type='group',
                children=[
                    dict(name='x_min', type='float', value=model.get_property('x_min', 0.0) if model else 0.0),
                    dict(name='x_max', type='float', value=model.get_property('x_max', 1.0) if model else 1.0),
                    dict(name='y_min', type='float', value=model.get_property('y_min', 0.0) if model else 0.0),
                    dict(name='y_max', type='float', value=model.get_property('y_max', 1.0) if model else 1.0),
                    dict(name='auto_range', type='bool', value=model.get_property('auto_range', True) if model else True),
                    dict(
                        name='roi', 
                        type='str',  # Change to str since we can't use list directly
                        value=str(model.get_property('roi', [0.0, 1.0])) if model else '[0.0, 1.0]'
                    )
                ]
            )
        ]
        
        # Create the Settings group and add all children
        settings = Parameter.create(name='Settings', type='group', children=settings_children)
        self.addChild(settings)
        
        # Connect signal handlers for all parameters recursively
        def connect_handlers(param):
            param.sigValueChanged.connect(self._handle_child_change)
            for child in param.children():
                connect_handlers(child)
                
        connect_handlers(settings)

    def _handle_child_change(self, param, value):
        """Handle child parameter changes by updating model."""
        if not self.state or not self.model_id:
            return
            
        model = self.state.get_model(self.model_id)
        if not model:
            return
            
        # Update model with value directly
        model.set_property(param.name(), value)
                    
    def handle_property_update(self, name: str, value: Any):
        """Handle model property updates by finding and updating the matching parameter."""
        settings = self.child('Settings')
        if not settings:
            return
            
        def update_param(group, name, value):
            for param in group.children():
                if param.name() == name:
                    # Special handling for ROI
                    if name == 'roi':
                        param.setValue(str(value))
                    else:
                        param.setValue(value)
                    return True
                if param.type() == 'group':
                    if update_param(param, name, value):
                        return True
            return False
            
        update_param(settings, name, value)