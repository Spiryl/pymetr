import numpy as np

def run_test():
    """
    Simplified Plot Test
    Tests basic plot features, including trace plotting, markers, cursors, and a data table.
    """
    
    # Create a plot with a simple setup
    plot = create_plot("Simplified Test Plot")
    plot.show()
    
    # Set basic plot properties
    plot.title = "Simplified Feature Test"
    plot.x_label = "Time (s)"
    plot.y_label = "Amplitude"
    plot.background_color = "#1E1E1E"
    plot.foreground_color = "#FFFFFF"
    plot.grid_enabled = True
    plot.legend_enabled = True
    
    # Generate sample data
    t = np.linspace(0, 10, 500)
    sine_wave = np.sin(2 * np.pi * 0.5 * t)
    
    # Add a trace for the sine wave
    plot.set_trace(
        "Sine Wave",
        t,
        sine_wave,
        mode="Group",
        color="#00FF00",
        style="solid",
        width=2,
        marker_style="o",
        visible=True,
        opacity=1.0
    )
    
    # Create a marker at the maximum point of the sine wave
    max_idx = np.argmax(sine_wave)
    plot.create_marker(
        x=t[max_idx],
        y=sine_wave[max_idx],
        label="Max",
        color="yellow",
        size=10,
        symbol="t"  # triangle symbol
    )
    
    # Create a vertical cursor at x = 5.0 and a horizontal cursor at y = 0.0
    plot.create_cursor(
        name="Cursor X",
        axis="x",
        position=5.0,
        color="yellow",
        style="dash",
        width=1
    )
    plot.create_cursor(
        name="Cursor Y",
        axis="y",
        position=0.0,
        color="magenta",
        style="dot",
        width=1
    )
    
    # Create a simple data table for analysis results
    table = create_table("Simple Analysis")
    table.columns = ["Metric", "Value", "Units"]
    table.add_row(["Peak-to-Peak", np.ptp(sine_wave), "V"])
    table.add_row(["RMS", np.sqrt(np.mean(sine_wave**2)), "V"])
    
    # Update test progress
    set_test_progress(50, "Plot elements created")
    
    # Wait 1 second then update some properties dynamically
    wait(1000)  # Wait for 1 second
    plot.title = "Updated Simplified Feature Test"
    
    # Move cursors: shift the x-cursor to 7.0 and the y-cursor to 0.5
    for cursor in plot.get_cursors():
        if cursor.axis == "x":
            cursor.set_position(7.0)
        elif cursor.axis == "y":
            cursor.set_position(0.5)
    
    # Update the marker position (for example, shift the max marker slightly)
    for marker in plot.get_markers():
        if marker.label == "Max":
            marker.set_position(t[max_idx], sine_wave[max_idx] + 0.2)
    
    set_test_progress(100, "Test complete!")
    return True
