from typing import Dict, Any, Optional, List
import pandas as pd
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QMenu
from PySide6.QtCore import Qt
from pyqtgraph.parametertree import Parameter
from pymetr.core.logging import logger

from .base import ModelParameter, ModelParameterItem, ParameterWidget


class DataTableDisplayWidget(ParameterWidget):
    """
    Widget that displays the row and column counts in the format
    "[{row_count}:{column_count}]" in white text.
    """
    def __init__(self, param, parent=None):
        super().__init__(param, parent)
        self._current_counts = {'rows': None, 'cols': None}
        self._setup_ui()

    def _setup_ui(self):
        logger.debug("Setting up DataTableDisplayWidget UI")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.size_label = QLabel()
        self.size_label.setStyleSheet("""
            QLabel {
                color: white;
                padding: 2px 4px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.size_label)
        layout.addStretch()
        self.setLayout(layout)

    def _process_pending_update(self):
        logger.debug("DataTableDisplayWidget processing pending update")
        self._pending_updates.clear()

        # Get the model from state
        model = (self.param.state.get_model(self.param.model_id)
                 if self.param.state and self.param.model_id else None)
        if model is None:
            logger.debug("DataTableDisplayWidget: No model found")
            return

        # Get the DataFrame
        df = model.get_property("data")
        if not isinstance(df, pd.DataFrame):
            logger.debug("DataTableDisplayWidget: Model data is not a DataFrame")
            return

        # Calculate row and column counts
        row_count = len(df)
        col_count = len(df.columns)
        logger.debug(f"DataTableDisplayWidget: Row count = {row_count}, Col count = {col_count}")

        # Only update the label if counts have changed
        if (row_count != self._current_counts['rows'] or 
            col_count != self._current_counts['cols']):
            self.size_label.setText(f"[{row_count}:{col_count}]")
            self._current_counts['rows'] = row_count
            self._current_counts['cols'] = col_count
            logger.debug("DataTableDisplayWidget label updated")
        else:
            logger.debug("DataTableDisplayWidget: No change in row/col counts")


class DataTableParameterItem(ModelParameterItem):
    """
    Parameter item for the DataTable parameter.
    Creates and attaches the DataTableDisplayWidget.
    """
    def makeWidget(self) -> Optional[QWidget]:
        logger.debug(f"Creating DataTable widget for parameter {self.param.title()}")
        try:
            self.widget = DataTableDisplayWidget(self.param)
            return self.widget
        except Exception as e:
            logger.error(f"Error creating DataTable widget for {self.param.title()}: {e}")
            return None

    def updateWidget(self, **kwargs):
        if self.widget:
            logger.debug(f"DataTableParameterItem updating widget with {kwargs}")
            self.widget.queue_update(**kwargs)

    def treeWidgetChanged(self) -> None:
        # Attach the widget when the item is added to the tree.
        super().treeWidgetChanged()
        if self.widget is None:
            logger.debug(f"DataTableParameterItem.treeWidgetChanged: Creating widget for parameter {self.param.title()}")
            self.widget = self.makeWidget()
            self.param.widget = self.widget
        tree = self.treeWidget()
        if tree is not None:
            logger.debug("DataTableParameterItem.treeWidgetChanged: Setting item widget in tree")
            tree.setItemWidget(self, 1, self.widget)

class DataTableParameter(ModelParameter):
    """
    Model parameter for data table display.
    This parameter both displays table metadata via a custom widget
    and holds sub-parameters for display and formatting options.
    """
    itemClass = DataTableParameterItem

    def __init__(self, **opts):
        opts['type'] = 'table'
        super().__init__(**opts)
        self.can_export = True
        # Retrieve the initial model if available
        model = self.state.get_model(self.model_id) if self.state and self.model_id else None
        self._setup_parameters(model)

    def _setup_parameters(self, model):
        logger.debug("Setting up DataTableParameter child parameters")
        # Define child parameters for table display options.
        children = [
            {
                'name': 'Display',
                'type': 'group',
                'expanded': False,
                'children': [
                    {
                        'name': 'show_index',
                        'type': 'bool',
                        'value': model.get_property('show_index', True) if model else True
                    },
                    {
                        'name': 'show_header',
                        'type': 'bool',
                        'value': model.get_property('show_header', True) if model else True
                    },
                    {
                        'name': 'alternate_rows',
                        'type': 'bool',
                        'value': model.get_property('alternate_rows', True) if model else True
                    }
                ]
            },
            {
                'name': 'Format',
                'type': 'group',
                'expanded': False,
                'children': [
                    {
                        'name': 'decimal_places',
                        'type': 'int',
                        'value': model.get_property('decimal_places', 2) if model else 2,
                        'limits': (0, 10)
                    },
                    {
                        'name': 'thousands_separator',
                        'type': 'bool',
                        'value': model.get_property('thousands_separator', True) if model else True
                    }
                ]
            }
        ]
        
        for child in children:
            param = Parameter.create(**child)
            self.addChild(param)
            if child['type'] == 'group':
                for subchild in param.children():
                    subchild.sigValueChanged.connect(self._handle_child_change)
        logger.debug("DataTableParameter child parameters set up")

    def _handle_child_change(self, param, value):
        logger.debug(f"DataTableParameter child parameter {param.name()} changed to {value}")
        if not self.state or not self.model_id:
            logger.debug("DataTableParameter: Missing state or model_id")
            return
        try:
            # Update the underlying model property when a child parameter changes
            self.set_model_property(param.name(), value)
            # Trigger an update to the widget
            if hasattr(self, 'widget') and self.widget:
                self.widget.queue_update()
        except Exception as e:
            logger.error(f"Error handling child parameter change for {param.name()}: {e}")

    def handle_property_update(self, name: str, value: Any):
        logger.debug(f"DataTableParameter handling property update: {name} = {value}")
        try:
            updated = False
            # Update matching child parameter values.
            for group in self.children():
                if group.type() == 'group':
                    for param in group.children():
                        if param.name() == name:
                            param.setValue(value)
                            updated = True
                            break
                    if updated:
                        break
            # For metadata updates (row and column counts), trigger the widget update.
            if name in ['row_count', 'col_count', 'data']:
                if hasattr(self, 'widget') and self.widget:
                    self.widget.queue_update(**{name: value})
        except Exception as e:
            logger.error(f"Error handling property update for {name}: {e}")
