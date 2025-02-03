# src/pymetr/models/test_script.py
from pathlib import Path
from typing import Dict, List, Optional, Any
from PySide6.QtCore import QObject, Signal

from ..logging import logger
from .base import BaseModel
from .test_result import TestResult

class TestScript(BaseModel, QObject):
    """
    A test container that can hold multiple results.
    
    Signals:
        progress_changed(str, float, str): Emitted when progress changes (test_id, percent, message)
        status_changed(str, str): Emitted when status changes (test_id, new_status)
        result_added(str, str): Emitted when result is added (test_id, result_id)
        result_removed(str, str): Emitted when result is removed (test_id, result_id)
        metadata_changed(str): Emitted when metadata changes (test_id)
    """

    progress_changed = Signal(str, float, str)  # test_id, percent, message
    status_changed = Signal(str, str)  # test_id, status
    result_added = Signal(str, str)  # test_id, result_id
    result_removed = Signal(str, str)  # test_id, result_id
    metadata_changed = Signal(str)  # test_id

    def __init__(self, name: str, script_path: Optional[Path] = None, id: Optional[str] = None):
        BaseModel.__init__(self, id)
        QObject.__init__(self)
        
        self.name = name
        self.script_path = script_path
        self.results: Dict[str, TestResult] = {}
        self.required_instruments: List[Dict[str, str]] = []
        self.metadata: Dict[str, Any] = {}
        
        self._progress = 0.0
        self._progress_message = ""
        self._status = "Not Run"

        logger.debug(f"TestScript.__init__: Created TestScript '{self.name}' with ID={self.id}")

    # ... rest of TestScript implementation stays the same ...

    @property
    def progress(self) -> float:
        return self._progress

    @progress.setter
    def progress(self, value: float):
        old_progress = self._progress
        self._progress = max(0.0, min(100.0, value))
        logger.debug(f"TestScript ID={self.id}: Progress changed from {old_progress} to {self._progress}")
        self.progress_changed.emit(self.id, self._progress, self._progress_message)

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, value: str):
        old_status = self._status
        self._status = value
        logger.debug(f"TestScript ID={self.id}: Status changed from '{old_status}' to '{value}'")
        self.status_changed.emit(self.id, value)

    def add_result(self, result: TestResult):
        """Add a new result to the test."""
        self.results[result.id] = result
        logger.debug(f"TestScript ID={self.id}: Added TestResult ID={result.id}")
        self.result_added.emit(self.id, result.id)
        self.calculate_aggregate_status()

    def remove_result(self, result_id: str):
        """Remove a result by ID."""
        if result_id in self.results:
            del self.results[result_id]
            logger.debug(f"TestScript ID={self.id}: Removed TestResult ID={result_id}")
            self.result_removed.emit(self.id, result_id)
            self.calculate_aggregate_status()

    def update_metadata(self, metadata: Dict[str, Any]):
        """Update metadata dictionary."""
        self.metadata.update(metadata)
        logger.debug(f"TestScript ID={self.id}: Metadata updated")
        self.metadata_changed.emit(self.id)

    def calculate_aggregate_status(self) -> str:
        """Calculate and update the aggregate status based on all results."""
        if not self.results:
            self._status = "Not Run"
            return self._status

        statuses = [result.status for result in self.results.values()]
        logger.debug(f"TestScript ID={self.id}: Calculating aggregate status from {statuses}")

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

        if new_status != self._status:
            self._status = new_status
            self.status_changed.emit(self.id, new_status)

        return self._status

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "script_path": str(self.script_path) if self.script_path else None,
            "metadata": self.metadata,
            "results": {rid: res.to_dict() for rid, res in self.results.items()},
            "required_instruments": self.required_instruments,
            "progress": self.progress,
            "progress_message": self._progress_message,
            "status": self.status
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TestScript':
        """Create from dictionary."""
        test = TestScript(
            name=data["name"],
            script_path=Path(data["script_path"]) if data.get("script_path") else None,
            id=data.get("id")
        )
        test.metadata = data.get("metadata", {})
        test.required_instruments = data.get("required_instruments", [])
        test._progress = data.get("progress", 0.0)
        test._progress_message = data.get("progress_message", "")
        test._status = data.get("status", "Not Run")
        
        for rid, rdata in data.get("results", {}).items():
            result = TestResult.from_dict(rdata)
            test.add_result(result)
            
        return test