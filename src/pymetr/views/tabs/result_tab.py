# views/tabs/result_tab.py
from PySide6.QtWidgets import QVBoxLayout, QToolBar, QComboBox, QLabel, QSizePolicy
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Slot

from pymetr.views.tabs.base import BaseTab
from pymetr.views.widgets.result_view import ResultView, LayoutMode
from pymetr.core.logging import logger

class ResultTab(BaseTab):
    """Full-featured result tab with layout controls."""
    
    def __init__(self, state, model_id: str, parent=None):
        super().__init__(state, model_id, parent)
        
    def _setup_ui(self):
        """Initialize the tab UI components."""
        # Add layout controls to the toolbar
        self.toolbar.addWidget(QLabel("Layout:"))
        self.layout_combo = QComboBox()
        self.layout_combo.addItems([
            "Vertical Stack",
            "2 Columns",
            "3 Columns",
            "Auto Grid"
        ])
        # Set the default to Auto Grid (index 3) to match ResultView's default
        self.layout_combo.setCurrentIndex(3)
        self.layout_combo.currentIndexChanged.connect(self._handle_layout_changed)
        self.toolbar.addWidget(self.layout_combo)
        
        self.toolbar.addSeparator()
        
        # Export action
        self.export_action = QAction("Export Results...", self)
        self.export_action.triggered.connect(self._handle_export)
        self.toolbar.addAction(self.export_action)

        # Set up content area with ResultView
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Result view
        self.result_view = ResultView(self.state, self.model_id, self)
        self.result_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_layout.addWidget(self.result_view)

    def _handle_layout_changed(self, index: int):
        """Change result layout mode."""
        mode = [
            LayoutMode.Vertical,
            LayoutMode.Grid2,
            LayoutMode.Grid3,
            LayoutMode.GridAuto
        ][index]
        self.result_view.set_layout_mode(mode)

    def _handle_export(self):
        """Handle export action."""
        # TODO: Implement result export
        pass

    def set_model(self, model_id: str):
        """Override to ensure ResultView gets model updates."""
        super().set_model(model_id)
        if hasattr(self, 'result_view'):
            self.result_view.set_model(model_id)