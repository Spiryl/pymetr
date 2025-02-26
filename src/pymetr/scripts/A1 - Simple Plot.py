#Basic visualization with a single sine wave trace
import numpy as np
def run_test(test):
    """
    Minimal test with single plot
    """
    
    # Create a single plot
    plot = test.create_plot("Simple Sine Wave")
    plot.x_label = "Time"
    plot.y_label = "Amplitude"
    plot.show()
    
    # Create x points
    x = np.linspace(0, 10, 100)
    y = np.sin(x)
    plot.set_trace("Sine", x, y, color="#4CAF50")

    return True