from typing import Any
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

from .base import ModelParameter, ModelParameterItem
from pymetr.core.logging import logger

class CursorStatusWidget(QWidget):
    """Simple widget showing cursor axis and position."""
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
        self.status_label.setText(f"{axis}-cursor at {position:.3f}")

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
        if self.widget and self.param.state and self.param.model_id:
            model = self.param.state.get_model(self.param.model_id)
            if model:
                axis = model.get_property('axis', 'x')
                position = model.get_property('position', 0.0)
                self.widget.update_status(axis, position)
                
    def treeWidgetChanged(self):
        """Called when this item is added or removed from a tree."""
        super().treeWidgetChanged()
        if self.widget is None:
            self.widget = self.makeWidget()
        tree = self.treeWidget()
        if tree is not None:
            tree.setItemWidget(self, 1, self.widget)

class CursorParameter(ModelParameter):
    """Parameter tree item for Cursor models."""
    
    itemClass = CursorParameterItem
    
    def __init__(self, **opts):
        # Get model properties from opts
        model = None
        if opts.get('state') and opts.get('model_id'):
            model = opts['state'].get_model(opts['model_id'])

        opts['type'] = 'cursor'
        
        # Create parameter groups
        opts['children'] = [
            {
                'name': 'Position',
                'type': 'group',
                'children': [
                    {'name': 'axis', 'type': 'list', 
                     'value': model.get_property('axis', 'x') if model else 'x',
                     'limits': ['x', 'y']},
                    {'name': 'position', 'type': 'float', 
                     'value': model.get_property('position', 0.0) if model else 0.0}
                ]
            },
            {
                'name': 'Style',
                'type': 'group',
                'children': [
                    {'name': 'color', 'type': 'color',
                     'value': model.get_property('color', '#FFFF00') if model else '#FFFF00'},
                    {'name': 'width', 'type': 'int',
                     'value': model.get_property('width', 1) if model else 1,
                     'limits': (1, 10)},
                    {'name': 'style', 'type': 'list',
                     'value': model.get_property('style', 'solid') if model else 'solid',
                     'limits': ['solid', 'dash', 'dot']}
                ]
            },
            {
                'name': 'Display',
                'type': 'group',
                'children': [
                    {'name': 'visible', 'type': 'bool',
                     'value': model.get_property('visible', True) if model else True}
                ]
            }
        ]
        
        super().__init__(**opts)

    def handle_property_update(self, name: str, value: Any):
        """Handle model property updates."""
        for group in self.children():
            for param in group.children():
                if param.name() == name:
                    param.setValue(value)
                    # Update the status widget if position related properties change
                    if name in ['axis', 'position']:
                        if self.items and self.items[0]:
                            self.items[0].update_status()
                    return