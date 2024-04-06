import logging
logger = logging.getLogger()
import os
os.environ['PYQTGRAPH_QT_LIB'] = 'PySide6'

import importlib.util
from pyqtgraph.parametertree import Parameter, ParameterTree

from pyqtgraph.Qt import QtCore, QtGui
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QDockWidget, QPushButton, QWidget, QFileDialog 

from pymetr.instrument import Instrument
from pymetr.application.instrument_factory import InstrumentFactory
from pymetr.application.trace_data_fetcher_thread import TraceDataFetcherThread

class TraceDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Trace Parameters", parent)
        self.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)

        self.dockLayout = QVBoxLayout()
        self.dockWidget = QWidget()
        self.dockWidget.setLayout(self.dockLayout)

        self.parameters = Parameter.create(name='Trace Parameters', type='group', children=[]) 
        self.parameterTree = ParameterTree()
        self.dockLayout.addWidget(self.parameterTree)

        self.setWidget(self.dockWidget)

    def update_trace_parameters(self, trace_data):
        parameters = []
        for trace_id, trace_info in trace_data.items():
            trace_params = [
                dict(name='label', type='str', value=trace_info.get('label', f'Trace {trace_id}')),
                dict(name='color', type='color', value=trace_info.get('color', '#FFFFFF')),
                dict(name='visible', type='bool', value=trace_info.get('visible', True)),
                dict(name='style', type='list', limits=['solid', 'dash', 'dot'], value=trace_info.get('style', 'solid')),
                dict(name='glow', type='bool', value=trace_info.get('glow', False)),
            ]
            parameters.append(dict(name=trace_id, type='group', children=trace_params))
        self.parameters = Parameter.create(name='Trace Parameters', type='group', children=parameters)
        self.parameterTree.setParameters(self.parameters, showTop=False)

    def get_trace_parameters(self):
        trace_params = {}
        for trace_param in self.parameterTree.topLevelItem(0).children():
            trace_id = trace_param.param('name').value()
            trace_params[trace_id] = {
                'label': trace_param.param('label').value(),
                'color': trace_param.param('color').value(),
                'visible': trace_param.param('visible').value(),
                'style': trace_param.param('style').value(),
                'glow': trace_param.param('glow').value(),
            }
        return trace_params