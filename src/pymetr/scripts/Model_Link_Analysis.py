def run_test():
    """
    Test script to analyze model linking behavior.
    Creates a hierarchy of models and monitors registration/linking.
    """
    # Create a result for our test
    result = create_result("Model Link Analysis")
    
    # Create a group to hold some test models
    group = create_group("Test Group")
    
    # Create a few plots in sequence
    plot1 = create_plot("Plot 1")
    plot2 = create_plot("Plot 2")
    
    # Add some traces to the plots
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x)
    y2 = np.cos(x)
    
    # Create traces - this should trigger model registration and linking
    trace1 = create_trace("Sine", x, y1)
    trace2 = create_trace("Cosine", x, y2)
    
    # Set the traces on plot1
    plot1.set_trace("Sine", x, y1)
    plot1.set_trace("Cosine", x, y2)
    
    # Create another plot with the same traces
    plot2.set_trace("Sine", x, y1)
    plot2.set_trace("Cosine", x, y2)
    
    # Add everything to result to force hierarchy
    result.add(group)
    result.add(plot1)
    result.add(plot2)
    
    # Explicitly try to add again to test duplicate linking
    result.add(plot1)  # This should ideally be ignored
    
    # Add delay to ensure we can see all events
    wait(1000)
    
    result.status = "Pass"
    return True