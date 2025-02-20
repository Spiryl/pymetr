import numpy as np

def run_test(test):
    """
    Minimal test with single plot and few updates
    """
    # Create result container
    result = test.create_result("Simple Plot Test")
    result.show()
    
    # Create a single plot
    plot = test.create_plot("Simple Sine Wave")
    plot.x_label = "Time"
    plot.y_label = "Amplitude"
    result.add(plot)
    
    # Create x points
    x = np.linspace(0, 10, 5000)

    for i in range(50):
        # Simple sine wave with changing phase
        y = np.sin(x + i)
        plot.set_trace("Sine", x, y, color="#4CAF50")
        
        # Longer wait to see each update clearly
        test.wait(100)  # 100 ms between updates
        result.progress = (i*2)
    
    result.progress = 100
    result.status = "PASS"
    return True