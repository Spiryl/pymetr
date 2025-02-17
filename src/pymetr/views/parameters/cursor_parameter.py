from typing import Any
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QMenu

from pyqtgraph.parametertree import Parameter
from .base import ModelParameter, ModelParameterItem

class CursorStatusWidget(QWidget):
    """Widget showing cursor axis and position."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
    def update_status(self, axis: str, position: float):
        """Update cursor status display."""
        orientation = "Vertical" if axis == 'x' else "Horizontal"
        self.status_label.setText(f"{orientation} at {position:.3f}")

class CursorParameterItem(ModelParameterItem):
    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.hideWidget = False
        self.widget = None
        
    def makeWidget(self):
        self.widget = CursorStatusWidget()
        self.update_status()
        return self.widget
        
    def update_status(self):
        if hasattr(self, 'widget') and self.widget and hasattr(self.param, 'state') and hasattr(self.param, 'model_id'):
            model = self.param.state.get_model(self.param.model_id)
            if model:
                axis = model.get_property('axis', 'x')
                position = model.get_property('position', 0.0)
                self.widget.update_status(axis, position)
                
    def treeWidgetChanged(self):
        super().treeWidgetChanged()
        if not hasattr(self, 'widget') or not self.widget:
            self.widget = self.makeWidget()
        tree = self.treeWidget()
        if tree is not None:
            tree.setItemWidget(self, 1, self.widget)

class CursorParameter(ModelParameter):
    """
    Parameter tree item for Cursor models.
    
    Structure:
    - Cursor Parameter
      └─ Settings (group)
         ├─ Position Settings (direct parameters)
         ├─ Style (group)
         └─ Display (group)
    """
    
    itemClass = CursorParameterItem
    
    def __init__(self, **opts):
        model = None
        if opts.get('state') and opts.get('model_id'):
            model = opts['state'].get_model(opts['model_id'])

        opts['type'] = 'cursor'
        super().__init__(**opts)
        
        settings_children = [
            # Position settings at top level
            dict(name='axis', type='list', 
                 value=model.get_property('axis', 'x') if model else 'x',
                 limits=['x', 'y']),
            dict(name='position', type='float', 
                 value=model.get_property('position', 0.0) if model else 0.0),
                 
            # Style settings subgroup
            dict(
                name='Style',
                type='group',
                children=[
                    dict(name='color', type='color',
                         value=model.get_property('color', '#FFFF00') if model else '#FFFF00'),
                    dict(name='width', type='int',
                         value=model.get_property('width', 1) if model else 1,
                         limits=(1, 10)),
                    dict(name='style', type='list',
                         value=model.get_property('style', 'solid') if model else 'solid',
                         limits=['solid', 'dash', 'dot'])
                ]
            ),
            
            # Display settings subgroup
            dict(
                name='Display',
                type='group',
                children=[
                    dict(name='visible', type='bool',
                         value=model.get_property('visible', True) if model else True)
                ]
            )
        ]
        
        # Create settings group and add children
        settings = Parameter.create(name='Settings', type='group', children=settings_children)
        self.addChild(settings)
        
        # Connect signal handlers recursively
        def connect_handlers(param):
            param.sigValueChanged.connect(self._handle_child_change)
            for child in param.children():
                connect_handlers(child)
                
        connect_handlers(settings)

    def _handle_child_change(self, param, value):
        if not self.state or not self.model_id:
            return
            
        model = self.state.get_model(self.model_id)
        if not model:
            return
            
        model.set_property(param.name(), value)
                    
    def handle_property_update(self, name: str, value: Any):
        settings = self.child('Settings')
        if not settings:
            return
            
        def update_param(group, name, value):
            for param in group.children():
                if param.name() == name:
                    param.setValue(value)
                    return True
                if param.type() == 'group':
                    if update_param(param, name, value):
                        return True
            return False
            
        update_param(settings, name, value)

    def add_context_actions(self, menu: QMenu) -> None:
        """
        Abstract method to add parameter-specific context menu actions.
        Must be implemented by subclasses.
        
        Args:
            menu: QMenu to add actions to
        """
        pass