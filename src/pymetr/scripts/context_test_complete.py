import numpy as np

def run_test(test):
    """
    Demonstrates two results with just a few key updates.
    """
    # ---- First Result: Two Plots ----
    result1 = test.create_result("First Result")
    result1.show()

    # Setup plots
    plotA = test.create_plot("Plot A")
    plotA.x_label, plotA.y_label = "Time (s)", "Voltage (V)"
    plotA.title = "Plot A: Sine & Cosine with Marker"
    
    plotB = test.create_plot("Plot B")
    plotB.x_label, plotB.y_label = "Time (s)", "Amplitude"
    plotB.title = "Plot B: Random Data with Cursor"
    
    result1.add(plotA)
    result1.add(plotB)

    x = np.linspace(0, 10, 1000)
    
    # Initial state
    plotA.set_trace("Sine A", x, np.sin(x), color="#FF0000")
    plotA.set_trace("Cosine A", x, np.cos(x), color="#00FF00")
    plotA.set_marker("Marker A", x=5.0, y=0.0)
    
    plotB.set_trace("Random 1 B", x, np.random.normal(0, 0.1, len(x)), color="#0000FF")
    plotB.set_trace("Random 2 B", x, np.random.normal(0, 0.1, len(x)), color="#FFA500")
    plotB.set_cursor("Cursor B", position=2.0, axis="x", color="#00FFFF")
    
    result1.progress = 50
    test.wait(500)

    # Final state
    plotA.set_trace("Sine A", x, np.sin(x + np.pi), color="#FF0000")
    plotA.set_trace("Cosine A", x, np.cos(x + np.pi), color="#00FF00")
    plotA.set_marker("Marker A", x=5.0, y=0.5)
    
    plotB.set_trace("Random 1 B", x, np.random.normal(0.5, 0.1, len(x)), color="#0000FF")
    plotB.set_trace("Random 2 B", x, np.random.normal(-0.5, 0.1, len(x)), color="#FFA500")
    plotB.set_cursor("Cursor B", position=4.0)
    
    result1.progress = 100
    result1.status = "PASS"

    # ---- Second Result: Plot and Table ----
    result2 = test.create_result("Second Result")
    result2.show()

    plotC = test.create_plot("Plot C")
    plotC.x_label, plotC.y_label = "Sample", "Value"
    plotC.title = "Plot C: Random Sine"
    
    table = test.create_table("Data Table")
    table.columns = ["Index", "Value 1", "Value 2", "Value 3"]
    
    result2.add(plotC)
    result2.add(table)

    # Initial state
    x2 = np.arange(1000)
    plotC.set_trace("Random Sine C", x2, np.sin(x2 * 0.05), color="#4CAF50")
    
    # Add just a few rows
    for i in range(3):
        table.add_row([str(i)] + [f"{np.random.uniform(0,1):.3f}" for _ in range(3)])
    
    result2.progress = 50
    test.wait(500)

    # Final state
    plotC.set_trace("Random Sine C", x2, np.sin(x2 * 0.05 + np.pi) + np.random.normal(0, 0.1, len(x2)), color="#4CAF50")
    for i in range(3):
        table.add_row([str(i+3)] + [f"{np.random.uniform(0,1):.3f}" for _ in range(3)])
    
    result2.progress = 100
    result2.status = "PASS"
    
    return True