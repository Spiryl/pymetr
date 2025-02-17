# trace_parameter.py
from typing import Any
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal

from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes.pen import PenPreviewLabel
from .base import ModelParameter, ModelParameterItem
import pyqtgraph.functions as fn

class TraceParameterItem(ModelParameterItem):
    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.hideWidget = False
        self.widget = None
        
        # Create the item widget with layout
        self.itemWidget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Visibility toggle
        self.visibilityBtn = QPushButton("👁️")
        self.visibilityBtn.setFixedSize(20, 20)
        self.visibilityBtn.setStyleSheet("""
            QPushButton { 
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 20);
            }
        """)
        self.visibilityBtn.clicked.connect(self._toggleVisibility)
        
        # Pen preview label
        self.penLabel = PenPreviewLabel(param)
        
        # Add widgets to layout
        layout.addWidget(self.visibilityBtn)
        layout.addWidget(self.penLabel)
        self.itemWidget.setLayout(layout)
        
        self._visible = True
        
    def treeWidgetChanged(self):
        """Called when this item is added or removed from a tree."""
        super().treeWidgetChanged()
        tree = self.treeWidget()
        if tree is not None:
            tree.setItemWidget(self, 1, self.itemWidget)
            
    def _toggleVisibility(self):
        self._visible = not self._visible
        self.visibilityBtn.setText("👁️" if self._visible else "⊘")
        if hasattr(self.param, '_visibilityChanged'):
            self.param._visibilityChanged(self._visible)

class TraceParameter(ModelParameter):
    """Parameter for trace properties with visibility toggle"""
    itemClass = TraceParameterItem

    def __init__(self, **opts):
        # Set basic parameter options
        opts.setdefault('type', 'trace')
        
        # Initialize ModelParameter
        super().__init__(**opts)
        
        # Get the model if available
        model = self.state.get_model(self.model_id) if self.state and self.model_id else None
        
        # Extract trace-specific options
        mode = model.get_property('mode', 'Group') if model else opts.get('mode', 'Group')
        color = model.get_property('color', '#ffffff') if model else opts.get('color', '#ffffff')
        style = model.get_property('style', 'solid') if model else opts.get('style', 'solid')
        width = model.get_property('width', 1) if model else opts.get('width', 1)
        
        # Convert style string to Qt pen style
        style_map = {
            'solid': Qt.SolidLine,
            'dash': Qt.DashLine,
            'dot': Qt.DotLine,
            'dash-dot': Qt.DashDotLine
        }
        qt_style = style_map.get(style, Qt.SolidLine)
        
        # Initialize the pen
        self.pen = fn.mkPen(color=color, width=width, style=qt_style)
        
        # Add child parameters
        children = [
            dict(
                name='mode',
                type='list',
                value=mode,
                limits=['Group', 'Isolate']
            ),
            dict(
                name='pen',
                type='pen',
                value=self.pen
            )
        ]
        
        # Add the children parameters
        for child in children:
            param = Parameter.create(**child)
            param.sigValueChanged.connect(self._handle_child_change)
            self.addChild(param)
            
    def _visibilityChanged(self, visible):
        """Handle visibility toggle from widget"""
        if self.state and self.model_id:
            model = self.state.get_model(self.model_id)
            if model:
                model.set_property('visible', visible)
                
    def _handle_child_change(self, param, value):
        """Handle child parameter changes"""
        if not self.state or not self.model_id:
            return
            
        model = self.state.get_model(self.model_id)
        if not model:
            return
            
        if param.name() == 'pen':
            # Update our stored pen
            self.pen = value
            
            # Extract pen properties and set them individually on the model
            model.set_property('color', value.color().name())
            model.set_property('width', value.width())
            
            # Map Qt pen style back to string
            style_map = {
                Qt.SolidLine: 'solid',
                Qt.DashLine: 'dash',
                Qt.DotLine: 'dot',
                Qt.DashDotLine: 'dash-dot'
            }
            model.set_property('style', style_map.get(value.style(), 'solid'))
        else:
            # For other properties, update directly
            model.set_property(param.name(), value)
                    
    def handle_property_update(self, name: str, value: Any):
        """Handle model property updates."""
        # Update the corresponding parameter if it exists
        for child in self.children():
            if child.name() == name:
                child.setValue(value)
                break