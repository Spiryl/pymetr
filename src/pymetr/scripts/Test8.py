import numpy as np

def run_test():
    """
    Frame Rate Test
    Creates a single noise trace and continuously updates it.
    """
    
    # Create plot with basic setup
    plot = create_plot("Noise Plot")
    plot.x_label = "Sample"
    plot.y_label = "Amplitude"
    
    # Generate initial x points
    x_points = np.arange(1000)
    
    # Run for 1000 frames
    for frame in range(1000):
        # Generate new noise data
        y_points = np.random.normal(0, 1, 1000)
        
        # Update the trace
        plot.set_trace("Noise", x_points, y_points)
        
        # Update progress every 10 frames
        if frame % 10 == 0:
            progress = (frame / 1000) * 100
            set_test_progress(progress, f"Frame {frame}/1000")
        
        # Small wait to prevent overwhelming the UI
        wait(1)  # 1ms wait
    
    set_test_progress(100, "Test complete!")
    return True