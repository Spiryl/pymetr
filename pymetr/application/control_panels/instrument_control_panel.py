# pymetr/application/control_panels/instrument_control_panel.py
import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QGroupBox
from PySide6.QtCore import Signal

from pymetr.core.instrument import Instrument
from pymetr.application.factories.instrument_factory import InstrumentFactory
from pymetr.application.factories.instrument_interface import InstrumentInterface

logger = logging.getLogger(__name__)

class InstrumentControlPanel(QWidget):
    instrument_connected = Signal(str)
    instrument_disconnected = Signal(str)
    no_instruments_connected = Signal()

    def __init__(self, instrument_manager, parent=None):
        super().__init__(parent)
        self.instrument_manager = instrument_manager
        self.instrument_factory = InstrumentFactory()

        main_layout = QHBoxLayout(self)

        # Available Instruments
        available_group = QGroupBox("Available Instruments")
        available_layout = QVBoxLayout()
        self.available_instruments_list = QListWidget()
        available_layout.addWidget(self.available_instruments_list)

        connect_button = QPushButton("Connect")
        connect_button.clicked.connect(self.on_connect_button_clicked)
        available_layout.addWidget(connect_button)

        available_group.setLayout(available_layout)
        main_layout.addWidget(available_group)

        # Connected Instruments
        connected_group = QGroupBox("Connected Instruments")
        connected_layout = QVBoxLayout()
        self.connected_instruments_list = QListWidget()
        connected_layout.addWidget(self.connected_instruments_list)

        disconnect_button = QPushButton("Disconnect")
        disconnect_button.clicked.connect(self.on_disconnect_button_clicked)
        connected_layout.addWidget(disconnect_button)

        connected_group.setLayout(connected_layout)
        main_layout.addWidget(connected_group)

        self.update_available_instruments()

    def update_available_instruments(self):
        self.available_instruments_list.clear()
        instruments_data = Instrument.list_instruments("TCPIP?*::INSTR")
        for unique_key, resource in instruments_data[0].items():
            idn_response = unique_key.split(": ")[1]
            model_number = idn_response.split(',')[1].strip()
            display_text = f"{model_number} - {resource}"
            self.available_instruments_list.addItem(display_text)

    def on_connect_button_clicked(self):
        selected_item = self.available_instruments_list.currentItem()
        if selected_item:
            resource = selected_item.text().split(' - ')[1]
            instrument, unique_id = self.instrument_manager.initialize_instrument(resource)
            if instrument:
                self.available_instruments_list.takeItem(self.available_instruments_list.row(selected_item))
                self.connected_instruments_list.addItem(selected_item.text())
                self.instrument_connected.emit(unique_id)
            else:
                self.no_instruments_connected.emit()
        self.available_instruments_list.clearSelection()
        
    def on_disconnect_button_clicked(self):
        selected_item = self.connected_instruments_list.currentItem()
        if selected_item:
            unique_id = selected_item.text().split(' - ')[0]
            self.instrument_manager.disconnect_instrument(unique_id)
            self.connected_instruments_list.takeItem(self.connected_instruments_list.row(selected_item))
            self.available_instruments_list.addItem(selected_item.text())
            self.instrument_disconnected.emit(unique_id)
            self.remove_instrument_interface(unique_id)
            if not self.connected_instruments_list.count():
                self.no_instruments_connected.emit()

    def remove_instrument_interface(self, unique_id):
        pass