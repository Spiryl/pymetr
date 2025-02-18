import numpy as np

def run_test():
    """
    Comprehensive Plot Test
    Tests all plot features including properties, markers, cursors, and tables.
    """
    
    # Create plot with complete setup
    plot = create_plot("Feature Test Plot")
    plot.show()
    
    # Set basic properties
    plot.title = "Complete Feature Test"
    plot.x_label = "Time (s)"
    plot.y_label = "Voltage (V)"
    plot.x_unit = "s"
    plot.y_unit = "V"
    
    # Set display properties
    plot.grid_enabled = True
    plot.legend_enabled = True
    plot.roi_visible = True
    plot.background_color = "#1E1E1E"
    plot.foreground_color = "#FFFFFF"
    plot.grid_color = "#404040"
    plot.grid_alpha = 0.3
    plot.legend_position = "right"
    
    # Set axis properties
    plot.x_log = False
    plot.y_log = False
    plot.x_inverted = False
    plot.y_inverted = False
    plot.x_ticks = None  # Auto ticks
    plot.y_ticks = None  # Auto ticks
    plot.x_tick_labels = None  # Auto labels
    plot.y_tick_labels = None  # Auto labels
    
    # Generate some example data
    t = np.linspace(0, 10, 1000)
    signal = np.sin(2 * np.pi * 0.5 * t)
    noise = np.random.normal(0, 0.1, len(t))
    
    # Create main signal trace with styling
    plot.set_trace(
        "Signal",
        t,
        signal,
        mode="Group",
        color="#00FF00",
        style="solid",
        width=2,
        marker_style="",
        visible=True,
        opacity=1.0
    )
    
    # Create noise trace with different styling
    plot.set_trace(
        "Noise",
        t,
        signal + noise,
        mode="Group",
        color="#FF0000",
        style="dash",
        width=1,
        marker_style="",
        visible=True,
        opacity=0.5
    )
    
    # Create some markers at interesting points
    max_idx = np.argmax(signal)
    min_idx = np.argmin(signal)
    
    # Maximum point marker
    plot.create_marker(
        x=t[max_idx],
        y=signal[max_idx],
        label="Maximum",
        color="yellow",
        size=10,
        symbol="t"  # triangle
    )
    
    # Minimum point marker
    plot.create_marker(
        x=t[min_idx],
        y=signal[min_idx],
        label="Minimum",
        color="cyan",
        size=10,
        symbol="s"  # square
    )
    
    # Add vertical cursor at center
    plot.create_cursor(
        name="Cursor 1",
        axis="x",
        position=5.0,
        color="yellow",
        style="dash",
        width=1
    )
    
    # Add horizontal cursor at zero
    plot.create_cursor(
        name="Cursor 2",
        axis="y",
        position=0.0,
        color="magenta",
        style="dot",
        width=1
    )
    
    # Create a data table with analysis results
    table = create_table("Signal Analysis")
    
    # Add columns to table
    table.columns = ["Metric", "Value", "Units"]
    
    # Add analysis results
    table.add_row(["Peak-to-Peak", np.ptp(signal), "V"])
    table.add_row(["RMS", np.sqrt(np.mean(signal**2)), "V"])
    table.add_row(["Mean", np.mean(signal), "V"])
    table.add_row(["Std Dev", np.std(signal), "V"])
    
    # Update test progress
    set_test_progress(50, "Created plot elements")
    
    # Demonstrate some dynamic updates
    wait(1000)  # Wait 1 second
    
    # Update some properties
    plot.grid_color = "#606060"
    plot.title = "Updated Feature Test"
    
    # Move cursors
    cursors = plot.get_cursors()
    for cursor in cursors:
        if cursor.axis == "x":
            cursor.set_position(7.0)
        else:
            cursor.set_position(0.5)
    
    # Update marker positions
    markers = plot.get_markers()
    for marker in markers:
        if marker.label == "Maximum":
            marker.set_position(8.0, 0.8)
        elif marker.label == "Minimum":
            marker.set_position(2.0, -0.8)
    
    # Update progress and complete
    set_test_progress(100, "Test complete!")
    return True