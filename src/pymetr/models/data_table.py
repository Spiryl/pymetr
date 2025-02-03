# app/models/data_table.py

from typing import Dict, List, Optional, Any
import pandas as pd
from PySide6.QtCore import QObject, Signal
import logging
from .base import BaseModel

logger = logging.getLogger(__name__)

class DataTable(BaseModel, QObject):
    """
    A data table wrapper around pandas DataFrame with UI state tracking.
    
    Signals:
        data_changed(str): Emitted when data content changes (table_id)
        row_added(str, int): Emitted when row is added (table_id, row_index)
        row_removed(str, int): Emitted when row is removed (table_id, row_index)
        selection_changed(str, list): Emitted when row selection changes (table_id, selected_indices)
        visibility_changed(str, bool): Emitted when visibility changes (table_id, is_visible)
        sorted(str, str, bool): Emitted when data is sorted (table_id, column, ascending)
        filtered(str, str): Emitted when data is filtered (table_id, filter_condition)
    """

    data_changed = Signal(str)  # table_id
    row_added = Signal(str, int)  # table_id, row_index
    row_removed = Signal(str, int)  # table_id, row_index
    selection_changed = Signal(str, list)  # table_id, selected_indices
    visibility_changed = Signal(str, bool)  # table_id, is_visible
    sorted = Signal(str, str, bool)  # table_id, column, ascending
    filtered = Signal(str, str)  # table_id, filter_condition

    def __init__(
        self,
        result_id: str,
        name: str,
        data: Optional[pd.DataFrame] = None,
        id: Optional[str] = None
    ):
        BaseModel.__init__(self, id)
        QObject.__init__(self)
        
        self.result_id = result_id
        self.name = name
        self._data = data if data is not None else pd.DataFrame()
        self._visible = True
        self._selected_rows: List[int] = []

        logger.debug(f"Created DataTable '{self.name}' with ID: {self.id}")

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    def set_data(self, data: pd.DataFrame):
        """Set the entire DataFrame."""
        self._data = data
        logger.debug(f"DataTable ID={self.id}: Set new data with shape {data.shape}")
        self.data_changed.emit(self.id)

    def add_row(self, row: Dict[str, Any]):
        """Add a new row to the DataFrame."""
        index = len(self._data)
        self._data = pd.concat([self._data, pd.DataFrame([row])], ignore_index=True)
        logger.debug(f"DataTable ID={self.id}: Added row at index {index}")
        self.row_added.emit(self.id, index)

    def remove_row(self, index: int):
        """Remove a row by index."""
        if index in self._data.index:
            self._data = self._data.drop(index).reset_index(drop=True)
            logger.debug(f"DataTable ID={self.id}: Removed row at index {index}")
            self.row_removed.emit(self.id, index)

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        if self._visible != value:
            self._visible = value
            logger.debug(f"DataTable ID={self.id}: Visibility set to {value}")
            self.visibility_changed.emit(self.id, value)

    def select_rows(self, indices: List[int]):
        """Select multiple rows by their indices."""
        self._selected_rows = indices
        logger.debug(f"DataTable ID={self.id}: Selected rows {indices}")
        self.selection_changed.emit(self.id, indices)

    def sort_by(self, column: str, ascending: bool = True):
        """Sort the DataFrame by a column."""
        if column in self._data.columns:
            self._data = self._data.sort_values(by=column, ascending=ascending)
            logger.debug(f"DataTable ID={self.id}: Sorted by '{column}' ({ascending=})")
            self.sorted.emit(self.id, column, ascending)

    def filter_by(self, condition: str):
        """Filter the DataFrame using a query string."""
        try:
            self._data = self._data.query(condition)
            logger.debug(f"DataTable ID={self.id}: Filtered with condition '{condition}'")
            self.filtered.emit(self.id, condition)
        except Exception as e:
            logger.error(f"DataTable ID={self.id}: Filter error: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "result_id": self.result_id,
            "name": self.name,
            "data": self._data.to_dict(orient='records'),
            "visible": self._visible,
            "selected_rows": self._selected_rows
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'DataTable':
        """Create from dictionary."""
        table = DataTable(
            result_id=data["result_id"],
            name=data["name"],
            data=pd.DataFrame(data.get("data", [])),
            id=data.get("id")
        )
        table.visible = data.get("visible", True)
        table._selected_rows = data.get("selected_rows", [])
        return table