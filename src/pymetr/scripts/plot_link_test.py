import numpy as np

def run_test(test):
    """
    Simple test creating a plot that's shown both directly and in a result view.
    """
    # Create a plot and show it directly
    plot = test.create_plot("Test Plot")
    plot.show()  # This will create the first view of the plot
    
    # Create some test data
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x)
    y2 = np.cos(x)
    
    # Add two traces
    plot.set_trace("Sine", x, y1, color="#FF0000")
    plot.set_trace("Cosine", x, y2, color="#00FF00")
    test.wait(1000)  # Give time for first traces to show
    
    # Now create a result and add the SAME plot to it
    result = test.create_result("Plot Test Result")
    result.add(plot)  # This creates a second view of the same plot
    result.show()
    
    test.wait(100)  # Give time for second view to setup
    
    # Update one trace to see if both views update
    y3 = np.sin(x) * 2
    plot.set_trace("Sine", x, y3, color="#FF0000")
    
    result.status = "PASS"
    return True