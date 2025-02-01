# src/pymetr/views/ribbon/context.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum, auto

from pymetr.state import ApplicationState

class ActionCategory(Enum):
    """Categories for ribbon actions"""
    FILE = auto()
    EDIT = auto()
    RUN = auto()
    ANALYZE = auto()
    PLOT = auto()
    INSTRUMENT = auto()

@dataclass
class RibbonAction:
    """Represents a single ribbon action"""
    id: str
    name: str
    category: ActionCategory
    icon: str
    enabled: bool = True
    checkable: bool = False
    checked: bool = False
    tooltip: str = ""

class RibbonContext(ABC):
    """Base class for ribbon contexts"""
    def __init__(self, state: 'ApplicationState'):
        self.state = state
        
    @abstractmethod
    def get_actions(self) -> List[RibbonAction]:
        """Get available actions for this context"""
        pass
    
    @abstractmethod
    def get_title(self) -> str:
        """Get context title for ribbon"""
        pass
    
    def can_execute(self, action_id: str) -> bool:
        """Check if an action can be executed"""
        return True

class DefaultContext(RibbonContext):
    """Default context when no model is selected"""
    def get_actions(self) -> List[RibbonAction]:
        return [
            RibbonAction(
                id="new_script",
                name="New Script",
                category=ActionCategory.FILE,
                icon="📝",
                tooltip="Create a new test script"
            ),
            RibbonAction(
                id="new_instrument",
                name="New Instrument",
                category=ActionCategory.FILE,
                icon="🔧",
                tooltip="Configure a new instrument"
            )
        ]
    
    def get_title(self) -> str:
        return "Home"

class ScriptContext(RibbonContext):
    """Context for test script editing"""
    def get_actions(self) -> List[RibbonAction]:
        model = self.state.get_active_model()
        is_running = model and model.get_property('running', False)
        
        return [
            RibbonAction(
                id="run_script",
                name="Run",
                category=ActionCategory.RUN,
                icon="▶️",
                enabled=not is_running,
                tooltip="Run test script"
            ),
            RibbonAction(
                id="stop_script",
                name="Stop",
                category=ActionCategory.RUN,
                icon="⏹️",
                enabled=is_running,
                tooltip="Stop test execution"
            ),
            RibbonAction(
                id="save_script",
                name="Save",
                category=ActionCategory.FILE,
                icon="💾",
                tooltip="Save script changes"
            )
        ]
    
    def get_title(self) -> str:
        return "Script Editor"

class PlotContext(RibbonContext):
    """Context for plot editing"""
    def get_actions(self) -> List[RibbonAction]:
        return [
            RibbonAction(
                id="add_trace",
                name="Add Trace",
                category=ActionCategory.PLOT,
                icon="📈",
                tooltip="Add new trace to plot"
            ),
            RibbonAction(
                id="autorange",
                name="Auto Range",
                category=ActionCategory.PLOT,
                icon="🔍",
                tooltip="Auto-scale plot axes"
            ),
            RibbonAction(
                id="export_plot",
                name="Export",
                category=ActionCategory.FILE,
                icon="📤",
                tooltip="Export plot as image"
            )
        ]
    
    def get_title(self) -> str:
        return "Plot Editor"