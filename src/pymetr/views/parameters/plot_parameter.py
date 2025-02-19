from pathlib import Path
from typing import Optional, Any
from PySide6.QtWidgets import QWidget, QHBoxLayout, QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QIcon, QFont

from pyqtgraph.parametertree import Parameter
from .base import ModelParameter, ModelParameterItem, ParameterWidget
from pymetr.core.logging import logger
from pymetr.models import Plot, Trace, Marker, Cursor

class ItemCountIcon(QWidget):
    """Custom widget showing an icon with a count."""
    def __init__(self, icon_path: str, color: str = "#dddddd", parent=None):
        super().__init__(parent)
        self._icon = QIcon(icon_path)
        self._color = QColor(color)
        self._count = 0
        self.setFixedSize(24, 24)
        
    def setCount(self, count: int):
        self._count = count
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw icon
        self._icon.paint(painter, 2, 2, 20, 20)
        
        if self._count > 0:
            # Draw count
            painter.setPen(self._color)
            painter.setFont(QFont("Arial", 8))
            painter.drawText(0, 0, 24, 24, Qt.AlignCenter, str(self._count))

class PlotInfoWidget(ParameterWidget):
    """
    Enhanced widget showing counts of traces, markers, and cursors.
    """
    def __init__(self, param, parent=None):
        super().__init__(param, parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Create icons with counts for each type
        icons_path = Path(__file__).parent.parent / 'icons'
        self.trace_icon = ItemCountIcon(str(icons_path / 'waves.png'))
        self.marker_icon = ItemCountIcon(str(icons_path / 'markers.png'))
        self.cursor_icon = ItemCountIcon(str(icons_path / 'cursor.png'))
        
        # Add to layout
        layout.addWidget(self.trace_icon)
        layout.addWidget(self.marker_icon)
        layout.addWidget(self.cursor_icon)
        
        # Add spacer
        layout.addStretch()
    
    def _process_pending_update(self):
        """Update item counts."""
        try:
            model = self.param.state.get_model(self.param.model_id)
            if not model:
                return
                
            children = self.param.state.get_children(model.id)
            
            # Count each type
            trace_count = sum(1 for c in children if isinstance(c, Trace))
            marker_count = sum(1 for c in children if isinstance(c, Marker))
            cursor_count = sum(1 for c in children if isinstance(c, Cursor))
            
            # Update icons
            self.trace_icon.setCount(trace_count)
            self.marker_icon.setCount(marker_count)
            self.cursor_icon.setCount(cursor_count)
            
        except Exception as e:
            logger.error(f"Error updating plot info: {e}")

class PlotParameterItem(ModelParameterItem):
    """Parameter item for plots."""
    
    def makeWidget(self) -> Optional[QWidget]:
        """Create the info widget."""
        try:
            self.widget = PlotInfoWidget(self.param)
            return self.widget
        except Exception as e:
            logger.error(f"Error creating plot widget: {e}")
            return None
    
    def updateWidget(self, **kwargs):
        """Update the widget with new values."""
        if self.widget:
            self.widget.queue_update(**kwargs)
    
    def addCustomContextActions(self, menu: QMenu):
        """Add plot-specific context actions."""
        # Add 'Auto Range' action if we have any traces
        if self.param.state:
            model = self.param.state.get_model(self.param.model_id)
            if model and any(isinstance(child, Trace) 
                           for child in self.param.state.get_children(model.id)):
                auto_range = menu.addAction("Auto Range")
                auto_range.triggered.connect(self._handle_auto_range)
    
    def _handle_auto_range(self):
        """Reset plot ranges based on trace data."""
        if self.param.state:
            model = self.param.state.get_model(self.param.model_id)
            if model:
                model.set_property('auto_range', True)

class PlotParameter(ModelParameter):
    """
    Restructured plot parameter with cleaner organization.
    """
    
    itemClass = PlotParameterItem
    
    def __init__(self, **opts):
        opts['type'] = 'plot'
        super().__init__(**opts)
        self.can_export = True
        
        model = self.state.get_model(self.model_id) if self.state and self.model_id else None
        self.setupParameters(model)
    
    def setupParameters(self, model: Optional[Plot]):
        """Set up plot configuration parameters with new structure."""
        def get_prop(name, default):
            return model.get_property(name, default) if model else default
        
        # Settings group (top level)
        settings_group = {
            'name': 'Settings',
            'type': 'group',
            'expanded': False,
            'children': [
                # Basic settings at this level
                dict(name='title', type='str', value=get_prop('title', '')),
                dict(name='x_label', type='str', value=get_prop('x_label', '')),
                dict(name='y_label', type='str', value=get_prop('y_label', '')),
                dict(name='x_unit', type='str', value=get_prop('x_unit', '')),
                dict(name='y_unit', type='str', value=get_prop('y_unit', '')),
                
                # Advanced settings groups
                {
                    'name': 'Display',
                    'type': 'group',
                    'expanded': False,
                    'children': [
                        dict(name='grid_enabled', type='bool', 
                             value=get_prop('grid_enabled', True)),
                        dict(name='legend_enabled', type='bool', 
                             value=get_prop('legend_enabled', True)),
                        dict(name='legend_position', type='list', 
                             value=get_prop('legend_position', 'right'),
                             limits=['right', 'top', 'bottom', 'left'])
                    ]
                },
                {
                    'name': 'Axis',
                    'type': 'group',
                    'expanded': False,
                    'children': [
                        dict(name='x_log', type='bool', 
                             value=get_prop('x_log', False)),
                        dict(name='y_log', type='bool', 
                             value=get_prop('y_log', False)),
                        dict(name='x_inverted', type='bool', 
                             value=get_prop('x_inverted', False)),
                        dict(name='y_inverted', type='bool', 
                             value=get_prop('y_inverted', False))
                    ]
                },
                {
                    'name': 'Range',
                    'type': 'group',
                    'expanded': False,
                    'children': [
                        dict(name='auto_range', type='bool', 
                             value=get_prop('auto_range', True)),
                        dict(name='x_min', type='float', 
                             value=get_prop('x_min', 0.0)),
                        dict(name='x_max', type='float', 
                             value=get_prop('x_max', 1.0)),
                        dict(name='y_min', type='float', 
                             value=get_prop('y_min', 0.0)),
                        dict(name='y_max', type='float', 
                             value=get_prop('y_max', 1.0))
                    ]
                }
            ]
        }
        
        # Add the settings group
        settings = Parameter.create(**settings_group)
        self.addChild(settings)
        
        # Connect change handlers (recursively for all children)
        def connect_param(param):
            if param.type() != 'group':
                param.sigValueChanged.connect(self._handle_parameter_change)
            for child in param.children():
                connect_param(child)
        
        connect_param(settings)
    
    def _handle_parameter_change(self, param, value):
        """Handle parameter changes."""
        try:
            # Special handling for auto_range
            if param.name() == 'auto_range' and value:
                self.begin_update()
                try:
                    for range_param in ['x_min', 'x_max', 'y_min', 'y_max']:
                        self.set_model_property(range_param, None)
                finally:
                    self.end_update()
            else:
                # Normal property update
                self.set_model_property(param.name(), value)
        except Exception as e:
            logger.error(f"Error handling parameter change: {e}")
    
    def handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        try:
            # Find and update matching parameter
            settings = self.child('Settings')
            if settings:
                def update_param(parent, name, val):
                    for child in parent.children():
                        if child.name() == name:
                            child.setValue(val)
                            return True
                        if child.type() == 'group':
                            if update_param(child, name, val):
                                return True
                    return False
                
                update_param(settings, prop, value)
            
            # Update widget for child count changes
            if hasattr(self, 'widget'):
                self.widget.queue_update()
                
        except Exception as e:
            logger.error(f"Error handling property update: {e}")