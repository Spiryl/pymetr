#  --- instrument_manager.py ------
import logging
logger = logging.getLogger()
from datetime import datetime
from pyqtgraph.parametertree import Parameter, ParameterTree
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtWidgets import QVBoxLayout, QDockWidget, QPushButton, QWidget, QApplication

from pymetr.core import Instrument
from pymetr.application.instrument_manager import InstrumentManager

class InstrumentPanel(QDockWidget):
    instrument_connected = Signal(str)
    instrument_disconnected = Signal(str)
    trace_data_ready = Signal(object)
    continuous_mode_changed = Signal(bool)

    def __init__(self, instrument_manager, parent=None):
        super().__init__(parent)
        self.instrument_manager = instrument_manager
        self.instrument_manager.parameter_updated.connect(self.handle_parameter_update)
        self.instrument_manager.source_updated.connect(self.handle_source_update)
        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)
        self.setWidget(self.widget)
        self.instruments = {}  # Dictionary to store connected instruments

    def setup_parameters(self, parameters):
        """
        Receives a parameter tree and displays it within the dock.
        """
        logger.debug(f"Setting up parameters")
        self.parameters = parameters
        self.parameterTree = ParameterTree()
        self.layout.addWidget(self.parameterTree)
        self.parameterTree.setAlternatingRowColors(True)
        self.parameterTree.setParameters(parameters, showTop=True)
        self.parameterTree.setDragEnabled(True)  # Enable drag functionality
        self.parameterTree.setAcceptDrops(True)  # Enable drop functionality

    def add_action_button(self, button_text, handler_function):
        """
        Adds an action button to the instrument dock.

        Args:
            button_text (str): The text to display on the button.
            handler_function (callable): The function to be called when the button is clicked.
        """
        logger.debug(f"Adding action button: {button_text}")
        button = QPushButton(button_text)
        button.clicked.connect(lambda: handler_function())
        self.layout.addWidget(button)

    def setup_parameter_tree(self, instrument, unique_id):
        instr_data = instrument['instr_data']
        self.parameters_dict = instr_data['parameter_tree']
        self.path_map = instrument['path_map']
        self.parameters = Parameter.create(name=unique_id, type='group', children=self.parameters_dict)
        self.setup_parameters(self.parameters)
        self.parameters.sigTreeStateChanged.connect(self.create_parameter_change_handler(unique_id))

        def update_param_attributes(param_dict):
            if 'access' in param_dict:
                param_dict['readonly'] = param_dict['access'] != 'write'
            if 'range' in param_dict:
                param_dict['limits'] = param_dict['range']
            if 'units' in param_dict:
                param_dict['units'] = param_dict['units']
            for child_dict in param_dict.get('children', []):
                update_param_attributes(child_dict)

        for param_dict in self.parameters_dict:
            update_param_attributes(param_dict)

    def setup_method_buttons(self, methods_dict, instr):
        for method_name, method_info in methods_dict.items():
            if method_info.get('is_source_method', False):
                method_func = getattr(instr, method_name)
                self.add_action_button(method_name, method_func)

    def setup_sources_group(self, sources_list):
        sources_group = {
            'name': 'Sources',
            'type': 'group',
            'children': [{'name': source, 'type': 'bool', 'value': False} for source in sources_list]
        }
        self.parameters_dict.insert(0, sources_group)

    def create_parameter_change_handler(self, unique_id):
        def parameter_changed(param, changes):
            for param, change, data in changes:
                param_name = param.name()
                logger.debug(f"Parameter changed: {param_name}, Change: {change}, Data: {data}")

                # Check if the parameter type is 'action' to handle method execution
                if param.opts.get('type') == 'action':
                    if change == 'activated':  # Ensure the change type is an action activation
                        logger.debug(f"Action parameter activated: {param_name}")
                        # Dynamically find and call the associated method on the instrument
                        if hasattr(self.instrument_manager.instruments[unique_id]['instance'], param_name):
                            method = getattr(self.instrument_manager.instruments[unique_id]['instance'], param_name)
                            method()  # Execute the method
                            logger.debug(f"Executed action method: {param_name}")
                        else:
                            logger.error(f"No method found for action parameter: {param_name}")
                # Check if the parameter is in the "Sources" group
                elif param.parent() and param.parent().name() == "Sources":
                    logger.debug(f"Source {param_name} changed to {data}")
                    # Handle the source checkbox state change here
                    if data:
                        self.instrument_manager.instruments[unique_id]['instance'].sources.add_source(param_name)
                    else:
                        self.instrument_manager.instruments[unique_id]['instance'].sources.remove_source(param_name)
                else:
                    # For non-action parameters, handle them as usual
                    full_param_path = self.instrument_manager.construct_parameter_path(param).lstrip(unique_id)
                    full_param_path = full_param_path.lstrip(".")  
                    logger.debug(f"Constructed full parameter path: {full_param_path}")

                    path_map = self.instrument_manager.instruments[unique_id]['path_map']
                    property_path = path_map.get(full_param_path)
                    logger.debug(f"Property path from map: {property_path}")

                    if property_path:
                        # Use existing logic to update the property based on its path
                        self.instrument_manager.update_instrument(property_path, data, unique_id)
                    else:
                        logger.error(f"Property path missing for parameter: {param_name}")
        return parameter_changed

    def handle_parameter_update(self, unique_id, param_path, value):
        # Find and update the parameter in your parameter tree
        param = self.find_parameter_by_path(param_path)
        if param:
            param.setValue(value)

    def find_parameter_by_path(self, param_path):
        # Split path and find parameter based on path elements
        parts = param_path.split('.')
        current_params = self.parameters  # Assuming this is the root of your ParameterTree
        for part in parts:
            current_params = next((p for p in current_params.children() if p.name() == part), None)
            if current_params is None:
                return None
        return current_params
    
    def handle_source_update(self, unique_id, source_name, is_selected):
        # Construct the full path for the source parameter
        source_param_path = f"Oscilloscope.Sources.{source_name}"
        param = self.find_parameter_by_path(source_param_path)
        if param:
            param.setValue(is_selected)
            logger.debug(f"Updated source '{source_name}' to state: {is_selected}")
        else:
            logger.error(f"Source parameter '{source_name}' not found in parameter tree")

    def setup_instrument_panel(self, instrument, unique_id):
        self.unique_id = unique_id

        self.continuous_acquisition_button = QPushButton("Run")
        self.continuous_acquisition_button.setCheckable(True)
        self.continuous_acquisition_button.toggled.connect(lambda checked: self.toggle_continuous_acquisition(instrument['instance'], checked))
        self.layout.addWidget(self.continuous_acquisition_button)

        instrument['instance'].trace_data_ready.connect(self.on_trace_data_ready)

        self.setup_method_buttons(instrument['methods'], instrument['instance'])
        self.setup_parameter_tree(instrument, unique_id)
        self.setup_sources_group(instrument['sources'])

        syncInstrumentButton = QPushButton(f"Sync {unique_id}")
        syncInstrumentButton.clicked.connect(lambda: self.instrument_manager.synchronize_instrument(unique_id))
        self.layout.addWidget(syncInstrumentButton)

    def on_trace_data_ready(self, trace_data):
        # We can the trace data ready signal and ask for more if we are continuous
        QApplication.processEvents()
        instrument_instance = self.instrument_manager.instruments[self.unique_id]['instance']
        if instrument_instance.continuous_mode:
            instrument_instance.fetch_trace()

    def toggle_continuous_acquisition(self, instrument_instance, checked):
        instrument_instance.continuous_mode = checked
        self.continuous_acquisition_button.setText("Stop Acquisition" if checked else "Start Acquisition")
        self.continuous_mode_changed.emit(checked)
        # if checked:
        #     instrument_instance.fetch_trace()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QMainWindow
    from PyMetr import Instrument
    import sys

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Instrument Control")
            self.setGeometry(100, 100, 800, 600)

            self.instrument_manager = InstrumentManager()
            self.instrument_panel = None

            self.init_ui()

        def init_ui(self):
            resource = Instrument.select_instrument("TCPIP?*::INSTR")
            instrument, unique_id = self.instrument_manager.initialize_instrument(resource)
            if instrument:
                self.instrument_panel = InstrumentPanel(self.instrument_manager)
                self.instrument_panel.setup_instrument_panel(instrument, unique_id)
                self.addDockWidget(Qt.RightDockWidgetArea, self.instrument_panel)

    sys.argv += ['-platform', 'windows:darkmode=2']
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())