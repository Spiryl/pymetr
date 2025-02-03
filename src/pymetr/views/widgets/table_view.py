from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Qt
import pandas as pd

from pymetr.state import ApplicationState
from pymetr.models.data_table import DataTable

class TableView(QWidget):
    """Widget for displaying DataTable models."""
    
    def __init__(self, state: ApplicationState, model_id: str, parent=None):
        super().__init__(parent)
        self.state = state
        self.model_id = model_id
        self.model: DataTable = state.registry.get_model(model_id)

        if not self.model:
            raise ValueError(f"No DataTable model found with ID: {model_id}")

        self._setup_ui()
        self._load_data()
        self._register_signals()

    def _setup_ui(self):
        """Setup the table UI."""
        self.layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)

    def _load_data(self):
        """Load data from DataTable model into the table widget."""
        if self.model and isinstance(self.model.data, pd.DataFrame):
            df = self.model.data
            self.table.setRowCount(len(df))
            self.table.setColumnCount(len(df.columns))
            self.table.setHorizontalHeaderLabels(df.columns.tolist())

            for row_idx, row in df.iterrows():
                for col_idx, value in enumerate(row):
                    item = QTableWidgetItem(str(value))
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    self.table.setItem(row_idx, col_idx, item)

    def _register_signals(self):
        """Register model signals to update the view when data changes."""
        self.model.data_changed.connect(self._on_data_changed)
        self.model.row_added.connect(self._on_row_added)
        self.model.row_removed.connect(self._on_row_removed)

    def _on_data_changed(self):
        """Reloads the table when the entire dataset changes."""
        self._load_data()

    def _on_row_added(self, row):
        """Handles when a new row is added."""
        self._load_data()

    def _on_row_removed(self, row):
        """Handles when a row is removed."""
        self._load_data()
