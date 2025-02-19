from typing import Optional, List
from datetime import datetime
from pymetr.core.logging import logger
from pymetr.models.test import TestScript, TestStatus, TestResult,  ResultStatus, TestGroup
from pymetr.models.plot import Plot
from pymetr.models.trace import Trace
from pymetr.models.marker import Marker
from pymetr.models.cursor import Cursor
from pymetr.models.table import DataTable
    
class TestContext:
    """
    Context object provided to test scripts, encapsulating all allowed operations
    and maintaining script state.
    """
    def __init__(self, script: TestScript, engine):
        self.script = script
        self._engine = engine
        self._state = engine.state
        self.start_time = datetime.now()
        
        # Initialize script status
        self.script.set_property('status', TestStatus.READY)
        self.script.set_property('progress', 0.0)
        
    @property
    def progress(self) -> float:
        """Get current progress."""
        return self.script.get_property('progress', 0.0)
    
    @progress.setter
    def progress(self, value: float):
        """
        Set direct script progress. This will be averaged with result progress
        if results exist.
        """
        value = max(0.0, min(100.0, float(value)))
        self.script.set_property('progress', value)
        
        # If no results exist, this is the only progress
        if not self._get_test_results():
            return
            
        # Otherwise, trigger progress aggregation
        self._update_aggregate_progress()

    @property
    def status(self) -> TestStatus:
        """Get current test status."""
        status_str = self.script.get_property('status', TestStatus.READY.name)
        return TestStatus[status_str]

    @status.setter
    def status(self, value: TestStatus):
        """Set test status."""
        if isinstance(value, str):
            value = TestStatus[value.upper()]
        self.script.set_property('status', value.name)

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return (datetime.now() - self.start_time).total_seconds()
    
    def create_result(self, name: str) -> TestResult:
        """Create a test result with progress tracking."""
        result = self._state.create_model(TestResult, name=name)
        self._state.link_models(self.script.id, result.id)
        
        # Initialize result properties
        result.set_property('status', ResultStatus.PASS.name)
        result.set_property('progress', 0.0)
        
        # Update script progress
        self._update_aggregate_progress()
        
        return result
    
    def create_group(self, name: str) -> TestGroup:
        """Create a result group for organizing results."""
        group = self._state.create_model(TestGroup, name=name)
        self._state.link_models(self.script.id, group.id)
        return group
    
    def create_plot(self, title: str) -> Plot:
        """Create a plot linked to this test."""
        plot = self._state.create_model(Plot, title=title)
        self._state.link_models(self.script.id, plot.id)
        return plot
    
    def create_trace(self, name: str, x_data, y_data=None, **kwargs) -> Trace:
        """
        Create a trace linked to this test.
        If y_data is None and x_data is a tuple of two arrays, then unpack them.
        """
        if y_data is None and isinstance(x_data, tuple) and len(x_data) == 2:
            x_data, y_data = x_data
        trace = self._state.create_model(Trace, name=name, x_data=x_data, y_data=y_data, **kwargs)
        self._state.link_models(self.script.id, trace.id)
        return trace
    
    def create_table(self, title: str) -> DataTable:
        """Create a table linked to this test."""
        table = self._state.create_model(DataTable, title=title)
        self._state.link_models(self.script.id, table.id)
        return table

    def create_marker(self, name: str, **kwargs) -> Marker:
        """Create a marker linked to this test."""
        marker = self._state.create_model(Marker, name=name, **kwargs)
        self._state.link_models(self.script.id, marker.id)
        return marker

    def create_cursor(self, name: str, **kwargs) -> Cursor:
        """Create a cursor linked to this test."""
        cursor = self._state.create_model(Cursor, name=name, **kwargs)
        self._state.link_models(self.script.id, cursor.id)
        return cursor

    def get_result(self, name: str) -> Optional[TestResult]:
        """Find a result by name."""
        for model in self._state.get_children(self.script.id):
            if isinstance(model, TestResult) and model.get_property('name') == name:
                return model
        return None

    def get_plot(self, title: str) -> Optional[Plot]:
        """Find a plot by title."""
        for model in self._state.get_children(self.script.id):
            if isinstance(model, Plot) and model.get_property('title') == title:
                return model
        return None

    def wait(self, milliseconds: int):
        """Wait without blocking GUI."""
        self._engine.wait(milliseconds)

    # Internal methods
    def _get_test_results(self) -> List[TestResult]:
        """Get all test results created by this script."""
        return [
            model for model in self._state.get_children(self.script.id)
            if isinstance(model, TestResult)
        ]
    
    def _determine_final_status(self) -> TestStatus:
        """Determine final script status based on results."""
        results = self._get_test_results()
        
        if not results:
            return TestStatus.COMPLETE
            
        # Check all result statuses
        has_fails = any(
            result.get_property('status') == ResultStatus.FAIL.name
            for result in results
        )
        
        if has_fails:
            return TestStatus.FAIL
            
        return TestStatus.PASS
    
    def _update_aggregate_progress(self):
        """
        Update script progress based on results.
        Averages progress of all results, or uses script's direct progress
        if no results exist.
        """
        results = self._get_test_results()
        if not results:
            return  # Keep current script progress
            
        # Calculate average progress from all results
        total_progress = sum(
            result.get_property('progress', 0.0)
            for result in results
        )
        avg_progress = total_progress / len(results)
        
        # Update script progress
        self.script.set_property('progress', avg_progress)
    
    def on_script_start(self):
        """Called by engine when script starts."""
        self.script.set_property('status', TestStatus.RUNNING)
        self.start_time = datetime.now()
    
    def on_script_error(self, error: Exception):
        """Called by engine on script error."""
        self.script.set_property('status', TestStatus.ERROR)
        self.script.set_property('error', str(error))
    
    def on_script_complete(self):
        """Called by engine when script finishes."""
        try:
            final_status = self._determine_final_status()
            self.script.set_property('status', final_status)
            self.script.set_property('progress', 100.0)
        except Exception as e:
            logger.error(f"Error determining final status: {e}")
            self.script.set_property('status', TestStatus.ERROR)
            self.script.set_property('error', str(e))
    