# app/models/test_result.py

from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
from PySide6.QtCore import QObject, Signal, QTimer
from datetime import datetime

from ..logging import logger
from .base import BaseModel
from .plot import Plot
from .trace import Trace


class TestResult(BaseModel, QObject):
    """
    A test execution result with optional plot and data.
    
    Signals:
        data_updated(str): Emitted when DataFrame data changes (result_id)
        headers_changed(str, list): Emitted when DataFrame headers change (result_id, columns)
        status_changed(str, str): Emitted when status changes (result_id, new_status)
        plot_updated(str): Emitted when plot changes (result_id)
        measurements_changed(str): Emitted when measurements change (result_id)
        error_changed(str, dict): Emitted when error info changes (result_id, error_info)
        log_added(str, dict): Emitted when a log entry is added (result_id, log_entry)
    """

    VALID_STATUSES = {
        "Not Run",
        "Running",
        "Pass",
        "Fail",
        "Error",
        "Aborted",
        "Complete"
    }

    # Define signals
    data_updated = Signal(str)  # result_id
    headers_changed = Signal(str, list)  # result_id, columns
    status_changed = Signal(str, str)  # result_id, new_status
    plot_updated = Signal(str)  # result_id
    measurements_changed = Signal(str)  # result_id
    error_changed = Signal(str, dict)  # result_id, error_info
    log_added = Signal(str, dict)  # result_id, log_entry

    def __init__(self, name: str, id: Optional[str] = None):
        BaseModel.__init__(self, id)
        QObject.__init__(self)
        
        logger.debug(f"TestResult.__init__: Creating result '{name}' with ID={self.id}")
        self.name = name
        self._status = "Not Run"
        self.plot = None
        self._data = pd.DataFrame()
        self.measurements: Dict[str, Any] = {}
        self.error: Optional[Dict[str, str]] = None
        self.logs: List[Dict[str, str]] = []

        # Debounce timer for data updates
        self._update_timer = QTimer()
        self._update_timer.setInterval(200)  # 200ms debounce
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._emit_data_update)
        self._data_changed = False

        logger.debug(f"TestResult.__init__: Initialization complete for ID={self.id}")

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, value: str):
        if value not in self.VALID_STATUSES:
            logger.warning(f"Invalid status '{value}' for TestResult ID={self.id}. Defaulting to 'Not Run'.")
            value = "Not Run"

        if value != self._status:
            old_status = self._status
            self._status = value
            logger.debug(f"TestResult ID={self.id}: Status changed from '{old_status}' to '{value}'")
            self.status_changed.emit(self.id, value)

    @property
    def data(self) -> pd.DataFrame:
        """Returns the pandas DataFrame containing test data."""
        return self._data

    def set_data_headers(self, *columns):
        """Set or update DataFrame headers."""
        old_columns = list(self._data.columns)
        
        if len(old_columns) > 0:
            # Preserve existing data when updating headers
            self._data.columns = columns
        else:
            # Create new DataFrame with headers
            self._data = pd.DataFrame(columns=columns)
            
        logger.debug(f"TestResult ID={self.id}: Headers updated from {old_columns} to {list(columns)}")
        self.headers_changed.emit(self.id, list(columns))

    def set_data_row(self, idx: Optional[int], *values):
        """Set data row with automatic header creation if needed."""
        # Create default headers if needed
        if len(self._data.columns) == 0:
            default_headers = [f"Column_{i}" for i in range(len(values))]
            self._data = pd.DataFrame(columns=default_headers)
            logger.debug(f"TestResult ID={self.id}: Created default headers {default_headers}")
            self.headers_changed.emit(self.id, default_headers)

        # Handle value count mismatch
        if len(values) != len(self._data.columns):
            values = list(values)[:len(self._data.columns)]
            values.extend([None] * (len(self._data.columns) - len(values)))

        # Set the data
        actual_idx = idx if idx is not None else len(self._data)
        try:
            self._data.loc[actual_idx] = values
            self._data_changed = True
            
            # Start/restart debounce timer
            if not self._update_timer.isActive():
                self._update_timer.start()
                
            logger.debug(f"TestResult ID={self.id}: Set row {actual_idx}")
            return True
            
        except Exception as e:
            logger.error(f"TestResult ID={self.id}: Error setting data row: {e}")
            return False

    def _emit_data_update(self):
        """Emit data update signal if data has changed."""
        if self._data_changed:
            self._data_changed = False
            self.data_updated.emit(self.id)

    def set_trace(self, name: str, x_data=None, y_data=None, **style_kwargs) -> Trace:
        """Add or update a trace in the plot."""
        if not self.plot:
            self.plot = Plot(name=f"{self.name} Plot")
            
        trace = self.plot.set_trace(name, x_data, y_data, **style_kwargs)
        self.plot_updated.emit(self.id)
        return trace

    def update_measurements(self, measurements: Dict[str, Any]):
        """Update measurements dictionary."""
        self.measurements.update(measurements)
        self.measurements_changed.emit(self.id)

    def set_error(self, error_info: Dict[str, str]):
        """Set error information."""
        self.error = error_info
        self.error_changed.emit(self.id, error_info)

    def add_log(self, message: str, level: str = "INFO"):
        """Add a log entry with timestamp."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "level": level
        }
        self.logs.append(entry)
        self.log_added.emit(self.id, entry)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "plot": self.plot.to_dict() if self.plot else None,
            "data": self._data.to_dict(orient='split'),
            "measurements": self.measurements,
            "error": self.error,
            "logs": self.logs
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TestResult':
        """Create from dictionary."""
        result = TestResult(
            name=data["name"],
            id=data.get("id")
        )
        result.status = data.get("status", "Not Run")
        if data.get("plot"):
            result.plot = Plot.from_dict(data["plot"])
        if data.get("data"):
            result._data = pd.DataFrame(**data["data"])
        result.measurements = data.get("measurements", {})
        result.error = data.get("error")
        result.logs = data.get("logs", [])
        return result