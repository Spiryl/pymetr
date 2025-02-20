from pathlib import Path
from typing import Optional, Any
from PySide6.QtWidgets import QWidget, QHBoxLayout, QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QIcon, QFont, QBrush, QPen

from pyqtgraph.parametertree import Parameter
from .base import ModelParameter, ModelParameterItem, ParameterWidget
from pymetr.core.logging import logger
from pymetr.models import Plot, Trace, Marker, Cursor

class ItemCountIcon(QWidget):
    """Custom widget showing an icon with a count badge in the top-right corner."""
    def __init__(self, icon_path: str, badge_color: str = "#FF8400", text_color: str = "#DDDDDD", parent=None):
        super().__init__(parent)
        self._icon = QIcon(icon_path)
        self._badge_color = QColor(badge_color)
        self._text_color = QColor(text_color)
        self._count = 0
        self.setFixedSize(24, 24)
        
    def setCount(self, count: int):
        self._count = count
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw the icon to cover the entire widget area.
        self._icon.paint(painter, 0, 0, self.width(), self.height())
        
        if self._count > 0:
            # Define badge size.
            badge_radius = 8
            # Position badge at top-right.
            badge_x = self.width() - badge_radius * 2
            badge_y = 0
            # Draw a circle for the badge background.
            painter.setBrush(QBrush(self._badge_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(badge_x, badge_y, badge_radius * 2, badge_radius * 2)
            
            # Draw the count number over the badge.
            painter.setPen(QPen(self._text_color))
            painter.setFont(QFont("Arial", 8, QFont.Bold))
            painter.drawText(badge_x, badge_y, badge_radius * 2, badge_radius * 2, 
                             Qt.AlignCenter, str(self._count))

class PlotInfoWidget(ParameterWidget):
    """
    Enhanced widget showing counts of traces, markers, and cursors.
    Updates efficiently and tracks changes properly.
    """
    def __init__(self, param, parent=None):
        super().__init__(param, parent)
        self._setup_ui()
        self._current_counts = {'traces': 0, 'markers': 0, 'cursors': 0}
        
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
        
        # Connect to model signals
        if self.param.state:
            self.param.state.models_linked.connect(self._handle_model_linked)
            self.param.state.model_removed.connect(self._handle_model_removed)
    
    def _process_pending_update(self):
        """Update item counts."""
        try:
            if not self.param.state or not self.param.model_id:
                return
                
            model = self.param.state.get_model(self.param.model_id)
            if not model:
                return
                
            children = self.param.state.get_children(model.id)
            
            # Count each type
            new_counts = {
                'traces': sum(1 for c in children if isinstance(c, Trace)),
                'markers': sum(1 for c in children if isinstance(c, Marker)),
                'cursors': sum(1 for c in children if isinstance(c, Cursor))
            }
            
            # Only update icons if counts changed
            if new_counts['traces'] != self._current_counts['traces']:
                self.trace_icon.setCount(new_counts['traces'])
            if new_counts['markers'] != self._current_counts['markers']:
                self.marker_icon.setCount(new_counts['markers'])
            if new_counts['cursors'] != self._current_counts['cursors']:
                self.cursor_icon.setCount(new_counts['cursors'])
                
            self._current_counts = new_counts
            
        except Exception as e:
            logger.error(f"Error updating plot info: {e}")
    
    def _handle_model_linked(self, parent_id: str, child_id: str):
        """Update counts when new models are linked."""
        if not self.param.model_id or parent_id != self.param.model_id:
            return
        self.queue_update()
    
    def _handle_model_removed(self, model_id: str):
        """Update counts when models are removed."""
        if not self.param.model_id:
            return
            
        # Check if removed model was our child
        model = self.param.state.get_model(self.param.model_id)
        if model and model_id in [c.id for c in model.get_children()]:
            self.queue_update()
    
    def cleanup(self):
        """Clean up signal connections."""
        try:
            if self.param.state:
                self.param.state.models_linked.disconnect(self._handle_model_linked)
                self.param.state.model_removed.disconnect(self._handle_model_removed)
        except:
            pass
        super().cleanup()

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