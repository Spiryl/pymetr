from typing import Optional, Any
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen
from pyqtgraph.parametertree import Parameter

from .base import ModelParameter, ModelParameterItem, ParameterWidget
from pymetr.core.logging import logger
from pymetr.models import Cursor

class CursorPreviewWidget(ParameterWidget):
    """
    Widget showing cursor position and line preview.
    """
    def __init__(self, param, parent=None):
        super().__init__(param, parent)
        self._setup_ui()
        
        # Cache current values
        self._current_position = 0.0
        self._current_axis = 'x'  # 'x' for vertical, 'y' for horizontal
        self._current_color = "#ffffff"
        self._current_style = "solid"
        self._current_width = 1
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Position display
        self.position_label = QLabel()
        self.position_label.setStyleSheet("""
            QLabel {
                color: #dddddd;
                padding: 2px 4px;
                min-width: 80px;
            }
        """)
        
        # Line preview
        self.line_preview = CursorLinePreview()
        
        layout.addWidget(self.position_label)
        layout.addWidget(self.line_preview)
        layout.addStretch()
    
    def _process_pending_update(self):
        """Process style and position updates."""
        updates = self._pending_updates
        self._pending_updates = {}
        
        try:
            # Update position display
            if 'position' in updates or 'axis' in updates:
                pos = updates.get('position', self._current_position)
                axis = updates.get('axis', self._current_axis)
                self._current_position = pos
                self._current_axis = axis
                # Format position display
                axis_label = 'X' if axis == 'x' else 'Y'
                self.position_label.setText(f"{axis_label} = {pos:.4g}")
            
            # Update line preview
            if any(key in updates for key in ['color', 'style', 'width', 'axis']):
                self.line_preview.update_style(
                    updates.get('axis', self._current_axis),
                    updates.get('color', self._current_color),
                    updates.get('style', self._current_style),
                    updates.get('width', self._current_width)
                )
                
        except Exception as e:
            logger.error(f"Error updating cursor preview: {e}")

class CursorLinePreview(QWidget):
    """Widget showing cursor line style preview."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 20)
        
        self._axis = 'x'
        self._color = QColor("#ffffff")
        self._style = Qt.SolidLine
        self._width = 1
    
    def update_style(self, axis: str, color: str, style: str, width: int):
        """Update line style properties."""
        self._axis = axis
        self._color = QColor(color)
        self._style = self._get_qt_line_style(style)
        self._width = width
        self.update()
    
    @staticmethod
    def _get_qt_line_style(style_str: str) -> Qt.PenStyle:
        """Convert string style to Qt PenStyle."""
        styles = {
            'solid': Qt.SolidLine,
            'dash': Qt.DashLine,
            'dot': Qt.DotLine,
            'dashdot': Qt.DashDotLine
        }
        return styles.get(style_str.lower(), Qt.SolidLine)
    
    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Set up pen
            pen = QPen(self._color)
            pen.setStyle(self._style)
            pen.setWidth(self._width)
            painter.setPen(pen)
            
            # Draw preview line
            if self._axis == 'x':  # Vertical line
                x = self.width() / 2
                painter.drawLine(x, 2, x, self.height() - 2)
            else:  # Horizontal line
                y = self.height() / 2
                painter.drawLine(2, y, self.width() - 2, y)
                
        except Exception as e:
            logger.error(f"Error drawing cursor preview: {e}")

class CursorParameterItem(ModelParameterItem):
    """Parameter item for cursors."""
    
    def makeWidget(self) -> Optional[QWidget]:
        """Create the cursor preview widget."""
        try:
            self.widget = CursorPreviewWidget(self.param)
            return self.widget
        except Exception as e:
            logger.error(f"Error creating cursor widget: {e}")
            return None
    
    def updateWidget(self, **kwargs):
        """Update the preview widget with new values."""
        if self.widget:
            self.widget.queue_update(**kwargs)
    
    def addCustomContextActions(self, menu: QMenu):
        """Add cursor-specific context actions."""
        # Toggle axis action
        model = self.param.state.get_model(self.param.model_id)
        if model:
            current_axis = model.get_property('axis', 'x')
            new_axis = 'y' if current_axis == 'x' else 'x'
            toggle_action = menu.addAction(f"Switch to {new_axis.upper()} axis")
            toggle_action.triggered.connect(
                lambda: self.param.set_model_property('axis', new_axis)
            )

class CursorParameter(ModelParameter):
    """
    Parameter for cursors with line style and position control.
    """
    
    itemClass = CursorParameterItem
    
    def __init__(self, **opts):
        opts['type'] = 'cursor'
        super().__init__(**opts)
        
        model = self.state.get_model(self.model_id) if self.state and self.model_id else None
        self.setupParameters(model)
    
    def setupParameters(self, model: Optional[Cursor]):
        """Set up cursor parameters with flat structure."""
        def get_prop(name, default):
            return model.get_property(name, default) if model else default
        
        # Create parameters
        params = [
            # Position and orientation
            dict(name='position', type='float',
                 value=get_prop('position', 0.0)),
            dict(name='axis', type='list',
                 value=get_prop('axis', 'x'),
                 limits=['x', 'y']),
            dict(name='visible', type='bool',
                 value=get_prop('visible', True)),
            dict(name='label', type='str',
                 value=get_prop('label', '')),
            
            # Line style
            dict(name='color', type='color',
                 value=get_prop('color', '#ffffff')),
            dict(name='style', type='list',
                 value=get_prop('style', 'solid'),
                 limits=['solid', 'dash', 'dot', 'dashdot']),
            dict(name='width', type='int',
                 value=get_prop('width', 1),
                 limits=(1, 5))
        ]
        
        # Add all parameters
        for param_opts in params:
            param = Parameter.create(**param_opts)
            self.addChild(param)
            param.sigValueChanged.connect(self._handle_parameter_change)
    
    def _handle_parameter_change(self, param, value):
        """Handle parameter changes."""
        self.set_model_property(param.name(), value)
    
    def handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        try:
            # Update matching parameter
            param = self.child(prop)
            if param:
                param.setValue(value)
            
            # Update preview widget
            if hasattr(self, 'widget'):
                self.widget.queue_update(**{prop: value})
                
        except Exception as e:
            logger.error(f"Error handling property update: {e}")

