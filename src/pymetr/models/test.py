# pymetr/models/test.py
from pathlib import Path
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Slot
from pymetr.models.base import BaseModel
from pymetr.core.logging import logger


class TestScript(BaseModel):
    """
    Represents a test script and its execution state.
    Links to TestResults created during execution (if any).
    """
    def __init__(self, script_path: Path, model_id: Optional[str] = None, name: Optional[str] = None):
        # If no name is provided, default to the stem of the script file.
        if name is None:
            name = script_path.stem
        super().__init__(model_id=model_id, name=name)
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
        super().__init__(state=state, name=name, **kwargs)
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
        super().__init__(state=state, name=name, **kwargs)
        self.set_property("status", "Not Run")
        self.set_property("created_time", datetime.now())
        self.set_property("completed_time", None)
        self.set_property("error", None)
        logger.debug(f"TestResult '{self.name}' created with id {self.id}.")

    @property
    def status(self) -> str:
        return self.get_property("status")
    
    @status.setter
    def status(self, value: str):
        allowed = ["Not Run", "Running", "Pass", "Fail", "Error"]
        if value not in allowed:
            raise ValueError(f"Invalid status: {value}")
        prev_status = self.status
        self.set_property("status", value)

        # Update completion time if moving from "Not Run"/"Running" to a final state.
        if prev_status in ["Not Run", "Running"] and value in ["Pass", "Fail", "Error"]:
            self.set_property("completed_time", datetime.now())

    def set_error(self, error_msg: str):
        """Set the error message and update status."""
        self.set_property("error", error_msg)
        self.status = "Error"
