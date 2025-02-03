# app/models/test_suite.py

from typing import Dict, Optional, Any
from PySide6.QtCore import QObject, Signal

from ..logging import logger
from .base import BaseModel
from .test_script import TestScript
from .test_result import TestResult


class TestSuite(BaseModel, QObject):
    """
    A container for multiple related tests.
    
    Signals:
        status_changed(str, str): Emitted when status changes (suite_id, new_status)
        test_added(str, str): Emitted when test is added (suite_id, test_id)
        test_removed(str, str): Emitted when test is removed (suite_id, test_id)
        result_added(str, str, str): Emitted when result is added (suite_id, test_id, result_id)
        metadata_changed(str): Emitted when metadata changes (suite_id)
    """

    status_changed = Signal(str, str)  # suite_id, new_status
    test_added = Signal(str, str)  # suite_id, test_id
    test_removed = Signal(str, str)  # suite_id, test_id
    result_added = Signal(str, str, str)  # suite_id, test_id, result_id
    metadata_changed = Signal(str)  # suite_id

    def __init__(self, name: str, id: Optional[str] = None):
        BaseModel.__init__(self, id)
        QObject.__init__(self)
        
        self.name = name
        self.tests: Dict[str, TestScript] = {}
        self.metadata: Dict[str, Any] = {}
        self._status = "Not Run"

        logger.debug(f"TestSuite.__init__: Created TestSuite '{self.name}' with ID={self.id}")

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, value: str):
        if value != self._status:
            old_status = self._status
            self._status = value
            logger.debug(f"TestSuite ID={self.id}: Status changed from '{old_status}' to '{value}'")
            self.status_changed.emit(self.id, value)

    def add_test(self, test: TestScript):
        """Add a new test to the suite."""
        self.tests[test.id] = test
        logger.debug(f"TestSuite ID={self.id}: Added TestScript ID={test.id}")
        self.test_added.emit(self.id, test.id)
        self.calculate_aggregate_status()

        # Connect test signals
        test.status_changed.connect(lambda t_id, status: self._handle_test_status_changed(t_id, status))
        test.result_added.connect(lambda t_id, r_id: self._handle_test_result_added(t_id, r_id))

    def remove_test(self, test_id: str):
        """Remove a test from the suite."""
        if test_id in self.tests:
            del self.tests[test_id]
            logger.debug(f"TestSuite ID={self.id}: Removed TestScript ID={test_id}")
            self.test_removed.emit(self.id, test_id)
            self.calculate_aggregate_status()

    def _handle_test_status_changed(self, test_id: str, status: str):
        """Handle status changes from contained tests."""
        logger.debug(f"TestSuite ID={self.id}: Test {test_id} status changed to '{status}'")
        self.calculate_aggregate_status()

    def _handle_test_result_added(self, test_id: str, result_id: str):
        """Handle new results from contained tests."""
        logger.debug(f"TestSuite ID={self.id}: Test {test_id} added result {result_id}")
        self.result_added.emit(self.id, test_id, result_id)

    def update_metadata(self, metadata: Dict[str, Any]):
        """Update metadata dictionary."""
        self.metadata.update(metadata)
        logger.debug(f"TestSuite ID={self.id}: Metadata updated")
        self.metadata_changed.emit(self.id)

    def calculate_aggregate_status(self) -> str:
        """Calculate and update the aggregate status based on all tests."""
        if not self.tests:
            self.status = "Not Run"
            return self.status

        statuses = [test.status for test in self.tests.values()]
        logger.debug(f"TestSuite ID={self.id}: Calculating aggregate status from {statuses}")

        if any(status == "Error" for status in statuses):
            new_status = "Error"
        elif any(status == "Fail" for status in statuses):
            new_status = "Fail"
        elif all(status == "Pass" for status in statuses):
            new_status = "Pass"
        elif all(status in ("Pass", "Complete") for status in statuses):
            new_status = "Complete"
        else:
            new_status = "Not Run"

        self.status = new_status
        return self.status

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "metadata": self.metadata,
            "tests": {tid: test.to_dict() for tid, test in self.tests.items()},
            "status": self.status
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TestSuite':
        """Create from dictionary."""
        suite = TestSuite(
            name=data["name"],
            id=data.get("id")
        )
        suite.metadata = data.get("metadata", {})
        suite._status = data.get("status", "Not Run")
        
        # Load tests
        for tid, tdata in data.get("tests", {}).items():
            test = TestScript.from_dict(tdata)
            suite.add_test(test)
        
        return suite