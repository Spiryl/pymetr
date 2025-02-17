from typing import Any
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QMenu
)
from PySide6.QtGui import QIcon

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
        self.info_label.setStyleSheet("""
            QLabel {
                color: #3498DB;
                padding: 2px 8px;
                border: 1px solid #3498DB;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.info_label)
        
    def update_info(self, trace_count: int):
        """Update plot info display."""
        self.info_label.setText(f"{trace_count} traces")

class PlotParameterItem(ModelParameterItem):
    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.hideWidget = False
        self.widget = None
        
    def makeWidget(self):
        self.widget = PlotStatusWidget()
        self.update_trace_count()  # Initial update
        return self.widget
        
    def update_trace_count(self):
        if self.widget and self.param.state and self.param.model_id:
            model = self.param.state.get_model(self.param.model_id)
            if model:
                trace_count = len([c for c in model.get_children() if isinstance(c, Trace)])
                self.widget.update_info(trace_count)
                
    def treeWidgetChanged(self):
        """Called when this item is added or removed from a tree."""
        super().treeWidgetChanged()
        if self.widget is None:
            self.widget = self.makeWidget()
        tree = self.treeWidget()
        if tree is not None:
            tree.setItemWidget(self, 1, self.widget)

class PlotParameter(ModelParameter):
    itemClass = PlotParameterItem
    
    def __init__(self, **opts):
        # Get model properties from opts
        model = None
        if opts.get('state') and opts.get('model_id'):
            model = opts['state'].get_model(opts['model_id'])

        opts['type'] = 'plot'
        # Create a dedicated class for settings to avoid weak reference issues
        class Setting:
            def __init__(self, value):
                self.value = value
            def __str__(self):
                return str(self.value)
                
        opts['children'] = [
            {
                'name': 'Settings',
                'type': 'group',
                'expanded': False,
                'children': [
                    {'name': 'title', 'type': 'str', 'value': Setting(model.get_property('title', '') if model else '')},
                    {'name': 'grid_enabled', 'type': 'bool', 'value': Setting(model.get_property('grid_enabled', True) if model else True)},
                    {'name': 'legend_enabled', 'type': 'bool', 'value': Setting(model.get_property('legend_enabled', True) if model else True)},
                    {'name': 'x_label', 'type': 'str', 'value': Setting(model.get_property('x_label', '') if model else '')},
                    {'name': 'y_label', 'type': 'str', 'value': Setting(model.get_property('y_label', '') if model else '')},
                    {'name': 'x_unit', 'type': 'str', 'value': Setting(model.get_property('x_unit', '') if model else '')},
                    {'name': 'y_unit', 'type': 'str', 'value': Setting(model.get_property('y_unit', '') if model else '')}
                ]
            }
        ]
        super().__init__(**opts)

    def add_context_actions(self, menu: QMenu) -> None:
        """Add parameter-specific menu actions."""
        pass

    def handle_property_update(self, name: str, value: Any):
        """Handle model property updates."""
        # Update settings group values when model changes
        settings = self.child('Settings')
        if settings and name in [c.name() for c in settings.children()]:
            settings.child(name).setValue(value)

# from typing import Any
# from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
# from PySide6.QtCore import Qt

# from .base import ModelParameter, ModelParameterItem
# from pymetr.core.logging import logger
# from pymetr.models.trace import Trace

# class PlotStatusWidget(QWidget):
#     """Simple widget showing trace count."""
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self._setup_ui()
        
#     def _setup_ui(self):
#         layout = QHBoxLayout(self)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setSpacing(4)
        
#         self.count_label = QLabel()
#         layout.addWidget(self.count_label)
        
#     def update_trace_count(self, count: int):
#         """Update trace count display."""
#         self.count_label.setText(f"{count} traces")

# class PlotParameterItem(ModelParameterItem):
#     def __init__(self, param, depth):
#         super().__init__(param, depth)
#         self.hideWidget = False
#         self.widget = None
        
#     def makeWidget(self):
#         self.widget = PlotStatusWidget()
#         self.update_trace_count()
#         return self.widget
        
#     def update_trace_count(self):
#         if self.widget and self.param.state and self.param.model_id:
#             model = self.param.state.get_model(self.param.model_id)
#             if model:
#                 trace_count = len([c for c in model.get_children() if isinstance(c, Trace)])
#                 self.widget.update_trace_count(trace_count)
                
#     def treeWidgetChanged(self):
#         """Called when this item is added or removed from a tree."""
#         super().treeWidgetChanged()
#         if self.widget is None:
#             self.widget = self.makeWidget()
#         tree = self.treeWidget()
#         if tree is not None:
#             tree.setItemWidget(self, 1, self.widget)

# class PlotParameter(ModelParameter):
#     """Parameter tree item for Plot models with all settings in one group."""
    
#     itemClass = PlotParameterItem
    
#     def __init__(self, **opts):
#         # Get model properties from opts
#         model = None
#         if opts.get('state') and opts.get('model_id'):
#             model = opts['state'].get_model(opts['model_id'])

#         opts['type'] = 'plot'
        
#         # Create settings group with all properties
#         opts['children'] = [
#             {
#                 'name': 'Settings',
#                 'type': 'group',
#                 'children': [
#                     {'name': 'title', 'type': 'str', 'value': model.get_property('title', '') if model else ''},
#                     {'name': 'x_label', 'type': 'str', 'value': model.get_property('x_label', '') if model else ''},
#                     {'name': 'y_label', 'type': 'str', 'value': model.get_property('y_label', '') if model else ''},
#                     {'name': 'x_unit', 'type': 'str', 'value': model.get_property('x_unit', '') if model else ''},
#                     {'name': 'y_unit', 'type': 'str', 'value': model.get_property('y_unit', '') if model else ''},
#                     {'name': 'grid_enabled', 'type': 'bool', 'value': model.get_property('grid_enabled', True) if model else True},
#                     {'name': 'legend_enabled', 'type': 'bool', 'value': model.get_property('legend_enabled', True) if model else True},
#                     {'name': 'roi_visible', 'type': 'bool', 'value': model.get_property('roi_visible', True) if model else True},
#                     {'name': 'legend_position', 'type': 'list', 'value': model.get_property('legend_position', 'right') if model else 'right',
#                      'limits': ['right', 'top', 'bottom', 'left']},
#                     {'name': 'x_log', 'type': 'bool', 'value': model.get_property('x_log', False) if model else False},
#                     {'name': 'y_log', 'type': 'bool', 'value': model.get_property('y_log', False) if model else False},
#                     {'name': 'x_inverted', 'type': 'bool', 'value': model.get_property('x_inverted', False) if model else False},
#                     {'name': 'y_inverted', 'type': 'bool', 'value': model.get_property('y_inverted', False) if model else False}
#                 ]
#             }
#         ]
        
#         super().__init__(**opts)

#     def handle_property_update(self, name: str, value: Any):
#         """Handle model property updates."""
#         settings = self.child('Settings')
#         if settings:
#             for param in settings.children():
#                 if param.name() == name:
#                     param.setValue(value)
#                     return