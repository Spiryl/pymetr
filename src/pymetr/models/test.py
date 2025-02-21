# pymetr/models/test.py
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

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


class RunConfig(BaseModel):
    """
    Defines a configuration of scripts to run and their order.
    """
    def __init__(self, **kwargs):
        super().__init__("runconfig", **kwargs)
        
        # Initialize properties
        self.set_property('name', kwargs.get('name', 'Default Config'))
        self.set_property('description', kwargs.get('description', ''))
        self.set_property('is_default', kwargs.get('is_default', False))
        
        # Script execution map: script_id -> order
        self._script_map: Dict[str, int] = {}
    
    def add_script(self, script_id: str, order: int):
        """Add script to this configuration."""
        self._script_map[script_id] = order
    
    def remove_script(self, script_id: str):
        """Remove script from configuration."""
        if script_id in self._script_map:
            del self._script_map[script_id]
    
    def get_execution_order(self) -> List[str]:
        """Get script IDs in execution order."""
        return [
            script_id for script_id, _ in 
            sorted(self._script_map.items(), key=lambda x: x[1])
        ]
    
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
        self.set_property('status', 'READY')
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
        allowed = ['READY', 'RUNNING', 'COMPLETE', 'ERROR', 'STOPPED', 'PASS', 'FAIL']
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

class TestSuite(BaseModel):
    """
    Container for test scripts and their execution configurations.
    Scripts can be added/removed dynamically.
    """
    def __init__(self, model_id: Optional[str] = None, name: Optional[str] = None):
        super().__init__(model_type='TestSuite', model_id=model_id, name=name)
        
        # Initialize with default properties
        self.set_property('status', TestStatus.READY.name)
        self.set_property('failure_behavior', 'stop')  # or 'continue'
        
    def add_script(self, script: TestScript):
        """Add a test script to this suite."""
        self.add_child(script)
        
    def remove_script(self, script_id: str):
        """Remove a script from this suite."""
        if self.state:
            self.state.remove_model(script_id)
            
    def get_scripts(self) -> List[TestScript]:
        """Get all test scripts in this suite."""
        return [
            model for model in self.get_children()
            if isinstance(model, TestScript)
        ]
    
    def get_run_configs(self) -> List[RunConfig]:
        """Get all run configurations."""
        return [
            model for model in self.get_children()
            if isinstance(model, RunConfig)
        ]
    
    def get_default_config(self) -> Optional[RunConfig]:
        """Get default run configuration."""
        for config in self.get_run_configs():
            if config.get_property('is_default', False):
                return config
        return None

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
    def status(self) -> Optional[ResultStatus]:
        """Get result status. Returns None if not reported."""
        status_str = self.get_property('status', None)
        if status_str is None:
            return None
        try:
            return ResultStatus[status_str.upper()]
        except KeyError:
            return None

    @status.setter
    def status(self, value: Optional[ResultStatus]):
        """Set result status. Allow None to indicate not reported."""
        if value is None:
            self.set_property('status', None)
        else:
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
            # # If child has another parent, unlink it first.
            # if self.state:
            #     current_parent = self.state.get_parent(child.id)
            #     if current_parent and current_parent.id != self.id:
            #         self.state.unlink_models(current_parent.id, child.id)
            self.add_child(child)
