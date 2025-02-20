from typing import Optional, Any
import numpy as np
from PySide6.QtWidgets import QWidget, QHBoxLayout, QFileDialog, QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen
from pyqtgraph.parametertree import Parameter

from .base import ModelParameter, ModelParameterItem, ParameterWidget
from pymetr.core.logging import logger
from pymetr.models import Trace

class TraceStylePreview(QWidget):
    """
    Enhanced trace preview widget showing style and data length.
    Handles updates efficiently and maintains visual consistency.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(20)
        self.setMinimumWidth(100)
        
        # Cache current values to avoid unnecessary redraws
        self._current_style = {
            'color': QColor("#ffffff"),
            'style': Qt.SolidLine,
            'width': 1
        }
        self._current_length = 0
    
    def update_style(self, color: str, style: str, width: int):
        """Update line style properties efficiently."""
        try:
            new_color = QColor(color)
            new_style = self._get_qt_line_style(style)
            new_width = max(1, int(width))
            
            # Only update if something changed
            if (new_color != self._current_style['color'] or 
                new_style != self._current_style['style'] or
                new_width != self._current_style['width']):
                
                self._current_style.update({
                    'color': new_color,
                    'style': new_style,
                    'width': new_width
                })
                self.update()
                
        except Exception as e:
            logger.error(f"Error updating trace style: {e}")
    
    def set_length(self, length: int):
        """Update data length display efficiently."""
        if length != self._current_length:
            self._current_length = length
            self.update()
    
    @staticmethod
    def _get_qt_line_style(style_str: str) -> Qt.PenStyle:
        """Convert string style to Qt PenStyle with proper normalization."""
        normalized = style_str.lower().replace(" ", "").replace("-", "")
        styles = {
            "solid": Qt.SolidLine,
            "dash": Qt.DashLine,
            "dot": Qt.DotLine,
            "dashdot": Qt.DashDotLine
        }
        return styles.get(normalized, Qt.SolidLine)
    
    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw length indicator efficiently
            painter.setPen(QPen(Qt.white))
            length_text = f"[{self._current_length:,}]"
            painter.drawText(2, 0, 50, 20, Qt.AlignVCenter, length_text)
            
            # Draw style preview with cached values
            pen = QPen(self._current_style['color'])
            pen.setStyle(self._current_style['style'])
            pen.setWidth(self._current_style['width'])
            painter.setPen(pen)
            
            # Draw line sample after the length text
            line_start = 60
            painter.drawLine(line_start, 10, self.width() - 5, 10)
            
        except Exception as e:
            logger.error(f"Error painting trace preview: {e}")

class TraceInfoWidget(ParameterWidget):
    """Widget showing trace info and style preview with proper update handling."""
    
    def __init__(self, param, parent=None):
        super().__init__(param, parent)
        self._setup_ui()
        
        # Cache current values
        self._current_color = "#ffffff"
        self._current_style = "solid"
        self._current_width = 1
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.style_preview = TraceStylePreview()
        layout.addWidget(self.style_preview)
    
    def _process_pending_update(self):
        """Process style and data updates efficiently."""
        updates = self._pending_updates
        self._pending_updates = {}
        
        try:
            # Update line style if any style properties changed
            if any(key in updates for key in ['color', 'style', 'width']):
                color = updates.get('color', self._current_color)
                style = updates.get('style', self._current_style)
                width = updates.get('width', self._current_width)
                
                self._current_color = color
                self._current_style = style
                self._current_width = width
                
                self.style_preview.update_style(color, style, width)
            
            # Update length if data changed
            if 'x_data' in updates:
                if isinstance(updates['x_data'], (list, tuple, np.ndarray)):
                    self.style_preview.set_length(len(updates['x_data']))
            
            # Also check model for initial data
            elif not hasattr(self, '_initialized'):
                model = self.param.state.get_model(self.param.model_id)
                if model and hasattr(model, 'x_data'):
                    self.style_preview.set_length(len(model.x_data))
                self._initialized = True
            
        except Exception as e:
            logger.error(f"Error updating trace info: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        try:
            super().cleanup()
            if hasattr(self, 'style_preview'):
                self.style_preview.deleteLater()
        except Exception as e:
            logger.error(f"Error cleaning up trace info widget: {e}")

class TraceParameterItem(ModelParameterItem):
    """Parameter item for traces with line style preview."""
    
    def makeWidget(self) -> Optional[QWidget]:
        """Create the trace preview widget."""
        try:
            self.widget = TraceInfoWidget(self.param)
            return self.widget
        except Exception as e:
            logger.error(f"Error creating trace widget: {e}")
            return None
    
    def updateWidget(self, **kwargs):
        """Update the widget with new values."""
        if self.widget:
            self.widget.queue_update(**kwargs)
    
    def addCustomContextActions(self, menu: QMenu):
        """Add trace-specific context actions."""
        try:
            model = self.param.state.get_model(self.param.model_id)
            if not model:
                return
                
            # Add "Show Only This" action
            isolate_action = menu.addAction("Show Only This")
            isolate_action.triggered.connect(self._handle_isolate)
            
            # Add "Show All" action
            show_all_action = menu.addAction("Show All")
            show_all_action.triggered.connect(self._handle_show_all)
            
            # Add separator before data actions
            menu.addSeparator()
            
            # Add data information/actions
            x_data = model.get_property('x_data', [])
            y_data = model.get_property('y_data', [])
            if len(x_data) > 0 and len(y_data) > 0:
                # Show data range info
                x_range = f"X Range: [{min(x_data):.4g}, {max(x_data):.4g}]"
                y_range = f"Y Range: [{min(y_data):.4g}, {max(y_data):.4g}]"
                range_action = menu.addAction(f"{x_range}, {y_range}")
                range_action.setEnabled(False)  # Just for display
                
                # Add "Export Data" action
                export_action = menu.addAction("Export Data...")
                export_action.triggered.connect(self._handle_export)
                
        except Exception as e:
            logger.error(f"Error adding context actions: {e}")
    
    def _handle_isolate(self):
        """Handle 'Show Only This' action."""
        try:
            plot_model = None
            model = self.param.state.get_model(self.param.model_id)
            if model:
                # Find parent plot
                plot_model = self.param.state.get_parent(model.id)
            
            if plot_model:
                # Hide all traces except this one
                for trace in self.param.state.get_children(plot_model.id):
                    if isinstance(trace, Trace):
                        trace.set_property('visible', trace.id == model.id)
                        
        except Exception as e:
            logger.error(f"Error handling isolate action: {e}")
    
    def _handle_show_all(self):
        """Handle 'Show All' action."""
        try:
            plot_model = None
            model = self.param.state.get_model(self.param.model_id)
            if model:
                # Find parent plot
                plot_model = self.param.state.get_parent(model.id)
            
            if plot_model:
                # Show all traces
                for trace in self.param.state.get_children(plot_model.id):
                    if isinstance(trace, Trace):
                        trace.set_property('visible', True)
                        
        except Exception as e:
            logger.error(f"Error handling show all action: {e}")
    
    def _handle_export(self):
        """Handle 'Export Data' action."""
        try:
            model = self.param.state.get_model(self.param.model_id)
            if not model:
                return
                
            # Get file path from user
            path, _ = QFileDialog.getSaveFileName(
                None,
                "Export Trace Data",
                "",
                "CSV Files (*.csv);;All Files (*.*)"
            )
            
            if path:
                x_data = model.get_property('x_data', [])
                y_data = model.get_property('y_data', [])
                
                # Create DataFrame and save
                import pandas as pd
                df = pd.DataFrame({
                    'x': x_data,
                    'y': y_data
                })
                df.to_csv(path, index=False)
                
        except Exception as e:
            logger.error(f"Error exporting trace data: {e}")
            
class TraceParameter(ModelParameter):
    """
    Parameter for traces with pen styling and data handling.
    """
    
    itemClass = TraceParameterItem
    
    def __init__(self, **opts):
        opts['type'] = 'trace'
        super().__init__(**opts)
        
        model = self.state.get_model(self.model_id) if self.state and self.model_id else None
        self.setupParameters(model)
    
    def setupParameters(self, model: Optional[Trace]):
        def get_prop(name, default):
            return model.get_property(name, default) if model else default

        # Create the pen dictionary
        pen_dict = {
            'color': get_prop('color', '#ffffff'),
            'width': get_prop('width', 1),
            'style': get_prop('style', 'solid')
        }

        # Convert it to a QPen instance
        qpen = QPen()
        qpen.setColor(QColor(pen_dict['color']))
        qpen.setWidth(pen_dict['width'])
        # Use your _get_qt_line_style function to convert the style string
        qpen.setStyle(self._get_qt_line_style(pen_dict['style']))

        params = [
            dict(name='visible', type='bool', value=get_prop('visible', True)),
            dict(name='mode', type='list',
                value=get_prop('mode', 'Group'),
                limits=['Group', 'Isolate']),
            {
                'name': 'pen',
                'type': 'pen',
                'expanded':False,
                'value': qpen
            }
        ]

        # Add each parameter as a child with signal connections
        for param_opts in params:
            param = Parameter.create(**param_opts)
            if param.type() == 'pen':
                param.sigValueChanged.connect(self._handle_pen_change)
            else:
                param.sigValueChanged.connect(self._handle_parameter_change)
            self.addChild(param)
    
    def _handle_pen_change(self, param, value):
        """Handle pen parameter changes."""
        try:
            # Update individual style properties
            self.begin_update()
            try:
                self.set_model_property('color', value.color().name())
                self.set_model_property('width', value.width())
                self.set_model_property('style', self._get_style_string(value.style()))
            finally:
                self.end_update()
        except Exception as e:
            logger.error(f"Error handling pen change: {e}")
    
    def _handle_parameter_change(self, param, value):
        """Handle non-pen parameter changes."""
        self.set_model_property(param.name(), value)
    
    @staticmethod
    def _get_style_string(qt_style: Qt.PenStyle) -> str:
        """Convert Qt PenStyle to string."""
        style_map = {
            Qt.SolidLine: 'solid',
            Qt.DashLine: 'dash',
            Qt.DotLine: 'dot',
            Qt.DashDotLine: 'dashdot'
        }
        return style_map.get(qt_style, 'solid')
    
    def handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        try:
            # Update matching parameter
            if prop in ['visible', 'mode']:
                param = self.child(prop)
                if param:
                    param.setValue(value)
            
            # Update pen parameter if style property changed
            elif prop in ['color', 'width', 'style']:
                pen_param = self.child('pen')
                if pen_param:
                    pen = pen_param.value()
                    if prop == 'color':
                        pen.setColor(QColor(value))
                    elif prop == 'width':
                        pen.setWidth(value)
                    elif prop == 'style':
                        pen.setStyle(self._get_qt_line_style(value))
                    pen_param.setValue(pen)
            
            # Update widget
            if hasattr(self, 'widget'):
                self.widget.queue_update(**{prop: value})
                
        except Exception as e:
            logger.error(f"Error handling property update: {e}")
    
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