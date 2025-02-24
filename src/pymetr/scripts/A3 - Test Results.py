import numpy as np

def run_test(test):
    """
    Simple test creating a plot that's shown both directly and in a result view.
    """

    # Now create a test result object with a name
    result = test.create_result("Test Result")

    # Create a plot with a name
    plot = test.create_plot("Test Plot")

    # Add the plot to this test result
    result.add(plot)

    # Tell the UI to show the result.
    result.show()

    # Create some test data
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x)
    y2 = np.cos(x)
    
    # Use the set_trace method to create and/or update plot traces
    plot.set_trace("Sine", x, y1, color="#FF0000")
    plot.set_trace("Cosine", x, y2, color="#00FF00")
    
    # Set the result status to 'PASS' or 'FAIL'
    result.status = "PASS"

    # Returning False from the test script would flag the test with an error.
    return True