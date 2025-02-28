from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Slot

from pymetr.ui.views.discovery_view import DiscoveryView
from pymetr.core.logging import logger

class DiscoveryDialog(QDialog):
    """Dialog for instrument discovery and connection."""
    
    def __init__(self, state, model_filter=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.model_filter = model_filter
        self.result_info = None
        
        self._setup_ui()
        
        # Start discovery with optional filter
        self._start_discovery()
        
    def _setup_ui(self):
        """Initialize dialog UI."""
        self.setWindowTitle("Discover Instruments")
        self.setMinimumSize(800, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        
        # Discovery view (reused component)
        self.discovery_view = DiscoveryView(self.state)
        self.discovery_view.refresh_clicked.connect(self._start_discovery)
        self.discovery_view.connect_clicked.connect(self._handle_connect)
        layout.addWidget(self.discovery_view)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
    def _start_discovery(self):
        """Start the discovery process."""
        logger.debug(f"Starting discovery with filter: {self.model_filter}")
        self.state.discover_instruments(
            model_filter=[self.model_filter] if self.model_filter else None
        )
    
    @Slot(dict)
    def _handle_connect(self, info):
        """Handle instrument connection."""
        self.result_info = info
        self.accept()  # Uses QDialog.accept() method