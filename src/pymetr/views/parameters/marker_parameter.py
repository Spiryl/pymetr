from typing import Any
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

from .base import ModelParameter, ModelParameterItem
from pymetr.core.logging import logger

class MarkerStatusWidget(QWidget):
    """Simple widget showing marker position."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
    def update_status(self, x: float, y: float, label: str):
        """Update marker status display."""
        display_text = f"({x:.3f}, {y:.3f})"
        if label:
            display_text += f" - {label}"
        self.status_label.setText(display_text)

class MarkerParameterItem(ModelParameterItem):
    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.hideWidget = False
        self.widget = None
        
    def makeWidget(self):
        self.widget = MarkerStatusWidget()
        self.update_status()
        return self.widget
        
    def update_status(self):
        if self.widget and self.param.state and self.param.model_id:
            model = self.param.state.get_model(self.param.model_id)
            if model:
                x = model.get_property('x', 0.0)
                y = model.get_property('y', 0.0)
                label = model.get_property('label', '')
                self.widget.update_status(x, y, label)
                
    def treeWidgetChanged(self):
        """Called when this item is added or removed from a tree."""
        super().treeWidgetChanged()
        if self.widget is None:
            self.widget = self.makeWidget()
        tree = self.treeWidget()
        if tree is not None:
            tree.setItemWidget(self, 1, self.widget)

class MarkerParameter(ModelParameter):
    """Parameter tree item for Marker models."""
    
    itemClass = MarkerParameterItem
    
    def __init__(self, **opts):
        # Get model properties from opts
        model = None
        if opts.get('state') and opts.get('model_id'):
            model = opts['state'].get_model(opts['model_id'])

        opts['type'] = 'marker'
        
        # Create parameter groups
        opts['children'] = [
            {
                'name': 'Position',
                'type': 'group',
                'children': [
                    {'name': 'x', 'type': 'float',
                     'value': model.get_property('x', 0.0) if model else 0.0},
                    {'name': 'y', 'type': 'float',
                     'value': model.get_property('y', 0.0) if model else 0.0}
                ]
            },
            {
                'name': 'Label',
                'type': 'group',
                'children': [
                    {'name': 'label', 'type': 'str',
                     'value': model.get_property('label', '') if model else ''}
                ]
            },
            {
                'name': 'Style',
                'type': 'group',
                'children': [
                    {'name': 'color', 'type': 'color',
                     'value': model.get_property('color', '#FFFF00') if model else '#FFFF00'},
                    {'name': 'size', 'type': 'int',
                     'value': model.get_property('size', 8) if model else 8,
                     'limits': (1, 20)},
                    {'name': 'symbol', 'type': 'list',
                     'value': model.get_property('symbol', 'o') if model else 'o',
                     'limits': ['o', 't', 's', 'd']}  # circle, triangle, square, diamond
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
                    # Update the status widget if position/label properties change
                    if name in ['x', 'y', 'label']:
                        if self.items and self.items[0]:
                            self.items[0].update_status()
                    return