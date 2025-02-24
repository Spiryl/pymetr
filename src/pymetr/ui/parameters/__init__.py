"""
PyMetr Parameter Classes

This module contains parameter widgets for different types of models
in the PyMetr application. Parameters provide a unified interface for
displaying and editing model properties.
"""

# Base parameter classes
from pymetr.ui.parameters.base import (
    ParameterWidget,
    ModelParameterItem,
    ModelParameter
)

# Model-specific parameter classes
from pymetr.ui.parameters.analysis_parameter import (
    AnalysisParameter,
    AnalysisStatusWidget
)
from pymetr.ui.parameters.analysis_dual_parameter import DualAnalysisParameter
from pymetr.ui.parameters.cursor_parameter import (
    CursorParameter,
    CursorParameterItem,
    CursorPreviewWidget,
    CursorLinePreview
)
from pymetr.ui.parameters.data_table_parameter import (
    DataTableParameter,
    DataTableParameterItem,
    DataTableDisplayWidget
)
from pymetr.ui.parameters.device_parameter import (
    DeviceParameter,
    DeviceInfoWidget,
    LEDIndicator
)
from pymetr.ui.parameters.marker_parameter import (
    MarkerParameter,
    MarkerParameterItem,
    MarkerPreviewWidget,
    MarkerSymbolPreview,
    MarkerInfoWidget
)
from pymetr.ui.parameters.plot_parameter import (
    PlotParameter,
    PlotParameterItem,
    PlotInfoWidget,
    ItemCountIcon
)
from pymetr.ui.parameters.test_result_parameter import (
    TestResultParameter,
    TestResultParameterItem,
    ResultStatusWidget
)
from pymetr.ui.parameters.test_script_parameter import (
    TestScriptParameter,
    TestScriptParameterItem,
    TestProgressWidget
)
from pymetr.ui.parameters.test_suite_parameter import (
    TestSuiteParameter,
    TestSuiteParameterItem,
    TestSuiteStatusWidget
)
from pymetr.ui.parameters.trace_parameter import (
    TraceParameter,
    TraceParameterItem,
    TraceInfoWidget,
    TraceStylePreview
)

# Convenience collection of all parameter classes
ALL_PARAMETER_CLASSES = {
    'AnalysisParameter': AnalysisParameter,
    'DualAnalysisParameter': DualAnalysisParameter,
    'CursorParameter': CursorParameter,
    'DataTableParameter': DataTableParameter,
    'DeviceParameter': DeviceParameter,
    'MarkerParameter': MarkerParameter,
    'PlotParameter': PlotParameter,
    'TestResultParameter': TestResultParameter,
    'TestScriptParameter': TestScriptParameter,
    'TestSuiteParameter': TestSuiteParameter,
    'TraceParameter': TraceParameter
}

# Public API
__all__ = [
    # Base classes
    'ParameterWidget',
    'ModelParameterItem',
    'ModelParameter',
    
    # Analysis parameters
    'AnalysisParameter',
    'AnalysisStatusWidget',
    'DualAnalysisParameter',
    
    # Cursor parameters
    'CursorParameter',
    'CursorParameterItem',
    'CursorPreviewWidget',
    'CursorLinePreview',
    
    # Data table parameters
    'DataTableParameter',
    'DataTableParameterItem',
    'DataTableDisplayWidget',
    
    # Device parameters
    'DeviceParameter',
    'DeviceInfoWidget',
    'LEDIndicator',
    
    # Marker parameters
    'MarkerParameter',
    'MarkerParameterItem',
    'MarkerPreviewWidget',
    'MarkerSymbolPreview',
    'MarkerInfoWidget',
    
    # Plot parameters
    'PlotParameter',
    'PlotParameterItem',
    'PlotInfoWidget',
    'ItemCountIcon',
    
    # Test result parameters
    'TestResultParameter',
    'TestResultParameterItem',
    'ResultStatusWidget',
    
    # Test script parameters
    'TestScriptParameter',
    'TestScriptParameterItem',
    'TestProgressWidget',
    
    # Test suite parameters
    'TestSuiteParameter',
    'TestSuiteParameterItem',
    'TestSuiteStatusWidget',
    
    # Trace parameters
    'TraceParameter',
    'TraceParameterItem',
    'TraceInfoWidget',
    'TraceStylePreview',
    
    # Collections
    'ALL_PARAMETER_CLASSES'
]