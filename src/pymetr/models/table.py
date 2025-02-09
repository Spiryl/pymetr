from typing import Optional, List,  Any
from pymetr.models.base import BaseModel
from pymetr.core.logging import logger

class DataTable(BaseModel):
    """
    Represents a tabular dataset with columns and rows.
    Stores column names and row data in model properties.
    """

    def __init__(
        self,
        title: str,
        columns: Optional[List[str]] = None,
        model_id: Optional[str] = None
    ):
        """
        :param title:  Name/description of this table
        :param columns: Optional list of column names
        :param model_id: Optional unique identifier (auto-generated if None)
        """
        super().__init__(model_id=model_id)
        self.set_property("title", title)
        # Keep column names in a list of strings
        self.set_property("columns", columns or [])
        # Store table data as a list of rows, where each row is a list of cell values
        self.set_property("data", [])
        
        logger.debug(f"DataTable '{title}' created with id {self.id}")

    @property
    def title(self) -> str:
        return self.get_property("title")

    @title.setter
    def title(self, value: str):
        self.set_property("title", value)

    def get_columns(self) -> List[str]:
        """Return the list of column names."""
        return self.get_property("columns")

    def set_columns(self, column_names: List[str]):
        """
        Replace all columns with new names.
        If new column count is different, existing rows are truncated or extended with None.
        """
        old_columns = self.get_property("columns")
        data = self.get_property("data")

        # Adjust each row's length to match new columns
        new_count = len(column_names)
        for row in data:
            if len(row) < new_count:
                row.extend([None] * (new_count - len(row)))
            elif len(row) > new_count:
                del row[new_count:]

        self.set_property("columns", column_names)
        self.set_property("data", data)  # re-emit data after adjusting

    def add_column(self, column_name: str):
        """
        Add a single new column (appended to the right).
        All existing rows get a None placeholder in that column.
        """
        columns = self.get_property("columns")
        data = self.get_property("data")

        columns.append(column_name)
        for row in data:
            row.append(None)

        self.set_property("columns", columns)
        self.set_property("data", data)

    def row_count(self) -> int:
        """Number of rows."""
        return len(self.get_property("data"))

    def col_count(self) -> int:
        """Number of columns."""
        return len(self.get_property("columns"))

    def add_row(self, row_data: Optional[List[Any]] = None) -> int:
        """
        Append a new row. If row_data is shorter than columns, missing cells become None;
        if it's longer, extra items are discarded. Returns the new row index.
        """
        columns = self.get_property("columns")
        data = self.get_property("data")

        if row_data is None:
            # Create an empty row
            row_data = [None] * len(columns)
        else:
            # Adjust row_data size to match column count
            if len(row_data) < len(columns):
                row_data += [None] * (len(columns) - len(row_data))
            elif len(row_data) > len(columns):
                row_data = row_data[:len(columns)]

        data.append(row_data)
        self.set_property("data", data)
        return len(data) - 1

    def remove_row(self, index: int):
        """
        Remove a row at a given index (0-based).
        """
        data = self.get_property("data")
        if 0 <= index < len(data):
            data.pop(index)
            self.set_property("data", data)

    def get_data(self) -> List[List[Any]]:
        """Return the entire table as a list of rows."""
        return self.get_property("data")

    def set_data(self, new_data: List[List[Any]]):
        """
        Replace all rows with new_data (list of lists).
        Rows are truncated/extended to match current columns.
        """
        columns = self.get_property("columns")
        data_adjusted = []
        col_count = len(columns)
        for row in new_data:
            # Adjust row to match col_count
            if len(row) < col_count:
                row += [None] * (col_count - len(row))
            elif len(row) > col_count:
                row = row[:col_count]
            data_adjusted.append(row)

        self.set_property("data", data_adjusted)

    def get_value(self, row: int, col: int) -> Any:
        """
        Get the value from a specific cell.
        """
        data = self.get_property("data")
        if 0 <= row < len(data) and 0 <= col < len(data[row]):
            return data[row][col]
        return None

    def set_value(self, row: int, col: int, value: Any):
        """
        Set the value in a specific cell, then emit property change.
        """
        data = self.get_property("data")
        if 0 <= row < len(data) and 0 <= col < len(data[row]):
            data[row][col] = value
            # Storing back triggers a property change event and
            # ensures watchers know data has updated.
            self.set_property("data", data)