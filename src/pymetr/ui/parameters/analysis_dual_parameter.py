from typing import Optional, Any, Dict
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QMenu
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QBrush, QPen

from pyqtgraph.parametertree import Parameter
from pymetr.models.device import Device, AcquisitionMode
from pymetr.core.logging import logger
from pymetr.ui.parameters.analysis_parameter import AnalysisParameter

class DualAnalysisParameter(AnalysisParameter):
    """Parameter for dual-trace analysis with trace selection."""
    def __init__(self, **opts):
        super().__init__(**opts)
        self.setupParameters()

    def setupParameters(self):
        # Add trace selection parameters
        traces = [
            {'name': t.name, 'id': t.id}
            for t in self.state.get_models_by_type('Trace')
            if t.visible
        ]

        self.addChild({
            'name': 'Reference Trace',
            'type': 'list',
            'values': [t['name'] for t in traces],
            'value': traces[0]['name'] if traces else '',
            'readonly': True
        })