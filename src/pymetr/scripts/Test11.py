import numpy as np
import time

def run_test():
    """
    Test Script: Dynamic Data and Table Update
    
    This script demonstrates:
      1. Creating a result and a plot.
      2. Creating a sine-wave trace using the new create_trace helper.
      3. Dynamically updating the trace's data over time.
      4. Creating a table and logging the sine wave's peak amplitude in real time.
      5. Updating progress throughout the test.
    """
    # Create a new test result and show it.
    result = create_result("Test: Dynamic Data and Table Update")
    result.show()

    # Create a plot and set its labels via properties.
    plot = create_plot("Simulated Data Plot")
    plot.x_label = "Time (s)"
    plot.y_label = "Amplitude"
    result.add(plot)

    # Prepare an initial sine-wave dataset.
    t = np.linspace(0, 2 * np.pi, 500)
    y = np.sin(t)
    
    # Create a sine wave trace using the create_trace helper.
    sine_trace = create_trace("Sine Wave", t, y, color="#4CAF50", style="solid", width=2)
    # Add the trace to the plot.
    plot.add_child(sine_trace)

    # Create a table to log the sine wave's peak amplitude over time.
    table = create_table("Measurement Log")
    table.columns = ["Time (s)", "Peak Amplitude"]
    result.add(table)

    # Simulate dynamic updates for 10 seconds.
    duration = 10  # seconds
    start_time = time.time()
    frame = 0
    while time.time() - start_time < duration:
        frame += 1
        current_time = time.time() - start_time

        # Shift the sine wave's phase over time.
        phase = frame * 0.1
        new_y = np.sin(t + phase)
        # Update the trace data via the property accessor.
        sine_trace.data = [t, new_y]

        # Update progress from 0 to 100%.
        progress = ((time.time() - start_time) / duration) * 100
        set_test_progress(progress, f"Frame {frame}: Updating sine wave")

        # Every 10 frames (~1 sec if wait is 100ms), log the peak amplitude.
        if frame % 10 == 0:
            peak = np.max(new_y)
            table.add_row([current_time, peak])

        wait(100)  # Wait 100ms between updates

    # Mark the result as passed and signal test completion.
    result.status = "Pass"
    set_test_progress(100, "Test complete!")
    return True
