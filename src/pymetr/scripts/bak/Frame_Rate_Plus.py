import numpy as np

def run_test(test):
    """
    Frame Rate Test
    Creates a single noise trace with a marker at peak and cursor at minimum.
    """
    # Create plot with basic setup
    plot = test.create_plot("Noise Plot")
    plot.show()
    plot.x_label = "Sample"
    plot.y_label = "Amplitude"

    # Generate initial x points
    x_points = np.arange(5000)

    # Initial setup for marker and cursor
    plot.set_marker("Peak", x=0, y=0, color="#FF0000")  # Red marker

    # Run for 1000 frames
    for frame in range(1000):
        # Generate new noise data
        y_points = np.random.normal(0, 1, 5000)
        
        # Find max and min positions
        max_idx = np.argmax(y_points)
        min_idx = np.argmin(y_points)
        
        # Update the trace
        plot.set_trace("Noise", x_points, y_points, color="#FF9535")
        
        # Update marker to peak
        plot.set_marker("Peak", x=float(x_points[max_idx]), y=float(y_points[max_idx]), color="#FF00FF")

        # Small wait to prevent overwhelming the UI
        test.wait(10)  # 1ms wait

    return True