# src/pymetr/__main__.py
import sys
import pandas as pd
from PySide6.QtWidgets import QApplication
from pathlib import Path

from .state import ApplicationState
from .views.windows.main_window import MainWindow
from .models.base import BaseModel
from .models.data_table import DataTable
from .models.test_script import TestScript
from .models.test_result import TestResult
from .logging import logger

VOLTAGE_SCRIPT = '''# Voltage Test Script
import time
from instrument_utils import get_dut

def test_voltage():
    """Run automated voltage measurements."""
    # Get the DUT
    dut = get_dut()
    
    # Configure voltage measurement
    set_test_progress(10, "Configuring voltage measurement...")
    dut.configure_voltage_measurement()
    
    # Take measurements
    set_test_progress(50, "Taking voltage measurements...")
    result = new_result("Voltage Test")
    measurements = dut.measure_voltage()
    
    # Process data
    set_test_progress(75, "Processing measurements...")
    for value in measurements:
        result.add_data_point(value)
        time.sleep(0.1)  # Simulate processing
    
    # Save data and complete
    set_test_progress(90, "Saving results...")
    result.add_data(measurements)
    set_test_progress(100, "Test complete!")
    
    return result
'''

CURRENT_SCRIPT = '''# Current Test Script
import time
from instrument_utils import get_dut

def test_current():
    """Run automated current measurements."""
    # Get the DUT
    dut = get_dut()
    
    # Configure current measurement
    set_test_progress(10, "Configuring current measurement...")
    dut.configure_current_measurement()
    
    # Take measurements
    set_test_progress(50, "Taking current measurements...")
    result = new_result("Current Test")
    measurements = dut.measure_current()
    time.sleep(0.5)  # Simulation
    
    # Test paused at 50% for demonstration
    return result
'''

def create_test_data(state: ApplicationState):
    logger.info("Creating test data...")

    # Create example script files if they don't exist
    scripts_dir = Path(__file__).parent / "example_scripts"
    scripts_dir.mkdir(exist_ok=True)

    voltage_script = scripts_dir / "voltage_test.py"
    current_script = scripts_dir / "current_test.py"

    # Write script content
    voltage_script.write_text(VOLTAGE_SCRIPT)
    current_script.write_text(CURRENT_SCRIPT)

    # Create test scripts with file paths
    script1 = TestScript(
        name="Voltage Test",
        script_path=voltage_script
    )
    script2 = TestScript(
        name="Current Test",
        script_path=current_script
    )
    
    # Set different progress values
    script1.progress = 100  # Completed
    script1.status = "Complete"
    script2.progress = 50   # In progress
    script2.status = "Running"
    
    state.registry.register(script1)
    state.registry.register(script2)
    logger.debug(f"Registered test scripts: {script1.id}, {script2.id}")

    # Create test results with meaningful names
    result1 = TestResult("Voltage Measurements")
    result2 = TestResult("Current Measurements")
    state.registry.register(result1)
    state.registry.register(result2)
    logger.debug(f"Registered test results: {result1.id}, {result2.id}")

    # Link results to test scripts
    state.registry.link(script1.id, result1.id)
    state.registry.link(script2.id, result2.id)

    # Emit signals for scripts and results
    state.signals.emit('model_created', script1.id, 'TestScript')
    state.signals.emit('model_created', script2.id, 'TestScript')
    state.signals.emit('model_created', result1.id, 'TestResult')
    state.signals.emit('model_created', result2.id, 'TestResult')
    state.signals.emit('models_linked', script1.id, result1.id)
    state.signals.emit('models_linked', script2.id, result2.id)

    # Create sample data tables with descriptive names
    data1 = pd.DataFrame({
        "Voltage (V)": [1.2, 2.3, 3.4], 
        "Current (A)": [0.5, 0.8, 1.1]
    })
    data_table1 = DataTable(result_id=result1.id, name="Voltage vs Current Data", data=data1)
    state.registry.register(data_table1)
    state.registry.link(result1.id, data_table1.id)

    data2 = pd.DataFrame({
        "Resistance (Ω)": [100, 200, 300], 
        "Power (W)": [0.6, 1.2, 1.8]
    })
    data_table2 = DataTable(result_id=result2.id, name="Resistance vs Power Data", data=data2)
    state.registry.register(data_table2)
    state.registry.link(result2.id, data_table2.id)

    logger.debug(f"Registered data tables: {data_table1.id}, {data_table2.id}")

    # Emit signals for data tables
    state.signals.emit('model_created', data_table1.id, 'DataTable')
    state.signals.emit('model_created', data_table2.id, 'DataTable')
    state.signals.emit('models_linked', result1.id, data_table1.id)
    state.signals.emit('models_linked', result2.id, data_table2.id)

    logger.info("Test data creation completed.")

def main():
    app = QApplication(sys.argv)


    app.setStyle('fusion')

    # # Load and apply the stylesheet
    # with open('gui/styles.qss', 'r') as file:
    #     app.setStyleSheet(file.read())

    # Create application state and main window
    state = ApplicationState()
    window = MainWindow(state)

    # Add test data
    create_test_data(state)

    # Show the main window
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())