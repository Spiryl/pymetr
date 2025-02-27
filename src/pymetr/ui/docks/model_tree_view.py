from typing import Dict, Any, Optional, TypeVar
from pathlib import Path
from PySide6.QtWidgets import (
    QHeaderView, QSizePolicy, QVBoxLayout, QAbstractItemView
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QIcon

import pyqtgraph.parametertree as pt
from pyqtgraph.parametertree import Parameter, ParameterTree

from ..parameters.device_parameter import DeviceParameter
from ..parameters.trace_parameter import TraceParameter
from ..parameters.plot_parameter import PlotParameter
from ..parameters.marker_parameter import MarkerParameter
from ..parameters.cursor_parameter import CursorParameter
from ..parameters.data_table_parameter import DataTableParameter
from ..parameters.test_script_parameter import TestScriptParameter
from ..parameters.test_result_parameter import TestResultParameter
from ..parameters.test_suite_parameter import TestSuiteParameter
from ..parameters.base import ModelParameter

from pymetr.ui.views.base import BaseWidget
from pymetr.models.base import BaseModel

from pymetr.core.logging import logger

T = TypeVar('T', bound=BaseModel)

class ModelTreeView(BaseWidget):
    """
    Tree view for displaying and controlling model hierarchy.
    Implements observer pattern for state updates and provides
    efficient update batching.
    """
    
    # Register parameter types
    PARAMETER_TYPES = {
        'device': DeviceParameter,
        'trace': TraceParameter,
        'plot': PlotParameter,
        'marker': MarkerParameter,
        'cursor': CursorParameter,
        'datatable': DataTableParameter,
        'testscript': TestScriptParameter,
        'testresult': TestResultParameter,
        'testsuite': TestSuiteParameter  # Add TestSuite parameter type
    }
    
    # Register parameter types with pyqtgraph
    for name, cls in PARAMETER_TYPES.items():
        pt.registerParameterType(name, cls)
    
    # Signals
    selection_changed = Signal(str)  # Emits selected model_id
    
    # Model type icons
    MODEL_ICONS = {
        'TestSuite': 'test_suite.png',  # Add TestSuite icon
        'TestScript': 'script.png',
        'TestResult': 'result.png',
        'TestGroup': 'folder.png',
        'Device': 'instruments.png',
        'Plot': 'chart.png',
        'Trace': 'waves.png',
        'Cursor': 'cursor.png',
        'Marker': 'markers.png',
        'DataTable': 'table.png',
        'Measurement': 'measure.png',
        'default': 'file_open.png'
    }

    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        
        # Item tracking
        self._items: Dict[str, Parameter] = {}
        self._icon_cache: Dict[str, QIcon] = {}
        
        # Update batching
        self._pending_updates: Dict[str, Dict[str, Any]] = {}
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._process_pending_updates)
        self._throttle_interval = 200  # ~30fps
        
        # Set up UI and connect signals
        self._setup_ui()
        self._connect_signals()
        self._preload_icons()
    
    def _setup_ui(self):
        """Initialize UI with optimized settings."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.tree = ParameterTree(self)
        self.tree.setAlternatingRowColors(False)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # Configure header
        header = self.tree.header()
        header.setMinimumSectionSize(120)
        header.setDefaultSectionSize(150)
        header.setStretchLastSection(True)
        header.setVisible(False)
        
        # Set size policies
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Create root parameter
        self.root = Parameter.create(name='Session', type='group', children=[])
        self.tree.setParameters(self.root, showTop=False)
        
        layout.addWidget(self.tree)
    
    def _connect_signals(self):
        """Connect to state signals for updates."""
        # Tree selection
        self.tree.itemSelectionChanged.connect(self._handle_selection_changed)
        
        # State signals
        self.state.model_registered.connect(self._handle_model_registered)
        self.state.models_linked.connect(self._handle_models_linked)
        self.state.model_changed.connect(self._queue_model_change)
        self.state.model_removed.connect(self._handle_model_removed)
    
    def _preload_icons(self):
        """Preload and cache icons for efficiency."""
        try:
            icons_path = Path(__file__).parent.parent / 'icons'
            for model_type, icon_file in self.MODEL_ICONS.items():
                icon_path = str(icons_path / icon_file)
                self._icon_cache[model_type] = QIcon(icon_path)
                logger.debug(f"Loaded icon: {icon_file} for type {model_type} from {icons_path}")
        except Exception as e:
            logger.error(f"Error preloading icons: {e}")
    
    def _get_icon(self, model_type: str) -> QIcon:
        """Get cached icon for model type."""
        return self._icon_cache.get(model_type, self._icon_cache['default'])
    
    def _create_parameter_for_model(self, model: BaseModel) -> Optional[Parameter]:
        """Create appropriate parameter type for model."""
        try:
            # Get model info
            model_type = type(model).__name__
            name = model.get_property('name', 'Unnamed')
            icon = self._get_icon(model_type)
            
            # Base parameter options
            param_opts = {
                'name': model.id,
                'title': name,
                'state': self.state,
                'model_id': model.id,
                'expanded': False,
                'removable': False,
                'renamable': False,
                'icon': icon,
                'default': None
            }
            
            # Create type-specific parameter
            param_type = model_type.lower()
            if param_type in self.PARAMETER_TYPES:
                param_class = self.PARAMETER_TYPES[param_type]
                # Auto-expand suites and scripts
                if param_type in ['testsuite', 'testscript']:
                    param_opts['expanded'] = True
                return param_class(**param_opts)
            
            # Default to group parameter
            param_opts['type'] = 'group'
            return Parameter.create(**param_opts)
            
        except Exception as e:
            logger.error(f"Error creating parameter for model {model.id}-{model_type}-{name}: {e}")
            return None
    
    def _handle_model_registered(self, model_id: str):
        """Handle new model registration."""
        try:
            model = self.state.get_model(model_id)
            if not model:
                return
            
            param = self._create_parameter_for_model(model)
            if param:
                self._items[model_id] = param
                
                # Start batch update if it's a model parameter
                if isinstance(param, ModelParameter):
                    param.begin_update()
                
                # Add to tree
                self.root.addChild(param)
                
                # End batch update
                if isinstance(param, ModelParameter):
                    param.end_update()
                
        except Exception as e:
            logger.error(f"Error registering model {model_id}: {e}")
    
    def _handle_models_linked(self, parent_id: str, child_id: str):
        """Handle model linking."""
        try:
            if parent_id in self._items and child_id in self._items:
                parent_param = self._items[parent_id]
                child_param = self._items[child_id]
                
                if child_param.parent():
                    child_param.remove()
                
                parent_param.addChild(child_param)
                
        except Exception as e:
            logger.error(f"Error linking models: {e}")
    
    def _queue_model_change(self, model_id: str, model_type: str, prop: str, value: Any):
        """Queue model updates for batch processing."""
        if model_id not in self._pending_updates:
            self._pending_updates[model_id] = {}
        self._pending_updates[model_id][prop] = value
        
        if not self._update_timer.isActive():
            self._update_timer.start(self._throttle_interval)
    
    def _process_pending_updates(self):
        """Process all queued model updates."""
        updates = self._pending_updates.copy()
        self._pending_updates.clear()
        
        for model_id, props in updates.items():
            if model_id in self._items:
                param = self._items[model_id]
                
                # Start batch update
                if isinstance(param, ModelParameter):
                    param.begin_update()
                
                # Apply updates
                for prop, value in props.items():
                    if hasattr(param, 'handle_property_update'):
                        param.handle_property_update(prop, value)
                
                # End batch update
                if isinstance(param, ModelParameter):
                    param.end_update()
    
    def _handle_model_removed(self, model_id: str):
        """Clean up when a model is removed."""
        if model_id in self._items:
            param = self._items[model_id]
            
            # Recursively cleanup child parameters
            def cleanup_parameter(p):
                try:
                    for child in p.children():
                        cleanup_parameter(child)
                    if hasattr(p, 'cleanup'):
                        p.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up parameter {p.name()}: {e}")
            
            try:
                cleanup_parameter(param)
                param.remove()
                del self._items[model_id]
                
            except Exception as e:
                logger.error(f"Error removing tree item for {model_id}: {e}")
    
    def _handle_selection_changed(self):
        """Handle tree selection changes."""
        try:
            selected = self.tree.selectedItems()
            if not selected or not selected[0].param:
                return
            
            param = selected[0].param
            model_id = getattr(param, 'model_id', param.name())
            
            model = self.state.get_model(model_id)
            if not model:
                return
            
            # Find viewable parent if needed
            if not hasattr(model, 'show'):
                parent = self._find_viewable_parent(model_id)
                if not parent:
                    return
                model = parent
            
            # Show view and emit selection
            model.show()
            self.selection_changed.emit(model.id)
            
        except Exception as e:
            logger.error(f"Error handling selection change: {e}")
    
    def _find_viewable_parent(self, model_id: str) -> Optional[BaseModel]:
        """Find first parent that has a view."""
        parent = self.state.get_parent(model_id)
        while parent:
            if hasattr(parent, 'show'):
                return parent
            parent = self.state.get_parent(parent.id)
        return None
    
    def cleanup(self):
        """Clean up resources."""
        try:
            # Stop timer
            self._update_timer.stop()
            
            # Clean up items
            for item in list(self._items.values()):
                if hasattr(item, 'cleanup'):
                    item.cleanup()
            self._items.clear()
            
            # Clear caches
            self._icon_cache.clear()
            self._pending_updates.clear()
            
        except Exception as e:
            logger.error(f"Error cleaning up tree view: {e}")

# from typing import Dict, Any, Optional, TypeVar
# from pathlib import Path
# from PySide6.QtWidgets import (
#     QHeaderView, QSizePolicy, QVBoxLayout, QAbstractItemView
# )
# from PySide6.QtCore import Signal, Qt, QTimer

# import pyqtgraph.parametertree as pt
# from pyqtgraph.parametertree import Parameter, ParameterTree

# # Import from parameter factory
# from pymetr.ui.factories.parameter_factory import ParameterFactory
# from pymetr.ui.parameters import ALL_PARAMETER_CLASSES

# from pymetr.ui.views.base import BaseWidget
# from pymetr.models.base import BaseModel

# from pymetr.core.logging import logger

# T = TypeVar('T', bound=BaseModel)

# class ModelTreeView(BaseWidget):
#     """
#     Tree view for displaying and controlling model hierarchy.
#     Implements observer pattern for state updates and provides
#     efficient update batching.
#     """
    
#     # Register parameter types with pyqtgraph
#     for name, cls in ALL_PARAMETER_CLASSES.items():
#         # Convert PascalCase to lowercase for parameter type registration
#         param_type = ''.join([c.lower() if i == 0 or not c.isupper() 
#                               else f"_{c.lower()}" for i, c in enumerate(name)])
#         param_type = param_type.replace('_parameter', '')
#         pt.registerParameterType(param_type, cls)
    
#     # Signals
#     selection_changed = Signal(str)  # Emits selected model_id

#     def __init__(self, state, parent=None):
#         super().__init__(state, parent)
        
#         # Item tracking
#         self._items: Dict[str, Parameter] = {}
        
#         # Update batching
#         self._pending_updates: Dict[str, Dict[str, Any]] = {}
#         self._update_timer = QTimer(self)
#         self._update_timer.setSingleShot(True)
#         self._update_timer.timeout.connect(self._process_pending_updates)
#         self._throttle_interval = 33  # ~30fps
        
#         # Set up UI and connect signals
#         self._setup_ui()
#         self._connect_signals()
    
#     def _setup_ui(self):
#         """Initialize UI with optimized settings."""
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setSpacing(0)
        
#         self.tree = ParameterTree(self)
#         self.tree.setAlternatingRowColors(False)
#         self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        
#         # Configure header
#         header = self.tree.header()
#         header.setMinimumSectionSize(120)
#         header.setDefaultSectionSize(150)
#         header.setStretchLastSection(True)
#         header.setVisible(False)
        
#         # Set size policies
#         self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
#         self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
#         # Create root parameter
#         self.root = Parameter.create(name='Session', type='group', children=[])
#         self.tree.setParameters(self.root, showTop=False)
        
#         layout.addWidget(self.tree)
    
#     def _connect_signals(self):
#         """Connect to state signals for updates."""
#         # Tree selection
#         self.tree.itemSelectionChanged.connect(self._handle_selection_changed)
        
#         # State signals
#         self.state.model_registered.connect(self._handle_model_registered)
#         self.state.models_linked.connect(self._handle_models_linked)
#         self.state.model_changed.connect(self._queue_model_change)
#         self.state.model_removed.connect(self._handle_model_removed)
    
#     def _create_parameter_for_model(self, model: BaseModel) -> Optional[Parameter]:
#         """Create appropriate parameter type for model."""
#         try:
#             # Get model info
#             model_type = type(model).__name__
#             name = model.get_property('name', 'Unnamed')
            
#             # Get icon from factory
#             icon = ParameterFactory.get_icon(model_type)
            
#             # Try to create parameter using factory first
#             param = ParameterFactory.create_parameter(model)
            
#             if param:
#                 # Set common properties that might not be set by the factory
#                 param.setOpts(
#                     name=model.id,
#                     title=name,
#                     icon=icon,
#                     expanded=(model_type in ['TestSuite', 'TestScript'])
#                 )
#                 return param
            
#             # Fallback to default group parameter if factory doesn't handle this type
#             return Parameter.create(
#                 name=model.id,
#                 title=name,
#                 type='group',
#                 state=self.state,
#                 model_id=model.id,
#                 expanded=False,
#                 removable=False,
#                 renamable=False,
#                 icon=icon,
#                 default=None
#             )
            
#         except Exception as e:
#             logger.error(f"Error creating parameter for model {model.id}-{model_type}-{name}: {e}")
#             return None
    
#     def _handle_model_registered(self, model_id: str):
#         """Handle new model registration."""
#         try:
#             model = self.state.get_model(model_id)
#             if not model:
#                 return
            
#             param = self._create_parameter_for_model(model)
#             if param:
#                 self._items[model_id] = param
                
#                 # Start batch update if it's a model parameter
#                 if hasattr(param, 'begin_update'):
#                     param.begin_update()
                
#                 # Add to tree
#                 self.root.addChild(param)
                
#                 # End batch update
#                 if hasattr(param, 'end_update'):
#                     param.end_update()
                
#         except Exception as e:
#             logger.error(f"Error registering model {model_id}: {e}")
    
#     def _handle_models_linked(self, parent_id: str, child_id: str):
#         """Handle model linking."""
#         try:
#             if parent_id in self._items and child_id in self._items:
#                 parent_param = self._items[parent_id]
#                 child_param = self._items[child_id]
                
#                 if child_param.parent():
#                     child_param.remove()
                
#                 parent_param.addChild(child_param)
                
#         except Exception as e:
#             logger.error(f"Error linking models: {e}")
    
#     def _queue_model_change(self, model_id: str, model_type: str, prop: str, value: Any):
#         """Queue model updates for batch processing."""
#         if model_id not in self._pending_updates:
#             self._pending_updates[model_id] = {}
#         self._pending_updates[model_id][prop] = value
        
#         if not self._update_timer.isActive():
#             self._update_timer.start(self._throttle_interval)
    
#     def _process_pending_updates(self):
#         """Process all queued model updates."""
#         updates = self._pending_updates.copy()
#         self._pending_updates.clear()
        
#         for model_id, props in updates.items():
#             if model_id in self._items:
#                 param = self._items[model_id]
                
#                 # Start batch update
#                 if hasattr(param, 'begin_update'):
#                     param.begin_update()
                
#                 # Apply updates
#                 for prop, value in props.items():
#                     if hasattr(param, 'handle_property_update'):
#                         param.handle_property_update(prop, value)
                
#                 # End batch update
#                 if hasattr(param, 'end_update'):
#                     param.end_update()
    
#     def _handle_model_removed(self, model_id: str):
#         """Clean up when a model is removed."""
#         if model_id in self._items:
#             param = self._items[model_id]
            
#             # Recursively cleanup child parameters
#             def cleanup_parameter(p):
#                 try:
#                     for child in p.children():
#                         cleanup_parameter(child)
#                     if hasattr(p, 'cleanup'):
#                         p.cleanup()
#                 except Exception as e:
#                     logger.error(f"Error cleaning up parameter {p.name()}: {e}")
            
#             try:
#                 cleanup_parameter(param)
#                 param.remove()
#                 del self._items[model_id]
                
#             except Exception as e:
#                 logger.error(f"Error removing tree item for {model_id}: {e}")
    
#     def _handle_selection_changed(self):
#         """Handle tree selection changes."""
#         try:
#             selected = self.tree.selectedItems()
#             if not selected or not selected[0].param:
#                 return
            
#             param = selected[0].param
#             model_id = getattr(param, 'model_id', param.name())
            
#             model = self.state.get_model(model_id)
#             if not model:
#                 return
            
#             # Find viewable parent if needed
#             if not hasattr(model, 'show'):
#                 parent = self._find_viewable_parent(model_id)
#                 if not parent:
#                     return
#                 model = parent
            
#             # Show view and emit selection
#             model.show()
#             self.selection_changed.emit(model.id)
            
#         except Exception as e:
#             logger.error(f"Error handling selection change: {e}")(f"Error handling selection change: {e}")
    
#     def _find_viewable_parent(self, model_id: str) -> Optional[BaseModel]:
#         """Find first parent that has a view."""
#         parent = self.state.get_parent(model_id)
#         while parent:
#             if hasattr(parent, 'show'):
#                 return parent
#             parent = self.state.get_parent(parent.id)
#         return None
    
#     def cleanup(self):
#         """Clean up resources."""
#         try:
#             # Stop timer
#             self._update_timer.stop()
            
#             # Clean up items
#             for item in list(self._items.values()):
#                 if hasattr(item, 'cleanup'):
#                     item.cleanup()
#             self._items.clear()
            
#             # Clear pending updates
#             self._pending_updates.clear()
            
#         except Exception as e:
#             logger.error(f"Error cleaning up tree view: {e}").error(f"Error handling selection change: {e}")
    
#     def _find_viewable_parent(self, model_id: str) -> Optional[BaseModel]:
#         """Find first parent that has a view."""
#         parent = self.state.get_parent(model_id)
#         while parent:
#             if hasattr(parent, 'show'):
#                 return parent
#             parent = self.state.get_parent(parent.id)
#         return None
    
#     def cleanup(self):
#         """Clean up resources."""
#         try:
#             # Stop timer
#             self._update_timer.stop()
            
#             # Clean up items
#             for item in list(self._items.values()):
#                 if hasattr(item, 'cleanup'):
#                     item.cleanup()
#             self._items.clear()
            
#             # Clear caches
#             self._icon_cache.clear()
#             self._pending_updates.clear()
            
#         except Exception as e:
#             logger.error(f"Error cleaning up tree view: {e}")