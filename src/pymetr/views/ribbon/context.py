# src/pymetr/views/ribbon/context.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from pymetr.state import ApplicationState

class ActionCategory(Enum):
    """Categories for ribbon actions."""
    FILE = auto()
    EDIT = auto()
    RUN = auto()
    ANALYZE = auto()
    PLOT = auto()
    DATA = auto()

@dataclass
class RibbonAction:
    """Represents a single ribbon action."""
    id: str
    name: str
    category: ActionCategory
    icon: str
    enabled: bool = True
    menu_items: Dict[str, tuple[str, callable]] = None
    tooltip: str = ""

class RibbonContext(ABC):
    """Base class for ribbon contexts."""
    def __init__(self, state: ApplicationState):
        self.state = state
        
    @abstractmethod
    def get_actions(self) -> List[RibbonAction]:
        """Get available actions for this context."""
        pass
    
    @abstractmethod
    def get_title(self) -> str:
        """Get context title for ribbon."""
        pass
    
    def can_execute(self, action_id: str) -> bool:
        """Check if an action can be executed."""
        return True

class DefaultContext(RibbonContext):
    """Default context when no model is selected."""
    def get_actions(self) -> List[RibbonAction]:
        # Return empty list since standard buttons are handled by permanent groups
        return []
    
    def get_title(self) -> str:
        return "Home"

class ScriptContext(RibbonContext):
    """Context for test script editing."""
    def get_actions(self) -> List[RibbonAction]:
        # Save actions
        save_menu_items = {
            "Save": ("save.png", lambda: self.state.actions.execute("save_script")),
            "Save As...": ("save_as.png", lambda: self.state.actions.execute("save_script_as"))
        }
        
        return [
            RibbonAction(
                id="save",
                name="Save",
                category=ActionCategory.FILE,
                icon="save.png",
                menu_items=save_menu_items,
                tooltip="Save script"
            ),
            RibbonAction(
                id="run_script",  # Changed to match command ID
                name="Run",
                category=ActionCategory.RUN,
                icon="run.png",
                tooltip="Run test script"
            ),
            RibbonAction(
                id="stop_script",  # Added for consistency
                name="Stop",
                category=ActionCategory.RUN,
                icon="stop.png",
                enabled=False,
                tooltip="Stop test execution"
            )
        ]
    
    def get_title(self) -> str:
        return "Script Editor"
    
    def can_execute(self, action_id: str) -> bool:
        """Additional validation for script actions."""
        if action_id == "run_script":
            # Get current active model
            model = self.state.get_active_model()
            return model and hasattr(model, 'script_path') and model.script_path.exists()
        return super().can_execute(action_id)
    
class PlotContext(RibbonContext):
    """Context for plot editing."""
    def get_actions(self) -> List[RibbonAction]:
        return [
            RibbonAction(
                id="autorange",
                name="Auto Range",
                category=ActionCategory.PLOT,
                icon="autorange.png",
                tooltip="Auto-scale plot axes"
            ),
            RibbonAction(
                id="roi",
                name="ROI",
                category=ActionCategory.PLOT,
                icon="roi.png",
                tooltip="Toggle region of interest"
            ),
            RibbonAction(
                id="export_plot",
                name="Export",
                category=ActionCategory.FILE,
                icon="export.png",
                tooltip="Export plot as image"
            )
        ]
    
    def get_title(self) -> str:
        return "Plot Editor"
    
class DataTableContext(RibbonContext):
    """Context for data table manipulation."""
    def get_actions(self) -> List[RibbonAction]:
        export_menu_items = {
            "Export CSV": ("csv.png", lambda: self.state.export_data("csv")),
            "Export Excel": ("excel.png", lambda: self.state.export_data("excel")),
            "Export JSON": ("json.png", lambda: self.state.export_data("json"))
        }

        return [
            RibbonAction(
                id="export_data",
                name="Export",
                category=ActionCategory.DATA,
                icon="export.png",
                menu_items=export_menu_items,
                tooltip="Export data table"
            ),
            RibbonAction(
                id="sort_data",
                name="Sort",
                category=ActionCategory.DATA,
                icon="sort.png",
                tooltip="Sort data table"
            ),
            RibbonAction(
                id="filter_data",
                name="Filter",
                category=ActionCategory.DATA,
                icon="filter.png",
                tooltip="Filter data table"
            )
        ]
    
    def get_title(self) -> str:
        return "Data Table"