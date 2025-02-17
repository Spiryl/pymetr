# data_table_parameter.py

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QMenu
from pyqtgraph.parametertree import Parameter
from .base import ModelParameter, ModelParameterItem

class DataTableParameterItem(ModelParameterItem):
    """Tree item for a DataTable parameter."""

    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.widget = None

    def makeWidget(self):
        # Create a small widget with a label showing row/column info
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.info_label = QLabel()
        layout.addWidget(self.info_label)
        w.setLayout(layout)

        self.widget = w
        self.update_info()  # Initial population
        return w

    def update_info(self):
        """Refresh the label to show row/column counts from the model."""
        if self.param.state and self.param.model_id:
            model = self.param.state.get_model(self.param.model_id)
            if model:
                row_count = model.get_property('row_count', 0)
                col_count = model.get_property('col_count', 0)
                self.info_label.setText(f"Rows: {row_count}, Columns: {col_count}")

    def optsChanged(self, param, opts):
        """Called when Parameter options change."""
        super().optsChanged(param, opts)
        # If the row_count or col_count property changes, refresh the label
        if 'row_count' in opts or 'col_count' in opts:
            self.update_info()

    def add_context_menu_actions(self, menu: QMenu):
        # Example: add a "Refresh" context menu
        refresh_action = menu.addAction("Refresh Data")
        refresh_action.triggered.connect(self.update_info)
        # Could add more actions here if needed

    def treeWidgetChanged(self):
        """Called when this item is added or removed from a tree."""
        super().treeWidgetChanged()
        if self.widget is None:
            self.widget = self.makeWidget()
        tree = self.treeWidget()
        if tree is not None:
            tree.setItemWidget(self, 1, self.widget)


class DataTableParameter(ModelParameter):
    """Custom Parameter type for a data table."""
    itemClass = DataTableParameterItem

    def __init__(self, **opts):
        # Mark the parameter's type so pyqtgraph knows it's a "datatable" param
        opts['type'] = 'datatable'
        super().__init__(**opts)

    def add_context_actions(self, menu: QMenu) -> None:
        """Add parameter-specific context menu actions."""
        pass
