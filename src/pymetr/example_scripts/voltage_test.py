# Voltage Test Script
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
