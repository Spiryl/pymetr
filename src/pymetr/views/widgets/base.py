from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal, Slot

from pymetr.models.base import BaseModel
from pymetr.core.logging import logger

class BaseWidget(QWidget):
    """
    Base class for all widgets that display model data.
    Handles model synchronization and updates.
    """
    
    # Signals
    model_changed = Signal(object)  # model
    
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._model_id = None
        self._updating = False  # Prevent update loops
        
    @property
    def model_id(self):
        return self._model_id
        
    @property
    def model(self) -> BaseModel:
        """Get current model instance."""
        if self._model_id:
            return self.state.get_model(self._model_id)
        return None
        
    def set_model(self, model_id: str):
        """Set the model for this widget."""
        if model_id != self._model_id:
            # # Disconnect from old model if exists
            # if self._model_id:
            #     old_model = self.state.get_model(self._model_id)
            #     if old_model:
            #         old_model.property_changed.disconnect(self._handle_property_change)
            
            # Connect to new model
            self._model_id = model_id
            model = self.state.get_model(model_id)
            if model:
                model.property_changed.connect(self._handle_property_change)
                self.update_from_model(model)
                self.model_changed.emit(model)
                
    def update_from_model(self, model: BaseModel):
        """
        Update widget from model data.
        Override in subclasses.
        """
        pass
        
    def update_model(self, **properties):
        """
        Update model properties from widget.
        
        Args:
            **properties: Property name/value pairs to update
        """
        if not self._model_id or self._updating:
            return
            
        model = self.state.get_model(self._model_id)
        if model:
            for name, value in properties.items():
                model.set_property(name, value)
                
    @Slot(str, str, str, object)  # NEW signature: model_id, model_type, prop, value
    def _handle_property_change(self, model_id: str, model_type: str, prop: str, value: object):
        """Handle model property changes."""
        if model_id != self._model_id or self._updating:
            return
            
        try:
            self._updating = True
            self.handle_property_update(prop, value)
        finally:
            self._updating = False
            
    def handle_property_update(self, prop: str, value: object):
        """
        Handle specific property updates.
        Override in subclasses.
        """
        pass
        
    def closeEvent(self, event):
        """Clean up model connections on close."""
        if self._model_id:
            model = self.state.get_model(self._model_id)
            if model:
                model.property_changed.disconnect(self._handle_property_change)
        super().closeEvent(event)