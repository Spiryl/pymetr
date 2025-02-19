from typing import Dict, Any, Optional, List
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QMenu
from PySide6.QtCore import QTimer

from pyqtgraph.parametertree import Parameter
from .base import ModelParameter, ModelParameterItem
from pymetr.core.logging import logger

class TableInfoWidget(QWidget):
    """
    Enhanced widget showing table metadata with efficient updates.
    Displays row/column counts and data type information.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Update throttling: adjusted to ~33ms (~30fps)
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._process_pending_update)
        self._pending_info = None
        self._throttle_interval = 33
        
        # Cache for metadata
        self._current_info = {
            'rows': 0,
            'cols': 0,
            'types': []
        }
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Info labels
        self.size_label = QLabel()
        self.type_label = QLabel()
        
        # Style labels
        for label in [self.size_label, self.type_label]:
            label.setStyleSheet("""
                QLabel {
                    color: #dddddd;
                    padding: 2px 4px;
                }
            """)
        
        layout.addWidget(self.size_label)
        layout.addWidget(self.type_label)
        layout.addStretch()
        
        self.setLayout(layout)
        
    def queue_update(self, rows: int, cols: int, types: List[str] = None):
        """Queue metadata update with throttling."""
        self._pending_info = {
            'rows': rows,
            'cols': cols,
            'types': types or []
        }
        if not self._update_timer.isActive():
            self._update_timer.start(self._throttle_interval)
    
    def _process_pending_update(self):
        """Process pending metadata update."""
        if not self._pending_info:
            return
            
        info = self._pending_info
        self._pending_info = None
        
        try:
            # Update only if changed
            if (info['rows'] != self._current_info['rows'] or 
                info['cols'] != self._current_info['cols']):
                self.size_label.setText(f"{info['rows']}×{info['cols']}")
                self._current_info.update(info)
            
            # Update type info if provided and changed
            if info['types'] and info['types'] != self._current_info['types']:
                type_text = self._format_type_info(info['types'])
                self.type_label.setText(type_text)
                self._current_info['types'] = info['types']
                
        except Exception as e:
            logger.error(f"Error updating table info: {e}")
    
    def _format_type_info(self, types: List[str]) -> str:
        """Format type information efficiently."""
        if not types:
            return ""
            
        try:
            # Get unique types with counts
            type_counts = {}
            for t in types:
                type_counts[t] = type_counts.get(t, 0) + 1
            
            # Format as compact string
            type_info = [f"{t}({c})" for t, c in type_counts.items()]
            return ", ".join(type_info)
            
        except Exception as e:
            logger.error(f"Error formatting type info: {e}")
            return ""
    
    def cleanup(self):
        """Clean up resources."""
        self._update_timer.stop()

class DataTableParameterItem(ModelParameterItem):
    """Enhanced parameter item for data tables."""
    
    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.hideWidget = False
        self.widget = None
        
    def makeWidget(self) -> Optional[QWidget]:
        """Create the info widget."""
        try:
            self.widget = TableInfoWidget()
            self.update_table_info()
            return self.widget
        except Exception as e:
            logger.error(f"Error creating table widget: {e}")
            return None
        
    def update_table_info(self):
        """Update table metadata display."""
        if (hasattr(self, 'widget') and self.widget and 
            hasattr(self.param, 'state') and 
            hasattr(self.param, 'model_id')):
            try:
                model = self.param.state.get_model(self.param.model_id)
                if model:
                    rows = model.get_property('row_count', 0)
                    cols = model.get_property('col_count', 0)
                    types = model.get_property('column_types', [])
                    self.widget.queue_update(rows, cols, types)
            except Exception as e:
                logger.error(f"Error updating table info: {e}")
                
    def treeWidgetChanged(self):
        """Set up tree widget with info display."""
        super().treeWidgetChanged()
        if not hasattr(self, 'widget') or not self.widget:
            self.widget = self.makeWidget()
        tree = self.treeWidget()
        if tree is not None:
            tree.setItemWidget(self, 1, self.widget)
    
    def cleanup(self):
        """Clean up resources properly."""
        try:
            if hasattr(self, 'widget') and self.widget:
                self.widget.cleanup()
                self.widget.deleteLater()
                self.widget = None
        except Exception as e:
            logger.error(f"Error cleaning up table parameter: {e}")
        super().cleanup()

class DataTableParameter(ModelParameter):
    """
    Enhanced parameter for data table display and control.
    Handles table metadata and provides efficient updates.
    """
    itemClass = DataTableParameterItem

    def __init__(self, **opts):
        opts['type'] = 'datatable'
        super().__init__(**opts)
        
        # Get model for initial values
        model = self.state.get_model(self.model_id) if self.state and self.model_id else None
        
        # Add export capability
        self.can_export = True
        
        # Set up child parameters
        self._setup_parameters(model)
        
    def _setup_parameters(self, model):
        """Set up child parameters with proper structure."""
        children = [
            dict(
                name='Display',
                type='group',
                children=[
                    dict(name='show_index', type='bool', default=None,
                         value=model.get_property('show_index', True) if model else True),
                    dict(name='show_header', type='bool', default=None,
                         value=model.get_property('show_header', True) if model else True),
                    dict(name='alternate_rows', type='bool', default=None,
                         value=model.get_property('alternate_rows', True) if model else True)
                ]
            ),
            dict(
                name='Format',
                type='group',
                children=[
                    dict(name='decimal_places', type='int', default=None,
                         value=model.get_property('decimal_places', 2) if model else 2,
                         limits=(0, 10)),
                    dict(name='thousands_separator', type='bool', default=None,
                         value=model.get_property('thousands_separator', True) if model else True)
                ]
            )
        ]
        
        # Add parameters and connect handlers
        for child in children:
            param = Parameter.create(**child)
            self.addChild(param)
            if child['type'] == 'group':
                for subchild in param.children():
                    subchild.sigValueChanged.connect(self._handle_child_change)
    
    def _handle_child_change(self, param, value):
        """Handle parameter changes efficiently."""
        if not self.state or not self.model_id:
            return
            
        try:
            # Update the model
            self.set_model_property(param.name(), value)
            
            # Update display if needed
            if hasattr(self, 'widget') and self.widget:
                self.widget.update_table_info()
                
        except Exception as e:
            logger.error(f"Error handling parameter change: {e}")
    
    def handle_property_update(self, name: str, value: Any):
        """Handle model property updates efficiently."""
        try:
            # First update any matching parameters
            updated = False
            for group in self.children():
                if group.type() == 'group':
                    for param in group.children():
                        if param.name() == name:
                            param.setValue(value)
                            updated = True
                            break
                    if updated:
                        break
            
            # Update table info if metadata changed
            if name in ['row_count', 'col_count', 'column_types']:
                if hasattr(self, 'widget') and self.widget:
                    self.widget.update_table_info()
                    
        except Exception as e:
            logger.error(f"Error handling property update: {e}")

    def add_context_actions(self, menu: QMenu) -> None:
        """Add table-specific context actions."""
        # Add actions for table operations if needed
        pass
