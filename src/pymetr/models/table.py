import pandas as pd
from typing import Optional, List, Any
from pymetr.models.base import BaseModel
from pymetr.core.logging import logger

class DataTable(BaseModel):
    """
    Represents a tabular dataset with columns and rows.
    Stores data as a pandas DataFrame.
    """
    def __init__(
        self,
        title: str,
        columns: Optional[List[str]] = None,
        model_id: Optional[str] = None
    ):
        super().__init__(model_type='DataTable', model_id=model_id, name=title)
        self.set_property("title", title)
        # Store column names and create an empty DataFrame with those columns.
        columns = columns or []
        self.set_property("columns", columns)
        self.set_property("data", pd.DataFrame(columns=columns))
        logger.debug(f"DataTable '{title}' created with id {self.id}")

    # --- Pythonic Property Accessors ---

    @property
    def columns(self) -> List[str]:
        """Get the list of column names."""
        return self.get_property("columns", [])

    @columns.setter
    def columns(self, column_names: List[str]):
        self.set_columns(column_names)

    @property
    def data(self) -> pd.DataFrame:
        """Get the data as a pandas DataFrame."""
        return self.get_data()

    @data.setter
    def data(self, new_data: pd.DataFrame):
        self.set_property("data", new_data)

    # --- Existing Methods ---

    def get_columns(self) -> List[str]:
        return self.get_property("columns", [])

    def set_columns(self, column_names: List[str]):
        df = self.get_property("data")
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame()
        # Reindex the DataFrame to the new columns, filling missing values with None.
        df = df.reindex(columns=column_names)
        self.set_property("columns", column_names)
        self.set_property("data", df)

    def add_column(self, column_name: str):
        df = self.get_property("data")
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame()
        df[column_name] = None
        self.set_property("columns", list(df.columns))
        self.set_property("data", df)

    def row_count(self) -> int:
        df = self.get_property("data")
        if isinstance(df, pd.DataFrame):
            return len(df)
        return 0

    def col_count(self) -> int:
        df = self.get_property("data")
        if isinstance(df, pd.DataFrame):
            return len(df.columns)
        return 0

    def add_row(self, row_data: Optional[List[Any]] = None) -> int:
        df = self.get_property("data").copy()  # Create a copy
        columns = self.get_property("columns", [])
        col_count = len(columns)
        if row_data is None:
            row_data = [None] * col_count
        else:
            if len(row_data) < col_count:
                row_data += [None] * (col_count - len(row_data))
            elif len(row_data) > col_count:
                row_data = row_data[:col_count]
        # Create new DataFrame with added row
        new_df = pd.concat([df, pd.DataFrame([row_data], columns=df.columns)], 
                        ignore_index=True)
        self.set_property("data", new_df)
        return len(new_df) - 1

    def remove_row(self, index: int):
        df = self.get_property("data")
        if 0 <= index < len(df):
            df = df.drop(index=index).reset_index(drop=True)
            self.set_property("data", df)

    def get_data(self) -> pd.DataFrame:
        data = self.get_property("data")
        if isinstance(data, pd.DataFrame):
            return data
        return pd.DataFrame()

    def set_data(self, new_data: List[List[Any]]):
        columns = self.get_property("columns", [])
        col_count = len(columns)
        adjusted_rows = []
        for row in new_data:
            if len(row) < col_count:
                row = row + [None] * (col_count - len(row))
            elif len(row) > col_count:
                row = row[:col_count]
            adjusted_rows.append(row)
        df = pd.DataFrame(adjusted_rows, columns=columns)
        self.set_property("data", df)

    def get_value(self, row: int, col: int) -> Any:
        df = self.get_property("data")
        if isinstance(df, pd.DataFrame):
            try:
                return df.iat[row, col]
            except Exception:
                return None
        return None

    def set_value(self, row: int, col: int, value: Any):
        df = self.get_property("data")
        if isinstance(df, pd.DataFrame):
            try:
                df.iat[row, col] = value
                self.set_property("data", df)
            except Exception:
                pass
