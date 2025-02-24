"""
Parameter Factory Module

This module provides factory functions to create parameter instances
for specific model types, simplifying parameter creation throughout
the application.
"""

from typing import Optional, Type, Dict
from pathlib import Path
from PySide6.QtGui import QIcon

from pymetr.ui.parameters import *
from pymetr.core.logging import logger


class ParameterFactory:
    """
    Factory for creating parameter objects based on model type.
    
    This factory provides a centralized way to instantiate parameters,
    mapping model types to their corresponding parameter classes.
    """
    
    # Mapping of model types to parameter classes
    # This can be extended as new model types are added
    _parameter_map: Dict[str, Type[ModelParameter]] = {
        'TestScript': TestScriptParameter,
        'TestResult': TestResultParameter,
        'TestSuite': TestSuiteParameter,
        'Plot': PlotParameter,
        'Device': DeviceParameter,
        'DataTable': DataTableParameter,
        'Trace': TraceParameter,
        'Marker': MarkerParameter,
        'Cursor': CursorParameter,
        'Analysis': AnalysisParameter,
        'DualAnalysis': DualAnalysisParameter
    }
    
    # Model type icons - centralized here for consistency
    _model_icons = {
        'TestSuite': 'test_suite.png',
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
        'Analysis': 'analysis.png',
        'DualAnalysis': 'dual_analysis.png',
        'search': 'search.png',
        'folder': 'folder.png',
        'default': 'file_open.png'
    }
    
    # Cache for loaded icons
    _icon_cache: Dict[str, QIcon] = {}
    
    @classmethod
    def register_parameter(cls, model_type: str, parameter_class: Type[ModelParameter]) -> None:
        """
        Register a new parameter class for a model type.
        
        Args:
            model_type: String identifier for the model type
            parameter_class: Parameter class to use for this model type
        """
        cls._parameter_map[model_type] = parameter_class
        logger.debug(f"Registered parameter class {parameter_class.__name__} for model type {model_type}")
    
    @classmethod
    def create_parameter(cls, model) -> Optional[ModelParameter]:
        """
        Create a parameter instance for a given model.
        
        Args:
            model: Model instance to create parameter for
            
        Returns:
            Appropriate parameter instance or None if no matching class found
        """
        model_type = type(model).__name__
        
        # Get parameter class
        parameter_class = cls._parameter_map.get(model_type)
        
        if not parameter_class:
            logger.warning(f"No parameter class registered for model type: {model_type}")
            return None
            
        # Create parameter instance
        try:
            parameter = parameter_class()
            parameter.setupParameters(model)
            return parameter
        except Exception as e:
            logger.error(f"Error creating parameter for {model_type}: {e}")
            return None
    
    @classmethod
    def available_parameter_types(cls) -> Dict[str, Type[ModelParameter]]:
        """
        Get available parameter types.
        
        Returns:
            Dictionary mapping model types to parameter classes
        """
        return cls._parameter_map.copy()
    
    @classmethod
    def get_icon(cls, model_type: str) -> QIcon:
        """
        Get icon for a model type.
        
        Args:
            model_type: Type of model to get icon for
            
        Returns:
            QIcon for the model type, or default icon if not found
        """
        # Load icons if cache is empty
        if not cls._icon_cache:
            cls._preload_icons()
            
        # Return cached icon or default
        return cls._icon_cache.get(model_type, cls._icon_cache.get('default', QIcon()))
    
    @classmethod
    def register_icon(cls, model_type: str, icon_path: str) -> None:
        """
        Register a custom icon for a model type.
        
        Args:
            model_type: Type of model
            icon_path: Path to icon file
        """
        cls._model_icons[model_type] = icon_path
        
        # Clear cache entry to force reload
        if model_type in cls._icon_cache:
            del cls._icon_cache[model_type]
    
    @classmethod
    def _preload_icons(cls) -> None:
        """Preload all icons into cache."""
        try:
            # Find the icons directory
            icons_path = Path(__file__).parent.parent.parent / 'icons'
            
            # If that doesn't exist, try another common location
            if not icons_path.exists():
                icons_path = Path(__file__).parent.parent / 'icons'
                
            logger.debug(f"Loading icons from {icons_path}")
            
            # Load each icon
            for model_type, icon_file in cls._model_icons.items():
                icon_path = str(icons_path / icon_file)
                cls._icon_cache[model_type] = QIcon(icon_path)
                
        except Exception as e:
            logger.error(f"Error preloading icons: {e}")


# Convenience function for creating parameters
def create_parameter_for_model(model) -> Optional[ModelParameter]:
    """
    Create a parameter instance for a given model.
    
    Args:
        model: Model instance to create parameter for
        
    Returns:
        Parameter instance or None if no matching parameter class found
    """
    return ParameterFactory.create_parameter(model)