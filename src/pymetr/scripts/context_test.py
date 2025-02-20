import numpy as np

def run_test(test):
    """
    Comprehensive Plot and Animation Test
    Combines static elements with dynamic trace animation, markers (using names),
    cursors, and a table with analysis data.
    """
    # Create a result container and show it
    result = test.create_result("Test Result")
    result.show()
    # Create a plot and add it to the result
    plot = test.create_plot("Test Plot")
    plot.x_label = "Time (s)"
    plot.y_label = "Voltage (V)"
    result.add(plot)
    
    # Set basic plot properties
    plot.title = "Complete Feature Test"
    plot.x_unit = "s"
    plot.y_unit = "V"
    plot.grid_enabled = True
    plot.legend_enabled = True
    
    
    # Create a table with 10 rows of analysis data and add it to the result
    table = test.create_table("Test Data")
    result.add(table)
    table.columns = ["Index", "Value1", "Value2", "Value3"]
    for i in range(10):
        # Generate example random data for each row
        row = [i, f"{np.random.uniform(0,1):.2f}",
                  f"{np.random.uniform(0,1):.2f}",
                  f"{np.random.uniform(0,1):.2f}"]
        table.add_row(row)
        test.wait(20)  # 10 ms wait between frames

    
    # Update progress to mid-test
    result.progress = 50
    
    # Animate 5 traces on the plot with the specified colors
    colors = ["#02FEE4", "#4BFF36", "#FF9535", "#F23CA6", "#5E57FF"]
    x_points = np.linspace(0, 10, 1000)
    
    # Initialize traces for each color
    for idx, col in enumerate(colors):
        plot.set_trace(f"Test Trace{idx+1}", x_points, np.zeros_like(x_points), color=col)
    
    # Animate for 1000 frames
    for frame in range(1000):
        for idx, col in enumerate(colors):
            phase = frame * 0.1
            # Generate sine data with a phase shift and small noise
            y_data = np.sin(x_points + phase + idx) + np.random.normal(0, 0.05, len(x_points))
            plot.set_trace(f"Test Trace{idx+1}", x_points, y_data, color=col)
        test.wait(17)  # 10 ms wait between frames
        # Update progress from 50% to 80%
        result.progress = 50 + int((frame+1)/200 * 30)
    
    
    # Final progress update and set test status
    result.progress = 100
    result.status = "PASS"
    return True
