import numpy as np
def run_test(test):
    """
    Test script to analyze model linking behavior.
    Creates a hierarchy of models and monitors registration/linking.
    """
    # Create a result for our test
    result = test.create_result("Model Link Analysis")
    
    # Create a few plots in sequence
    plot1 = test.create_plot("Plot 1")
    plot2 = test.create_plot("Plot 2")
    
    # Add some traces to the plots
    x = np.linspace(0, 10, 100)

    # Set the trace on plot1
    y1 = np.sin(x)
    plot1.set_trace("Sine", x, y1)
    
    # Create another trace on plot2
    y2 = np.cos(x)
    plot2.set_trace("Cosine", x, y2)
    
    # Add both plots to the same result
    result.add(plot1)
    result.add(plot2)

    # Tell the UI you want to see this right away
    result.show()

    # Return a status for the result
    result.status = "PASS"

    # Return True if the script finished successfully
    return True