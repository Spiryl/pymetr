# pymetr/models/test.py
from pathlib import Path
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Slot
from pymetr.models.base import BaseModel
from pymetr.core.logging import logger

from enum import Enum, auto

class TestStatus(Enum):
    """
    Test script status states.
    
    Flow:
    READY -> RUNNING -> (PASS | FAIL | ERROR | COMPLETE)
    
    READY: Initial state, script can be run
    RUNNING: Script is currently executing
    PASS: All test results passed
    FAIL: At least one test result failed
    ERROR: Script execution error
    COMPLETE: Script completed without any test results
    """
    READY = auto()      # Initial state
    RUNNING = auto()    # Currently executing
    PASS = auto()       # All results passed
    FAIL = auto()       # At least one result failed
    ERROR = auto()      # Script error
    COMPLETE = auto()   # Completed without results

class ResultStatus(Enum):
    """
    Test result status states.
    
    PASS: Test passed its criteria
    FAIL: Test failed its criteria
    ERROR: Error during test execution
    """
    PASS = auto()
    FAIL = auto()
    ERROR = auto()

    @classmethod
    def from_bool(cls, success: bool) -> 'ResultStatus':
        """Convert a boolean success value to ResultStatus."""
        return cls.PASS if success else cls.FAIL
    
class TestScript(BaseModel):
    """
    Represents a test script and its execution state.
    Links to TestResults created during execution (if any).
    """
    def __init__(self, script_path: Path, model_id: Optional[str] = None, name: Optional[str] = None):
        # If no name is provided, default to the stem of the script file.
        if name is None:
            name = script_path.stem

        super().__init__(model_type='TestScript', model_id=model_id, name=name)
        
        self.set_property('script_path', script_path)
        self.set_property('status', 'Not Run')
        self.set_property('start_time', None)
        self.set_property('elapsed_time', 0)
        self.set_property('progress', 0.0)
        # Now, the 'name' property is automatically set in BaseModel.

    @property
    def script_path(self) -> Path:
        return self.get_property('script_path')
        
    @property
    def status(self) -> str:
        return self.get_property('status')
        
    @status.setter
    def status(self, value: str):
        allowed = ['Not Run', 'Running', 'Complete', 'Error', 'Stopped']
        if value not in allowed:
            raise ValueError(f"Invalid status: {value}")
        self.set_property('status', value)
        
    @property
    def start_time(self) -> Optional[datetime]:
        return self.get_property('start_time')
        
    @property
    def elapsed_time(self) -> int:
        return self.get_property('elapsed_time')
        
    @elapsed_time.setter
    def elapsed_time(self, value: int):
        self.set_property('elapsed_time', value)
        
    @property
    def progress(self) -> float:
        return self.get_property('progress')
        
    @progress.setter
    def progress(self, value: float):
        if not 0 <= value <= 100:
            raise ValueError("Progress must be between 0 and 100.")
        self.set_property('progress', value)
        
    @Slot()
    def on_started(self):
        """Handle script start."""
        self.set_property('start_time', datetime.now())
        self.status = 'Running'
        self.progress = 0.0
        logger.info(f"Script {self.name} started.")
        
    @Slot(bool, str)
    def on_finished(self, success: bool, error_msg: str = ""):
        """Handle script completion."""
        if success:
            self.status = 'Complete'
            self.progress = 100.0
        else:
            self.status = 'Error'
            self.set_property('error', error_msg)
        logger.info(f"Script {self.name} finished: {self.status}")


class TestGroup(BaseModel):
    """
    A generic container model that can hold child data models.
    Users can add children (plots, measurements, etc.) to organize data.
    """
    def __init__(self, state=None, name="", **kwargs):
        # Generate a unique name if necessary.
        if state:
            name = self._get_unique_name(state, name)
        
        # Pass model_type explicitly and remove it from kwargs if present
        kwargs.pop('model_type', None)
        super().__init__(model_type='TestGroup', state=state, name=name, **kwargs)
        
        logger.debug(f"TestGroup '{self.name}' created with id {self.id}.")

    def _get_unique_name(self, state, base_name: str) -> str:
        """Generate a unique name by appending an incrementing number if needed."""
        existing_groups = state.get_models_by_type(TestGroup)
        existing_names = {group.get_property("name") for group in existing_groups}
        
        if base_name not in existing_names:
            return base_name
            
        counter = 1
        while f"{base_name}_{counter}" in existing_names:
            counter += 1
        return f"{base_name}_{counter}"

    def add(self, child_or_children):
        """
        Add one or more child models to this group.
        If a child is already linked to another parent, it is re-parented here.
        """
        if not isinstance(child_or_children, list):
            child_or_children = [child_or_children]
        for child in child_or_children:
            # If child has another parent, unlink it first.
            if self.state:
                current_parent = self.state.get_parent(child.id)
                if current_parent and current_parent.id != self.id:
                    self.state.unlink_models(current_parent.id, child.id)
            self.add_child(child)


class TestResult(TestGroup):
    """
    A specialized container for test results. Inherits from TestGroup so it
    can contain child models and adds status, timestamps, and error handling.
    """
    def __init__(self, state=None, name="", **kwargs):
        # Remove model_type from kwargs if present
        kwargs.pop('model_type', None)
        super().__init__(state=state, name=name, **kwargs)
        
        # Specify model type as 'TestResult' 
        self.model_type = 'TestResult'
        
        self.set_property("created_time", datetime.now())
        self.set_property("completed_time", None)
        
        logger.debug(f"TestResult '{self.name}' created with id {self.id}.")

    @property
    def progress(self) -> float:
        """Get result progress."""
        return self.get_property('progress', 0.0)
    
    @progress.setter 
    def progress(self, value: float):
        """Set result progress."""
        value = max(0.0, min(100.0, float(value)))
        self.set_property('progress', value)
    
    @property
    def status(self) -> ResultStatus:
        """Get result status."""
        status_str = self.get_property('status', ResultStatus.PASS.name)
        return ResultStatus[status_str]
    
    @status.setter
    def status(self, value: ResultStatus):
        """Set result status."""
        if isinstance(value, str):
            value = ResultStatus[value.upper()]
        self.set_property('status', value.name)

    def add(self, child_or_children):
        """
        Add one or more child models to this group.
        If a child is already linked to another parent, it is re-parented here.
        """
        if not isinstance(child_or_children, list):
            child_or_children = [child_or_children]
        for child in child_or_children:
            # If child has another parent, unlink it first.
            if self.state:
                current_parent = self.state.get_parent(child.id)
                if current_parent and current_parent.id != self.id:
                    self.state.unlink_models(current_parent.id, child.id)
            self.add_child(child)
