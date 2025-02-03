# discovery_view.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Signal, Qt

from pymetr.logging import logger
from pymetr.drivers.registry import get_driver_info

class DiscoveryView(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._setup_ui()

        # Listen for "instruments_discovered" signal
        self.state.signals.connect("instruments_discovered", self._on_instruments_discovered)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # "Refresh" button -> calls state.find_instruments
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(lambda: self.state.find_instruments())
        layout.addWidget(self.btn_refresh)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setHorizontalHeaderLabels(["Manufacturer","Model","Serial","Firmware","Resource"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        # "Connect" button -> connect the selected row
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self._on_connect)
        layout.addWidget(self.btn_connect)

    def _on_instruments_discovered(self, discovered: dict):
        """
        discovered is a dict:
          {
            unique_id: {
              "manufacturer": "...",
              "model": "...",
              "serial": "...",
              "firmware": "...",
              "resource": "..."
            },
            ...
          }
        """
        self.table.setRowCount(0)
        self._instrument_data_list = []  # store them in a local list

        for uid, info in discovered.items():
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(info["manufacturer"]))
            self.table.setItem(row, 1, QTableWidgetItem(info["model"]))
            self.table.setItem(row, 2, QTableWidgetItem(info["serial"]))
            self.table.setItem(row, 3, QTableWidgetItem(info["firmware"]))
            self.table.setItem(row, 4, QTableWidgetItem(info["resource"]))

            self._instrument_data_list.append(info)

    def _on_connect(self):
        """
        Called when user clicks 'Connect'. We retrieve the selected
        row's instrument info, look up driver_info from the registry,
        then pass it to 'connect_instrument'.
        """
        row = self.table.currentRow()
        if row < 0:
            # No selection
            return

        # Get the discovered instrument info from the row
        info = self._instrument_data_list[row]

        # 1) Attempt to look up a driver from your registry using the 'model'
        model = info.get("model")
        if not model:
            print("No model in this instrument info, cannot find driver.")
            return

        try:
            driver_info = get_driver_info(model)  # from your drivers/registry.py
            info["driver_info"] = driver_info
        except ValueError as e:
            print(f"No driver found for model {model}: {e}")
            # You can choose to continue or return here.

        # 2) Now that 'info' has 'driver_info', call state
        self.state.connect_instrument(info)