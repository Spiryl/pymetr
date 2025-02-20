from pathlib import Path
from typing import Optional, Dict, Any
from PySide6.QtWidgets import QWidget, QMenu, QInputDialog, QFileDialog
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from pyqtgraph.parametertree import Parameter, ParameterItem

from pymetr.services.file_services import FileService
from pymetr.core.logging import logger


class ParameterWidget(QWidget):
    """Base class for parameter widgets."""
    
    def __init__(self, param, parent=None):
        super().__init__(parent)
        self.param = param
        
        # Update throttling
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._process_pending_update)
        self._pending_updates: Dict[str, Any] = {}
        self._throttle_interval = 33  # ~30fps
    
    def _setup_ui(self):
        """Set up the widget UI."""
        raise NotImplementedError("Subclass must implement _setup_ui()")
    
    def _process_pending_update(self):
        """Process pending updates."""
        raise NotImplementedError("Subclass must implement _process_pending_update()")
    
    def queue_update(self, **kwargs):
        """Queue updates with throttling."""
        # logger.debug(f"Queueing update for {self.param.title()}: {kwargs}")
        self._pending_updates.update(kwargs)
        if not self._update_timer.isActive():
            self._update_timer.start(self._throttle_interval)
    
    def cleanup(self):
        """Clean up resources."""
        logger.debug(f"Cleaning up ParameterWidget for {self.param.title()}")
        self._update_timer.stop()


class ModelParameterItem(ParameterItem):
    """
    Base class for all model parameter items. Methods marked with
    NotImplementedError must be implemented by subclasses.
    """
    
    def __init__(self, param, depth, **kwargs):
        logger.debug(f"Initializing ModelParameterItem for {param.title()}")
        super().__init__(param, depth, **kwargs)
        self.hideWidget = False
        self.widget = None
        self._context_icons = self._load_context_icons()

    def optsChanged(self, param, changes):
        logger.debug(f"optsChanged called for parameter {param.title()} with changes: {changes}")
        # changes is typically a list of (propertyName, changeType, data)
        for change in changes:
            propName, changeType, data = change
            if propName == 'icon' and (changeType in ('value', 'childAdded')):
                logger.debug(f"Setting icon for {param.title()}: {data}")
                self.setIcon(data)  # Tell the item to display the icon
        
        super().optsChanged(param, changes)

    def treeWidgetChanged(self) -> None:
        super().treeWidgetChanged()
        
        # Set icon from parameter options if available
        icon = self.param.opts.get('icon')
        if icon is not None:
            self.setIcon(0, icon)
        
        if self.widget is None:
            self.widget = self.makeWidget()
            # Attach the widget to the parameter so that later calls to handle_property_update can find it.
            self.param.widget = self.widget
        tree = self.treeWidget()
        if tree is not None:
            tree.setItemWidget(self, 1, self.widget)

    def makeWidget(self) -> Optional[QWidget]:
        """Create and return the control widget."""
        logger.error("makeWidget() not implemented for parameter %s", self.param.title())
        raise NotImplementedError("Subclass must implement makeWidget()")
    
    def updateWidget(self, **kwargs):
        """Update the widget with new values."""
        logger.error("updateWidget() not implemented for parameter %s", self.param.title())
        raise NotImplementedError("Subclass must implement updateWidget()")
    
    def _load_context_icons(self) -> Dict[str, QIcon]:
        """Load standard context menu icons."""
        logger.debug("Loading context icons")
        try:
            icons_path = Path(__file__).parent.parent / 'icons'
            icons = {
                'edit': QIcon(str(icons_path / 'edit.png')),
                'delete': QIcon(str(icons_path / 'delete.png')),
                'export': QIcon(str(icons_path / 'export.png')),
                'refresh': QIcon(str(icons_path / 'refresh.png'))
            }
            logger.debug(f"Context icons loaded: {list(icons.keys())}")
            return icons
        except Exception as e:
            logger.error(f"Error loading context icons: {e}")
            return {}
    
    def contextMenuEvent(self, ev) -> None:
        """Standard context menu with extensibility."""
        logger.debug("contextMenuEvent triggered")
        try:
            menu = QMenu()
            
            # Add parameter-specific actions first
            self.addCustomContextActions(menu)
            
            # Add standard actions
            self.addStandardContextActions(menu)
            
            menu.exec_(ev.globalPos())
        except Exception as e:
            logger.error(f"Error showing context menu: {e}")
    
    def addCustomContextActions(self, menu: QMenu):
        """Add parameter-specific context menu actions."""
        logger.error("addCustomContextActions() not implemented for parameter %s", self.param.title())
        raise NotImplementedError("Subclass must implement addCustomContextActions()")
    
    def addStandardContextActions(self, menu: QMenu):
        """Add standard context menu actions."""
        if not self._context_icons:
            logger.debug("No context icons available for %s", self.param.title())
            return
            
        # Rename action
        rename_action = menu.addAction(
            self._context_icons.get('edit'),
            "Rename"
        )
        rename_action.triggered.connect(self._handleRename)
        
        menu.addSeparator()
        
        # Remove action
        remove_action = menu.addAction(
            self._context_icons.get('delete'),
            "Remove"
        )
        remove_action.triggered.connect(self._handleRemove)
        
        # Export action if supported
        if hasattr(self.param, 'can_export') and self.param.can_export:
            export_action = menu.addAction(
                self._context_icons.get('export'),
                "Export"
            )
            export_action.triggered.connect(self._handleExport)
    
    def _handleRename(self):
        """Handle rename action."""
        logger.debug("Rename action triggered for %s", self.param.title())
        if not hasattr(self.param, 'state') or not hasattr(self.param, 'model_id'):
            logger.debug("Parameter %s missing state or model_id", self.param.title())
            return
        try:
            model = self.param.state.get_model(self.param.model_id)
            if not model:
                logger.debug("No model found for %s", self.param.model_id)
                return
            current_name = model.get_property('name', '')
            new_name, ok = QInputDialog.getText(
                None, 
                "Rename",
                "Enter new name:",
                text=current_name
            )
            if ok and new_name and new_name != current_name:
                logger.debug("Renaming %s from '%s' to '%s'", self.param.title(), current_name, new_name)
                model.set_property('name', new_name)
        except Exception as e:
            logger.error(f"Error renaming parameter: {e}")
    
    def _handleRemove(self):
        """Handle remove action."""
        logger.debug("Remove action triggered for %s", self.param.title())
        if hasattr(self.param, 'remove_model'):
            self.param.remove_model()
    
    def _handleExport(self):
        """Handle export action."""
        logger.debug("Export action triggered for %s", self.param.title())
        if not hasattr(self.param, 'state') or not hasattr(self.param, 'model_id'):
            logger.debug("Parameter %s missing state or model_id", self.param.title())
            return
        try:
            path, _ = QFileDialog.getSaveFileName(
                None, "Export Data", "", "YAML Files (*.yaml)"
            )
            if path:
                FileService.export_model_data(
                    self.param.model_id,
                    self.param.state,
                    Path(path)
                )
        except Exception as e:
            logger.error(f"Error exporting parameter data: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        logger.debug("Cleaning up ModelParameterItem for %s", self.param.title())
        try:
            if self.widget:
                self.widget.cleanup()
                self.widget.deleteLater()
                self.widget = None
            self._context_icons.clear()
        except Exception as e:
            logger.error(f"Error cleaning up parameter item: {e}")

class ModelParameter(Parameter):
    """Base class for model parameters."""
    
    def __init__(self, **opts):
        # Store state and model info
        self.state = opts.get('state')
        self.model_id = opts.get('model_id')
        self.can_export = opts.get('can_export', False)
        
        # Batch update support
        self._batch_mode = False
        self._pending_updates: Dict[str, Any] = {}
        
        # Get model type for type-safe updates
        model = self.state.get_model(self.model_id) if self.state and self.model_id else None
        if model:
            self.model_type = model.model_type
        else:
            self.model_type = None
        
        super().__init__(**opts)
    
    def setupParameters(self, model):
        """Set up child parameters based on model."""
        raise NotImplementedError("Subclass must implement setupParameters()")
    
    def begin_update(self):
        """Begin batch update mode."""
        self._batch_mode = True
        self._pending_updates.clear()
    
    def end_update(self):
        """End batch update mode and apply updates."""
        updates = self._pending_updates.copy()
        self._batch_mode = False
        self._pending_updates.clear()
        for name, value in updates.items():
            self.set_model_property(name, value)
    
    def set_model_property(self, name: str, value: Any):
        """Set a model property with batch support."""
        if self._batch_mode:
            self._pending_updates[name] = value
            return
        if self.state and self.model_id:
            model = self.state.get_model(self.model_id)
            if model:
                model.set_property(name, value)
    
    def get_model_property(self, name: str, default: Any = None) -> Any:
        """Get a model property."""
        if self.state and self.model_id:
            model = self.state.get_model(self.model_id)
            if model:
                return model.get_property(name, default)
        return default
    
    def remove_model(self):
        """Remove the model with cleanup."""
        if not hasattr(self, 'state') or not hasattr(self, 'model_id'):
            return
        try:
            model = self.state.get_model(self.model_id)
            if model:
                parent = self.state.get_parent(self.model_id)
                if parent:
                    self.state.unlink_models(parent.id, self.model_id)
                self.state.remove_model(self.model_id)
        except Exception as e:
            logger.error(f"Error removing model: {e}")

