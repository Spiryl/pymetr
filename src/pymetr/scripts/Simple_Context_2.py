import numpy as np

def run_test(test):
    """
    Test that creates two results. The first result loops and finishes as PASS,
    and the second loops and finishes as FAIL. The overall test script status should
    aggregate to FAIL.
    """
    # --- First Result: Expected to PASS ---
    result1 = test.create_result("Sine Wave Test 1")
    result1.show()
    
    # Create a plot for the first result.
    plot1 = test.create_plot("Sine Wave 1")
    plot1.x_label = "Time"
    plot1.y_label = "Amplitude"
    result1.add(plot1)
    
    # Create x points.
    x = np.linspace(0, 10, 5000)
    
    # Update loop for first result.
    for i in range(50):
        y = np.sin(x + i)
        plot1.set_trace("Sine", x, y, color="#4CAF50")
        test.wait(10)  # 10 ms between updates
        result1.progress = (i + 1) * 2  # progress goes from 2 to 100%
    result1.progress = 100
    result1.status = "PASS"
    
    # --- Second Result: Expected to FAIL ---
    result2 = test.create_result("Sine Wave Test 2")
    result2.show()
    
    # Create a plot for the second result.
    plot2 = test.create_plot("Sine Wave 2")
    plot2.x_label = "Time"
    plot2.y_label = "Amplitude"
    result2.add(plot2)
    
    # Update loop for second result.
    for i in range(50):
        y = np.sin(x - i)
        plot2.set_trace("Sine", x, y, color="#F44336")
        test.wait(10)  # 10 ms between updates
        result2.progress = (i + 1) * 2  # progress goes from 2 to 100%
    result2.progress = 100
    result2.status = "FAIL"
    
    # Overall, if any child result fails, the test script should be marked as FAIL.
    # Returning False indicates the test script did not fully pass.
    return True
