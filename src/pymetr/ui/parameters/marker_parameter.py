from typing import Optional, Any, Tuple
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QMenu
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QPen
from pyqtgraph.parametertree import Parameter

from .base import ModelParameter, ModelParameterItem, ParameterWidget
from pymetr.core.logging import logger
from pymetr.models import Marker, Trace  # Add Trace import

class MarkerPreviewWidget(ParameterWidget):
    """
    Enhanced widget showing marker info with uncertainty and trace binding.
    """
    def __init__(self, param, parent=None):
        super().__init__(param, parent)
        self._setup_ui()
        
        # Cache for current values
        self._current_x = 0.0
        self._current_y = 0.0
        self._current_color = "#ffffff"
        self._current_symbol = "o"
        self._current_size = 8
        self._current_uncertainty = (None, None)
        self._current_bound = False
        self._current_mode = "linear"
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Position info - shows (x,y) and [computed] for trace binding
        self.position_label = QLabel()
        self.position_label.setStyleSheet("""
            QLabel {
                color: #dddddd;
                padding: 2px 4px;
                min-width: 120px;
            }
        """)
        
        # Symbol preview - shows marker with uncertainty bars
        self.symbol_preview = MarkerSymbolPreview()
        
        # Trace binding indicator
        self.binding_label = QLabel()
        self.binding_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-style: italic;
                padding: 2px 4px;
            }
        """)
        
        layout.addWidget(self.position_label)
        layout.addWidget(self.symbol_preview)
        layout.addWidget(self.binding_label)
        layout.addStretch()

    def _process_pending_update(self):
        """Process position and style updates."""
        updates = self._pending_updates
        self._pending_updates = {}
        
        try:
            # Update position display if x or y changed
            if 'x' in updates or 'y' in updates:
                x = updates.get('x', self._current_x)
                y = updates.get('y', self._current_y)
                self._current_x = x
                self._current_y = y
                self.position_label.setText(f"({x:.4g}, {y:.4g})")

            # Update marker style if style properties changed
            if any(key in updates for key in ['color', 'symbol', 'size']):
                color = updates.get('color', self._current_color)
                symbol = updates.get('symbol', self._current_symbol)
                size = updates.get('size', self._current_size)
                
                self._current_color = color
                self._current_symbol = symbol
                self._current_size = size

                # Get current uncertainty values
                if 'uncertainty_visible' in updates:
                    if updates['uncertainty_visible']:
                        upper = updates.get('uncertainty_upper', 0.0)
                        lower = updates.get('uncertainty_lower', 0.0)
                        self._current_uncertainty = (lower, upper)
                    else:
                        self._current_uncertainty = (None, None)
                
                self.symbol_preview.update_style(
                    color, 
                    symbol, 
                    size, 
                    self._current_uncertainty
                )

            # Update binding status if changed
            if 'bound_to_trace' in updates:
                self._current_bound = updates['bound_to_trace']
                self.binding_label.setText("[bound]" if self._current_bound else "")
                self.binding_label.setVisible(self._current_bound)

        except Exception as e:
            logger.error(f"Error updating marker preview: {e}")

class MarkerSymbolPreview(QWidget):
    """
    Custom widget showing marker symbol with uncertainty bars.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 20)
        
        self._color = QColor("#ffffff")
        self._symbol = "o"
        self._size = 8
        self._uncertainty = (None, None)
        
        # Symbol drawing functions
        self._symbol_funcs = {
            'o': self._draw_circle,
            's': self._draw_square,
            't': self._draw_triangle,
            'd': self._draw_diamond
        }
    
    def update_style(self, color: str, symbol: str, size: int, 
                    uncertainty: Tuple[Optional[float], Optional[float]]):
        try:
            self._color = QColor(color)
            self._symbol = symbol
            self._size = size
            self._uncertainty = uncertainty
            self.update()  # Force a repaint
            logger.debug(f"Updated marker style: color={color}, symbol={symbol}, size={size}")
        except Exception as e:
            logger.error(f"Error updating marker style: {e}")
    
    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Center point for symbol
            center = QPointF(30, 10)
            
            # Draw uncertainty bars if enabled
            if self._uncertainty[0] is not None and self._uncertainty[1] is not None:
                painter.setPen(QPen(self._color, 1, Qt.DashLine))
                # Scale uncertainty to widget height
                lower_y = 15  # Bottom of widget
                upper_y = 5   # Top of widget
                painter.drawLine(QPointF(30, lower_y), QPointF(30, upper_y))
                # End caps
                painter.drawLine(QPointF(27, lower_y), QPointF(33, lower_y))
                painter.drawLine(QPointF(27, upper_y), QPointF(33, upper_y))
            
            # Draw symbol
            painter.setPen(QPen(self._color))
            painter.setBrush(self._color)
            
            draw_func = self._symbol_funcs.get(self._symbol, self._draw_circle)
            draw_func(painter, center, self._size)
            
        except Exception as e:
            logger.error(f"Error drawing marker preview: {e}")

    def _draw_circle(self, painter, center, size):
        """Draw circle symbol."""
        radius = size / 2
        painter.drawEllipse(center, radius, radius)

    def _draw_square(self, painter, center, size):
        """Draw square symbol."""
        half_size = size / 2
        painter.drawRect(center.x() - half_size, center.y() - half_size, 
                        size, size)

    def _draw_triangle(self, painter, center, size):
        """Draw triangle symbol."""
        half_size = size / 2
        points = [
            QPointF(center.x(), center.y() - half_size),  # Top
            QPointF(center.x() - half_size, center.y() + half_size),  # Bottom left
            QPointF(center.x() + half_size, center.y() + half_size)   # Bottom right
        ]
        painter.drawPolygon(points)

    def _draw_diamond(self, painter, center, size):
        """Draw diamond symbol."""
        half_size = size / 2
        points = [
            QPointF(center.x(), center.y() - half_size),  # Top
            QPointF(center.x() + half_size, center.y()),  # Right
            QPointF(center.x(), center.y() + half_size),  # Bottom
            QPointF(center.x() - half_size, center.y())   # Left
        ]
        painter.drawPolygon(points)

class MarkerInfoWidget(ParameterWidget):
    """Widget showing marker info and symbol preview."""
    
    def __init__(self, param, parent=None):
        super().__init__(param, parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.symbol_preview = MarkerSymbolPreview()
        layout.addWidget(self.symbol_preview)
    
    def _process_pending_update(self):
        """Process position and style updates."""
        updates = self._pending_updates
        self._pending_updates = {}
        
        try:
            # Update marker style if any style properties changed
            if any(key in updates for key in ['color', 'symbol', 'size']):
                color = updates.get('color', self._current_color)
                symbol = updates.get('symbol', self._current_symbol)
                size = updates.get('size', self._current_size)
                
                self._current_color = color
                self._current_symbol = symbol
                self._current_size = size
                
                # Get current uncertainty values
                uncertainty = self._current_uncertainty
                if 'uncertainty_visible' in updates:
                    if updates['uncertainty_visible']:
                        upper = updates.get('uncertainty_upper', 0.0)
                        lower = updates.get('uncertainty_lower', 0.0)
                        uncertainty = (lower, upper)
                    else:
                        uncertainty = (None, None)
                
                self.symbol_preview.update_style(color, symbol, size, uncertainty)
            
            # Update position if x or y changed
            if 'x' in updates or 'y' in updates:
                x = updates.get('x', self._current_x)
                y = updates.get('y', self._current_y)
                self._current_x = x
                self._current_y = y
                self.position_label.setText(f"({x:.4g}, {y:.4g})")
                
            # Update binding status if changed
            if 'bound_to_trace' in updates:
                self._current_bound = updates['bound_to_trace']
                self.binding_label.setText("[bound]" if self._current_bound else "")
                self.binding_label.setVisible(self._current_bound)
                
        except Exception as e:
            logger.error(f"Error updating marker preview: {e}")

class MarkerParameterItem(ModelParameterItem):
    """Parameter item for markers with enhanced preview."""
    
    def makeWidget(self) -> Optional[QWidget]:
        """Create the marker preview widget."""
        try:
            self.widget = MarkerPreviewWidget(self.param)
            return self.widget
        except Exception as e:
            logger.error(f"Error creating marker widget: {e}")
            return None
    
    def updateWidget(self, **kwargs):
        """Update the preview widget with new values."""
        if self.widget:
            self.widget.queue_update(**kwargs)
    
    def addCustomContextActions(self, menu: QMenu):
        """Add marker-specific context actions."""
        # Add reset uncertainty action if enabled
        model = self.param.state.get_model(self.param.model_id)
        if model and model.get_property('uncertainty_visible', False):
            reset_action = menu.addAction("Reset Uncertainty")
            reset_action.triggered.connect(self._handle_reset_uncertainty)
    
    def _handle_reset_uncertainty(self):
        """Reset uncertainty bounds to zero."""
        try:
            self.param.begin_update()
            self.param.set_model_property('uncertainty_upper', 0.0)
            self.param.set_model_property('uncertainty_lower', 0.0)
            self.param.end_update()
        except Exception as e:
            logger.error(f"Error resetting uncertainty: {e}")

    
class MarkerParameter(ModelParameter):
    """
    Enhanced parameter for markers with trace binding and uncertainty support.
    Provides flat structure for common properties with minimal nesting.
    """
    
    itemClass = MarkerParameterItem
    
    def __init__(self, **opts):
        opts['type'] = 'marker'
        super().__init__(**opts)
        
        model = self.state.get_model(self.model_id) if self.state and self.model_id else None
        self.setupParameters(model)
    
    def setupParameters(self, model: Optional[Marker]):
        """Set up marker parameters with flattened structure."""
        def get_prop(name, default):
            return model.get_property(name, default) if model else default
        
        # Top-level parameters for quick access
        params = [
            # Position and identification
            dict(name='x', type='float',
                 value=get_prop('x', 0.0)),
            dict(name='y', type='float',
                 value=get_prop('y', 0.0),
                 enabled=not model.bound_to_trace if model else True),
            dict(name='label', type='str',
                 value=get_prop('label', '')),
            dict(name='visible', type='bool',
                 value=get_prop('visible', True)),
            
            # Visual style
            dict(name='color', type='color',
                 value=get_prop('color', '#ffffff')),
            dict(name='symbol', type='list',
                 value=get_prop('symbol', 'o'),
                 limits=['o', 's', 't', 'd']),
            dict(name='size', type='int',
                 value=get_prop('size', 8),
                 limits=(4, 20)),
                 
            # Interpolation (only shown when trace-bound)
            dict(name='interpolation_mode', type='list',
                 value=get_prop('interpolation_mode', 'linear'),
                 limits=['linear', 'nearest'],
                 visible=model.bound_to_trace if model else False),
            
            # Uncertainty as a subgroup
            {
                'name': 'Uncertainty',
                'type': 'group',
                'children': [
                    dict(name='uncertainty_visible', type='bool',
                         value=get_prop('uncertainty_visible', False)),
                    dict(name='uncertainty_upper', type='float',
                         value=get_prop('uncertainty_upper', 0.0)),
                    dict(name='uncertainty_lower', type='float',
                         value=get_prop('uncertainty_lower', 0.0))
                ]
            }
        ]
        
        # Add all parameters
        for param_opts in params:
            param = Parameter.create(**param_opts)
            self.addChild(param)
            
            # Connect change handlers
            if param.type() == 'group':
                for child in param.children():
                    child.sigValueChanged.connect(self._handle_parameter_change)
            else:
                param.sigValueChanged.connect(self._handle_parameter_change)
    
    def handle_property_update(self, prop: str, value: Any):
        """Handle model property updates with preview updates."""
        try:
            # For uncertainty properties, we need to handle them separately
            if prop.startswith('uncertainty_'):
                uncertainty_group = self.child('Uncertainty')
                if uncertainty_group and uncertainty_group.parent() is not None:  # Check if still in tree
                    param = uncertainty_group.child(prop)
                    if param and param.parent() is not None:  # Check if still in tree
                        # Block signals during setValue
                        param.setValue(value, blockSignal=self._handle_parameter_change)
            else:
                # For all other properties, they're at the root level
                param = self.child(prop)
                if param and param.parent() is not None:  # Check if still in tree
                    # Block signals during setValue
                    param.setValue(value, blockSignal=self._handle_parameter_change)

            # Special handling for bound_to_trace
            if prop == 'bound_to_trace':
                y_param = self.child('y')
                if y_param and y_param.parent() is not None:  # Check if still in tree
                    y_param.setOpts(enabled=not value)
                
                # Show/hide interpolation mode
                interp_param = self.child('interpolation_mode')
                if interp_param and interp_param.parent() is not None:  # Check if still in tree
                    interp_param.setOpts(visible=value)

            # Update preview widget
            if hasattr(self, 'widget') and self.widget and not self.widget.isDeleted():
                self.widget.queue_update(**{prop: value})

        except Exception as e:
            logger.error(f"Error handling property update: {e}")

    def _handle_parameter_change(self, param, value):
        """Handle parameter changes with trace binding awareness."""
        try:
            # Get current model
            model = self.state.get_model(self.model_id)
            if not model:
                return
            
            # Make sure parameter still exists
            if param.parent() is None:  # Check if parameter still in tree
                return
            
            # Special handling for y-value when trace bound
            if param.name() == 'y' and model.bound_to_trace:
                return  # Ignore y changes when bound to trace
            
            # Handle uncertainty visibility changes
            if param.name() == 'uncertainty_visible':
                uncertainty_group = self.child('Uncertainty')
                if uncertainty_group and uncertainty_group.parent() is not None:  # Check if still in tree
                    for child in uncertainty_group.children():
                        if child and child.parent() is not None and child.name() != 'uncertainty_visible':
                            child.setOpts(visible=value)
            
            # Update the model
            self.set_model_property(param.name(), value)
            
        except Exception as e:
            logger.error(f"Error handling parameter change: {e}")


# from typing import Optional, Any, Tuple
# from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QMenu
# from PySide6.QtCore import Qt, QPointF
# from PySide6.QtGui import QPainter, QColor, QPen
# from pyqtgraph.parametertree import Parameter

# from .base import ModelParameter, ModelParameterItem, ParameterWidget
# from pymetr.core.logging import logger
# from pymetr.models import Marker, Trace  # Add Trace import

# class MarkerPreviewWidget(ParameterWidget):
#     """
#     Enhanced widget showing marker info with uncertainty and trace binding.
#     """
#     def __init__(self, param, parent=None):
#         super().__init__(param, parent)
#         self._setup_ui()
        
#         # Cache for current values
#         self._current_x = 0.0
#         self._current_y = 0.0
#         self._current_color = "#ffffff"
#         self._current_symbol = "o"
#         self._current_size = 8
#         self._current_uncertainty = (None, None)
#         self._current_bound = False
#         self._current_mode = "linear"
    
#     def _setup_ui(self):
#         layout = QHBoxLayout(self)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setSpacing(4)
        
#         # Position info - shows (x,y) and [computed] for trace binding
#         self.position_label = QLabel()
#         self.position_label.setStyleSheet("""
#             QLabel {
#                 color: #dddddd;
#                 padding: 2px 4px;
#                 min-width: 120px;
#             }
#         """)
        
#         # Symbol preview - shows marker with uncertainty bars
#         self.symbol_preview = MarkerSymbolPreview()
        
#         # Trace binding indicator
#         self.binding_label = QLabel()
#         self.binding_label.setStyleSheet("""
#             QLabel {
#                 color: #666666;
#                 font-style: italic;
#                 padding: 2px 4px;
#             }
#         """)
        
#         layout.addWidget(self.position_label)
#         layout.addWidget(self.symbol_preview)
#         layout.addWidget(self.binding_label)
#         layout.addStretch()

#     def _process_pending_update(self):
#         """Process position and style updates."""
#         updates = self._pending_updates
#         self._pending_updates = {}
        
#         try:
#             # Update position display if x or y changed
#             if 'x' in updates or 'y' in updates:
#                 x = updates.get('x', self._current_x)
#                 y = updates.get('y', self._current_y)
#                 self._current_x = x
#                 self._current_y = y
#                 self.position_label.setText(f"({x:.4g}, {y:.4g})")

#             # Update marker style if style properties changed
#             if any(key in updates for key in ['color', 'symbol', 'size']):
#                 color = updates.get('color', self._current_color)
#                 symbol = updates.get('symbol', self._current_symbol)
#                 size = updates.get('size', self._current_size)
                
#                 self._current_color = color
#                 self._current_symbol = symbol
#                 self._current_size = size

#                 # Get current uncertainty values
#                 if 'uncertainty_visible' in updates:
#                     if updates['uncertainty_visible']:
#                         upper = updates.get('uncertainty_upper', 0.0)
#                         lower = updates.get('uncertainty_lower', 0.0)
#                         self._current_uncertainty = (lower, upper)
#                     else:
#                         self._current_uncertainty = (None, None)
                
#                 self.symbol_preview.update_style(
#                     color, 
#                     symbol, 
#                     size, 
#                     self._current_uncertainty
#                 )

#             # Update binding status if changed
#             if 'bound_to_trace' in updates:
#                 self._current_bound = updates['bound_to_trace']
#                 self.binding_label.setText("[bound]" if self._current_bound else "")
#                 self.binding_label.setVisible(self._current_bound)

#         except Exception as e:
#             logger.error(f"Error updating marker preview: {e}")

# class MarkerSymbolPreview(QWidget):
#     """
#     Custom widget showing marker symbol with uncertainty bars.
#     """
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setFixedSize(60, 20)
        
#         self._color = QColor("#ffffff")
#         self._symbol = "o"
#         self._size = 8
#         self._uncertainty = (None, None)
        
#         # Symbol drawing functions
#         self._symbol_funcs = {
#             'o': self._draw_circle,
#             's': self._draw_square,
#             't': self._draw_triangle,
#             'd': self._draw_diamond
#         }
    
#     def update_style(self, color: str, symbol: str, size: int, 
#                     uncertainty: Tuple[Optional[float], Optional[float]]):
#         try:
#             self._color = QColor(color)
#             self._symbol = symbol
#             self._size = size
#             self._uncertainty = uncertainty
#             self.update()  # Force a repaint
#             logger.debug(f"Updated marker style: color={color}, symbol={symbol}, size={size}")
#         except Exception as e:
#             logger.error(f"Error updating marker style: {e}")
    
#     def paintEvent(self, event):
#         try:
#             painter = QPainter(self)
#             painter.setRenderHint(QPainter.Antialiasing)
            
#             # Center point for symbol
#             center = QPointF(30, 10)
            
#             # Draw uncertainty bars if enabled
#             if self._uncertainty[0] is not None and self._uncertainty[1] is not None:
#                 painter.setPen(QPen(self._color, 1, Qt.DashLine))
#                 # Scale uncertainty to widget height
#                 lower_y = 15  # Bottom of widget
#                 upper_y = 5   # Top of widget
#                 painter.drawLine(QPointF(30, lower_y), QPointF(30, upper_y))
#                 # End caps
#                 painter.drawLine(QPointF(27, lower_y), QPointF(33, lower_y))
#                 painter.drawLine(QPointF(27, upper_y), QPointF(33, upper_y))
            
#             # Draw symbol
#             painter.setPen(QPen(self._color))
#             painter.setBrush(self._color)
            
#             draw_func = self._symbol_funcs.get(self._symbol, self._draw_circle)
#             draw_func(painter, center, self._size)
            
#         except Exception as e:
#             logger.error(f"Error drawing marker preview: {e}")

#     def _draw_circle(self, painter, center, size):
#         """Draw circle symbol."""
#         radius = size / 2
#         painter.drawEllipse(center, radius, radius)

#     def _draw_square(self, painter, center, size):
#         """Draw square symbol."""
#         half_size = size / 2
#         painter.drawRect(center.x() - half_size, center.y() - half_size, 
#                         size, size)

#     def _draw_triangle(self, painter, center, size):
#         """Draw triangle symbol."""
#         half_size = size / 2
#         points = [
#             QPointF(center.x(), center.y() - half_size),  # Top
#             QPointF(center.x() - half_size, center.y() + half_size),  # Bottom left
#             QPointF(center.x() + half_size, center.y() + half_size)   # Bottom right
#         ]
#         painter.drawPolygon(points)

#     def _draw_diamond(self, painter, center, size):
#         """Draw diamond symbol."""
#         half_size = size / 2
#         points = [
#             QPointF(center.x(), center.y() - half_size),  # Top
#             QPointF(center.x() + half_size, center.y()),  # Right
#             QPointF(center.x(), center.y() + half_size),  # Bottom
#             QPointF(center.x() - half_size, center.y())   # Left
#         ]
#         painter.drawPolygon(points)

# class MarkerInfoWidget(ParameterWidget):
#     """Widget showing marker info and symbol preview."""
    
#     def __init__(self, param, parent=None):
#         super().__init__(param, parent)
#         self._setup_ui()
    
#     def _setup_ui(self):
#         layout = QHBoxLayout(self)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setSpacing(4)
        
#         self.symbol_preview = MarkerSymbolPreview()
#         layout.addWidget(self.symbol_preview)
    
#     def _process_pending_update(self):
#         """Process position and style updates."""
#         updates = self._pending_updates
#         self._pending_updates = {}
        
#         try:
#             # Update marker style if any style properties changed
#             if any(key in updates for key in ['color', 'symbol', 'size']):
#                 color = updates.get('color', self._current_color)
#                 symbol = updates.get('symbol', self._current_symbol)
#                 size = updates.get('size', self._current_size)
                
#                 self._current_color = color
#                 self._current_symbol = symbol
#                 self._current_size = size
                
#                 # Get current uncertainty values
#                 uncertainty = self._current_uncertainty
#                 if 'uncertainty_visible' in updates:
#                     if updates['uncertainty_visible']:
#                         upper = updates.get('uncertainty_upper', 0.0)
#                         lower = updates.get('uncertainty_lower', 0.0)
#                         uncertainty = (lower, upper)
#                     else:
#                         uncertainty = (None, None)
                
#                 self.symbol_preview.update_style(color, symbol, size, uncertainty)
            
#             # Update position if x or y changed
#             if 'x' in updates or 'y' in updates:
#                 x = updates.get('x', self._current_x)
#                 y = updates.get('y', self._current_y)
#                 self._current_x = x
#                 self._current_y = y
#                 self.position_label.setText(f"({x:.4g}, {y:.4g})")
                
#             # Update binding status if changed
#             if 'bound_to_trace' in updates:
#                 self._current_bound = updates['bound_to_trace']
#                 self.binding_label.setText("[bound]" if self._current_bound else "")
#                 self.binding_label.setVisible(self._current_bound)
                
#         except Exception as e:
#             logger.error(f"Error updating marker preview: {e}")

# class MarkerParameterItem(ModelParameterItem):
#     """Parameter item for markers with enhanced preview."""
    
#     def makeWidget(self) -> Optional[QWidget]:
#         """Create the marker preview widget."""
#         try:
#             self.widget = MarkerPreviewWidget(self.param)
#             return self.widget
#         except Exception as e:
#             logger.error(f"Error creating marker widget: {e}")
#             return None
    
#     def updateWidget(self, **kwargs):
#         """Update the preview widget with new values."""
#         if self.widget:
#             self.widget.queue_update(**kwargs)
    
#     def addCustomContextActions(self, menu: QMenu):
#         """Add marker-specific context actions."""
#         # Add reset uncertainty action if enabled
#         model = self.param.state.get_model(self.param.model_id)
#         if model and model.get_property('uncertainty_visible', False):
#             reset_action = menu.addAction("Reset Uncertainty")
#             reset_action.triggered.connect(self._handle_reset_uncertainty)
    
#     def _handle_reset_uncertainty(self):
#         """Reset uncertainty bounds to zero."""
#         try:
#             self.param.begin_update()
#             self.param.set_model_property('uncertainty_upper', 0.0)
#             self.param.set_model_property('uncertainty_lower', 0.0)
#             self.param.end_update()
#         except Exception as e:
#             logger.error(f"Error resetting uncertainty: {e}")

    
# class MarkerParameter(ModelParameter):
#     """
#     Enhanced parameter for markers with trace binding and uncertainty support.
#     Provides flat structure for common properties with minimal nesting.
#     """
    
#     itemClass = MarkerParameterItem
    
#     def __init__(self, **opts):
#         opts['type'] = 'marker'
#         super().__init__(**opts)
        
#         model = self.state.get_model(self.model_id) if self.state and self.model_id else None
#         self.setupParameters(model)
    
#     def setupParameters(self, model: Optional[Marker]):
#         """Set up marker parameters with flattened structure."""
#         def get_prop(name, default):
#             return model.get_property(name, default) if model else default
        
#         # Top-level parameters for quick access
#         params = [
#             # Position and identification
#             dict(name='x', type='float',
#                  value=get_prop('x', 0.0)),
#             dict(name='y', type='float',
#                  value=get_prop('y', 0.0),
#                  enabled=not model.bound_to_trace if model else True),
#             dict(name='label', type='str',
#                  value=get_prop('label', '')),
#             dict(name='visible', type='bool',
#                  value=get_prop('visible', True)),
            
#             # Visual style
#             dict(name='color', type='color',
#                  value=get_prop('color', '#ffffff')),
#             dict(name='symbol', type='list',
#                  value=get_prop('symbol', 'o'),
#                  limits=['o', 's', 't', 'd']),
#             dict(name='size', type='int',
#                  value=get_prop('size', 8),
#                  limits=(4, 20)),
                 
#             # Interpolation (only shown when trace-bound)
#             dict(name='interpolation_mode', type='list',
#                  value=get_prop('interpolation_mode', 'linear'),
#                  limits=['linear', 'nearest'],
#                  visible=model.bound_to_trace if model else False),
            
#             # Uncertainty as a subgroup
#             {
#                 'name': 'Uncertainty',
#                 'type': 'group',
#                 'children': [
#                     dict(name='uncertainty_visible', type='bool',
#                          value=get_prop('uncertainty_visible', False)),
#                     dict(name='uncertainty_upper', type='float',
#                          value=get_prop('uncertainty_upper', 0.0)),
#                     dict(name='uncertainty_lower', type='float',
#                          value=get_prop('uncertainty_lower', 0.0))
#                 ]
#             }
#         ]
        
#         # Add all parameters
#         for param_opts in params:
#             param = Parameter.create(**param_opts)
#             self.addChild(param)
            
#             # Connect change handlers
#             if param.type() == 'group':
#                 for child in param.children():
#                     child.sigValueChanged.connect(self._handle_parameter_change)
#             else:
#                 param.sigValueChanged.connect(self._handle_parameter_change)
    
#     def handle_property_update(self, prop: str, value: Any):
#         """Handle model property updates with preview updates."""
#         try:
#             # For uncertainty properties, we need to handle them separately
#             if prop.startswith('uncertainty_'):
#                 uncertainty_group = self.child('Uncertainty')
#                 if uncertainty_group and not uncertainty_group.isRemoved():
#                     param = uncertainty_group.child(prop)
#                     if param and not param.isRemoved():
#                         param.setValue(value)
#             else:
#                 # For all other properties, they're at the root level
#                 param = self.child(prop)
#                 if param and not param.isRemoved():
#                     param.setValue(value)

#             # Special handling for bound_to_trace
#             if prop == 'bound_to_trace':
#                 y_param = self.child('y')
#                 if y_param and not y_param.isRemoved():
#                     y_param.setOpts(enabled=not value)
                
#                 # Show/hide interpolation mode
#                 interp_param = self.child('interpolation_mode')
#                 if interp_param and not interp_param.isRemoved():
#                     interp_param.setOpts(visible=value)

#             # Update preview widget
#             if hasattr(self, 'widget') and self.widget and not self.widget.isDeleted():
#                 self.widget.queue_update(**{prop: value})

#         except Exception as e:
#             logger.error(f"Error handling property update: {e}")

#     def _handle_parameter_change(self, param, value):
#         """Handle parameter changes with trace binding awareness."""
#         try:
#             # Get current model
#             model = self.state.get_model(self.model_id)
#             if not model:
#                 return
            
#             # Make sure parameter still exists
#             if param.isRemoved():
#                 return
            
#             # Special handling for y-value when trace bound
#             if param.name() == 'y' and model.bound_to_trace:
#                 return  # Ignore y changes when bound to trace
            
#             # Handle uncertainty visibility changes
#             if param.name() == 'uncertainty_visible':
#                 uncertainty_group = self.child('Uncertainty')
#                 if uncertainty_group and not uncertainty_group.isRemoved():
#                     for child in uncertainty_group.children():
#                         if child and not child.isRemoved() and child.name() != 'uncertainty_visible':
#                             child.setOpts(visible=value)
            
#             # Update the model
#             self.set_model_property(param.name(), value)
            
#         except Exception as e:
#             logger.error(f"Error handling parameter change: {e}")
