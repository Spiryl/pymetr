import numpy as np
import colorsys

def run_test():
    """
    Real-Time Noise Plot with Horizontal Cursors, Rainbow Trace Color,
    and Manual Y-Axis Limits
    Generates random noise data for 10,000 frames, updates a single trace,
    moves two horizontal cursors to track the trace's max and min values, and
    updates the trace color to roll through the rainbow.
    The y-axis is manually fixed to [-5, 5] so the axis does not jump around.
    """
    
    # Create the plot and set labels
    plot = create_plot("Noise Plot")
    plot.x_label = "Sample"
    plot.y_label = "Amplitude"
    
    # Show the plot immediately
    plot.show()
    
    # Set manual y-axis limits to (-5, 5)
    # (Assuming the plot model supports setting the "y_lim" property)
    plot.set_property("y_lim", (-5, 5))
    
    # Create the trace with empty data initially
    x_points = np.arange(5000)
    y_points = np.zeros(5000)
    plot.set_trace("Noise", x_points, y_points)
    
    # Create two horizontal cursors and capture the returned objects.
    # These cursors will be used to track the max and min values.
    max_cursor = plot.create_cursor(
        name="MaxCursor",
        axis="y",      # Horizontal line
        position=0.0,
        color="#FFFF88",  # Lighter yellow
        style="dash",
        width=1,
        visible=True
    )
    min_cursor = plot.create_cursor(
        name="MinCursor",
        axis="y",      # Horizontal line
        position=0.0,
        color="#FFFF88",  # Lighter yellow
        style="dash",
        width=1,
        visible=True
    )
    
    # Main loop: generate noise, update the trace (with color), and move cursors.
    for frame in range(10000):
        # Generate random noise data
        y_points = np.random.normal(0, 1, size=5000)
        
        # Calculate a new hue value that cycles through the rainbow.
        hue = (frame % 360) / 360.0
        r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
        new_color = '#{:02X}{:02X}{:02X}'.format(int(r*255), int(g*255), int(b*255))
        
        # Update the trace with new data and the updated color.
        plot.set_trace("Noise", x_points, y_points, color=new_color)
        
        # Compute max and min of the current data.
        max_val = np.max(y_points)
        min_val = np.min(y_points)
        
        # Update the horizontal cursor positions.
        max_cursor.position = max_val
        min_cursor.position = min_val
        
        # Update test progress every 10 frames.
        if frame % 10 == 0:
            progress = (frame / 10000) * 100
            set_test_progress(progress, f"Frame {frame}/10000")
        
        # Brief pause to allow the UI to refresh.
        wait(1)  # 1 ms pause
    
    set_test_progress(100, "Test complete!")
    return True
