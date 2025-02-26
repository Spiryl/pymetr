# views/tabs/base.py
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSizePolicy
)

from pymetr.ui.views.base import BaseWidget
from pymetr.ui.components.toolbar import TabToolbar
from pymetr.core.logging import logger

class BaseTab(BaseWidget):
    """Base class for all dockable content views."""
    
    def __init__(self, state, model_id: str, parent=None):
        super().__init__(state, parent)
        self._model_id = model_id
        self.toolbar: Optional[TabToolbar] = None
        self.content_widget: Optional[QWidget] = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)        
        self._setup_container()
        self._setup_ui()  # Setup UI first
        self.set_model(model_id)  # Then set model

    def _setup_container(self):
        """Set up main container and layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create toolbar
        self.toolbar = TabToolbar()
        layout.addWidget(self.toolbar)
        
        # Create content widget container
        self.content_widget = QWidget()
        self.content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.content_widget)

    def _setup_ui(self):
        """
        Initialize UI components.
        Must be overridden by derived classes.
        """
        raise NotImplementedError("Derived classes must implement _setup_ui")

    def add_toolbar_separator(self):
        """Add separator to toolbar."""
        self.toolbar.addSeparator()
        
    def add_toolbar_stretch(self):
        """Add stretch to toolbar."""
        self.toolbar.addStretch()
        
    def add_toolbar_widget(self, widget: QWidget):
        """Add widget to toolbar."""
        return self.toolbar.addWidget(widget)

    def get_title(self) -> str:
        """Get the title for this content."""
        if self.model:
            return self.model.get_property('name', str(self._model_id))
        return str(self._model_id)