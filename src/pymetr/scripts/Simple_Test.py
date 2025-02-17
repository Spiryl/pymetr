# SimpleDebugTest.py
import numpy as np
import time

def run_test():
    print("Starting test")
    
    # Create a test result
    result = create_result("Debug Test")
    print(f"Created result: {result.id}")
    result.show()
    
    # Create and configure a plot
    plot = create_plot("Debug Plot")
    print(f"Created plot: {plot.id}")
    plot.x_label = "Time (s)"
    plot.y_label = "Signal"
    result.add_child(plot)  # Changed from add to add_child
    
    # Create some sample data
    x = np.linspace(0, 10, 100)
    y = np.sin(x)
    
    # Create a trace
    trace = create_trace("Sine Wave", x, y)
    print(f"Created trace: {trace.id}")
    plot.add_child(trace)  # Changed from add to add_child
    
    # Create a table
    table = create_table("Debug Table")
    print(f"Created table: {table.id}")
    table.columns = ["Time", "Value"]
    result.add_child(table)  # Changed from add to add_child
    
    # Run a short loop to simulate progress
    duration_s = 1
    start_time = time.time()
    
    while (time.time() - start_time) < duration_s:
        current_time = time.time() - start_time
        progress = (current_time/duration_s) * 100
        
        # Add data to table
        table.add_row([current_time, np.sin(current_time)])
        
        # Update progress
        print(f"Progress: {progress:.1f}%")
        set_test_progress(progress, f"Time: {current_time:.1f}s")
        
        # Small delay
        wait(500)  # 500ms delay
    
    print("Test complete")
    result.status = "Pass"
    return True