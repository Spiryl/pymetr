import numpy as np

def run_test(test):
    """
    Frame Rate Test
    Creates a single noise trace and continuously updates it.
    """
    
    # Create plot with basic setup
    plot = test.create_plot("Noise Plot")
    plot.show()
    plot.x_label = "Sample"
    plot.y_label = "Amplitude"
    
    # Generate initial x points
    x_points = np.arange(5000)
    
    # Run for 1000 frames
    for frame in range(1000):
        # Generate new noise data
        y_points = np.random.normal(0, 1, 5000)
        
        # This method can be used to create and/or update traces by name
        plot.set_trace("Noise", x_points, y_points, color="#FF9535")
        
        # Small wait to prevent overwhelming the UI
        test.wait(1)  # 1ms wait
    
    return True