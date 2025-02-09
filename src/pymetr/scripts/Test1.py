import numpy as np
import time

def run_test():
    """
    Comprehensive test script demonstrating engine features.
    """
    # Create a top-level group for organizing results
    main_group = create_group("Main Test Results")
    
    # Create some test results
    voltage_result = create_result("Voltage Test")
    current_result = create_result("Current Test")
    
    # Add them to the main group
    main_group.add([voltage_result, current_result])
    
    # Simulate a long-running test with progress updates
    for progress in range(0, 101, 10):
        set_test_progress(progress, f"Processing step {progress}%")
        wait(500)  # Wait 500ms between updates
        
    # Generate some sample data
    time_points = np.linspace(0, 10, 1000)
    voltage = 5 * np.sin(2 * np.pi * 0.5 * time_points) + np.random.normal(0, 0.1, len(time_points))
    current = 2 * np.sin(2 * np.pi * 0.5 * time_points + np.pi/4) + np.random.normal(0, 0.05, len(time_points))
    
    # Create plots for voltage and current
    voltage_plot = create_plot("Voltage Waveform")
    voltage_plot.set_property("x_label", "Time (s)")
    voltage_plot.set_property("y_label", "Voltage (V)")
    voltage_plot.create_trace(time_points, voltage, name="Measured Voltage")
    
    current_plot = create_plot("Current Waveform")
    current_plot.set_property("x_label", "Time (s)")
    current_plot.set_property("y_label", "Current (A)")
    current_plot.create_trace(time_points, current, name="Measured Current")
    
    # Add plots to respective results
    voltage_result.add(voltage_plot)
    current_result.add(current_plot)
    
    # Create a power plot
    power_plot = create_plot("Power Analysis")
    power_plot.set_property("x_label", "Time (s)")
    power_plot.set_property("y_label", "Power (W)")
    
    # Calculate and plot instantaneous power
    power = voltage * current
    power_plot.create_trace(time_points, power, name="Instantaneous Power")
    
    # Add power plot to main group
    main_group.add(power_plot)
    
    # Create a data table with measurements
    table = create_table("Summary Measurements")
    table.add_row({
        "Measurement": "Vrms",
        "Value": f"{np.sqrt(np.mean(voltage**2)):.3f}",
        "Units": "V"
    })
    table.add_row({
        "Measurement": "Irms",
        "Value": f"{np.sqrt(np.mean(current**2)):.3f}",
        "Units": "A"
    })
    table.add_row({
        "Measurement": "Average Power",
        "Value": f"{np.mean(power):.3f}",
        "Units": "W"
    })
    
    # Add table to main group
    main_group.add(table)
    
    # Set pass/fail status based on some criteria
    voltage_peak = np.max(np.abs(voltage))
    if voltage_peak < 6.0:  # Example pass criteria
        voltage_result.status = "Pass"
    else:
        voltage_result.status = "Fail"
        
    current_peak = np.max(np.abs(current))
    if current_peak < 3.0:  # Example pass criteria
        current_result.status = "Pass"
    else:
        current_result.status = "Fail"
    
    # Set final progress
    set_test_progress(100, "Test complete!")
    
    # Return overall test success
    return voltage_result.status == "Pass" and current_result.status == "Pass"