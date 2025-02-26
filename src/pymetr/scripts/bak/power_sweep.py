import numpy as np

def run_test(test):
    """
    Power Calibration Test:
    - Sweeps from 100 MHz to 20 GHz in 100 MHz steps
    - Power levels from +20 dBm to -10 dBm in 5 dB steps
    - Measures raw power, applies calibration, and calculates error
    - Creates three plots:
        1. Raw measured power vs frequency (all power levels, updates each step)
        2. Calibrated power vs frequency (all power levels, updates each step)
        3. Power error vs expected value (updates each step)
    - Generates a separate result for each power level
    - Each power level result has a plot and table (updates every measurement)
    - Adds markers at key tabulated frequencies
    """
    
    # Define color scheme
    colors = ["#02FEE4", "#4BFF36", "#FF9535", "#F23CA6", "#5E57FF"]
    power_levels = np.arange(20, -1, -5)  # +20 dBm to -10 dBm in 5 dB steps
    power_color_map = {power: colors[i % len(colors)] for i, power in enumerate(power_levels)}
    
    # Frequency and power setup
    freqs = np.arange(100e6, 20.1e9, 100e6)  # 100 MHz to 20 GHz steps
    key_freqs = np.arange(2e9, 20.1e9, 2e9)  # Even 2 GHz intervals from 2 GHz to 20 GHz
    
    # Create first result container
    result1 = test.create_result("Power Calibration")
    result1.show()

    # Create Plots
    raw_plot = test.create_plot("Raw Measured Power")
    raw_plot.x_label = "Frequency (Hz)"
    raw_plot.y_label = "Measured Power (dBm)"
    raw_plot.title = "Raw Power vs Frequency"
    result1.add(raw_plot)

    cal_plot = test.create_plot("Calibrated Power")
    cal_plot.x_label = "Frequency (Hz)"
    cal_plot.y_label = "Calibrated Power (dBm)"
    cal_plot.title = "Calibrated Power vs Frequency"
    result1.add(cal_plot)

    error_plot = test.create_plot("Power Error")
    error_plot.x_label = "Frequency (Hz)"
    error_plot.y_label = "Error (dB)"
    error_plot.title = "Power Error vs Expected"
    result1.add(error_plot)

    # Simulated calibration offsets (random small errors)
    calibration_offsets = np.random.uniform(-0.1, 0.05, len(freqs))

    # **Initialize storage for real-time trace updates**
    freqs_list = []  
    measured_powers = {power: [] for power in power_levels}
    calibrated_powers = {power: [] for power in power_levels}
    errors = {power: [] for power in power_levels}

    # Sweep through frequencies (Outer Loop)
    for i, freq in enumerate(freqs):
        freqs_list.append(freq)  # Track measured frequencies

        # Sweep through power levels (Inner Loop)
        for power in power_levels:
            # Simulate measured power (not perfect)
            raw_meas = power + np.random.normal(0, 0.1)  # ±0.1 dB noise
            meas_calibrated = raw_meas + calibration_offsets[i]  # Apply calibration
            error = meas_calibrated - power  # Deviation from expected

            # Append new data for this power level
            measured_powers[power].append(raw_meas)
            calibrated_powers[power].append(meas_calibrated)
            errors[power].append(error)

        # **Update plots in real-time**
        for power in power_levels:
            color = power_color_map[power]
            raw_plot.set_trace(f"Raw {power}dBm", freqs_list, measured_powers[power], color=color)
            cal_plot.set_trace(f"Cal {power}dBm", freqs_list, calibrated_powers[power], color=color)
            error_plot.set_trace(f"Error {power}dBm", freqs_list, errors[power], color=color)

        test.wait(100)  # Simulated delay for real instrument behavior
        result1.progress = int(((i + 1) / len(freqs)) * 100)

    result1.progress = 100
    result1.status = "PASS"

    # ----------------------------------------------
    # SECOND PART: Create a Result for Each Power Level
    # ----------------------------------------------

    for power in power_levels:
        result = test.create_result(f"Power {power}dBm")
        result.show()

        # Create a plot for error vs frequency for this power level
        error_plot_individual = test.create_plot(f"Error at {power}dBm")
        error_plot_individual.x_label = "Frequency (Hz)"
        error_plot_individual.y_label = "Error (dB)"
        error_plot_individual.title = f"Power Error vs Frequency ({power}dBm)"
        result.add(error_plot_individual)

        # Create a table for this power level
        table = test.create_table(f"Results at {power}dBm")
        table.columns = ["Frequency (GHz)", "Measured Power (dBm)", "Error (dB)", "Uncertainty (± dB)"]
        result.add(table)
        
        freqs_list = []
        errors_list = []
        
        for i, freq in enumerate(freqs):
            raw_meas = power + np.random.normal(0, 0.1)  # Simulated measurement
            meas_calibrated = raw_meas + calibration_offsets[i]
            error = meas_calibrated - power
            uncertainty = np.random.uniform(0.02, 0.05)  # Simulated uncertainty

            # Append new data
            freqs_list.append(freq)
            errors_list.append(error)

            # **Update table in real-time**
            if freq in key_freqs:
                table.add_row([f"{freq/1e9:.2f}", f"{meas_calibrated:.2f}", f"{error:.3f}", f"±{uncertainty:.3f}"])
            
            # **Update error plot in real-time**
            error_plot_individual.set_trace(f"Error {power}dBm", freqs_list, errors_list, color=power_color_map[power])
            test.wait(10)

        result.progress = 100
        result.status = "PASS"

    return True
