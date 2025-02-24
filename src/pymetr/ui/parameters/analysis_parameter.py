from typing import Optional, Any, Dict
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QMenu
)
from PySide6.QtCore import Qt

from pymetr.core.logging import logger
from pymetr.ui.parameters.base import  ModelParameter,  ParameterWidget

class AnalysisParameter(ModelParameter):
    """Base parameter for analysis models."""
    
    ICONS = {
        'Analysis': 'science',  # Base analysis icon
        'TimeMeasurement': 'timer',  # For timing measurements
        'PeakSearch': 'signal_cellular_4_bar',  # For peak detection
        'FFT': 'wave', # For FFT analysis
        'CrossSpectrum': 'compare_arrows',  # For cross-spectral
        'PeriodMeasurement': 'repeat',  # For period/frequency
        'PeakToPeak': 'height',  # For amplitude measurements
        'EdgeMeasurement': 'trending_up',  # For edge timing
        'TraceMath': 'functions',  # For trace math operations
    }

    def __init__(self, **opts):
        opts['type'] = 'analysis'
        super().__init__(**opts)
        self.can_export = True  # Allow analysis results to be exported

class AnalysisStatusWidget(ParameterWidget):
    """Widget showing analysis result/status."""
    def __init__(self, param, parent=None):
        super().__init__(param, parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Result label
        self.result_label = QLabel()
        self.result_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Status indicator (could be colored dot/icon)
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(8, 8)
        self.status_indicator.setStyleSheet(
            "background-color: #4CAF50; border-radius: 4px;"
        )
        
        layout.addWidget(self.status_indicator)
        layout.addWidget(self.result_label)
        layout.addStretch()

    def _process_pending_update(self):
        """Update display with latest results."""
        pass