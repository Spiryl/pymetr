# Current Test Script
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
