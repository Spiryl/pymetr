import time
import numpy as np

def run_test():
    """Sample test that shows progress, status updates, and generates plots."""
    try:
        # Mark test as running.
        set_test_status("Running")
        
        # Create a new result for this test run.
        result = new_result("Sample Test")
        
        # Step 1: Initialization.
        set_test_progress(5, "Initializing test...")
        wait(500)  # Wait 0.5 second
        
        # Step 2: Load parameters.
        set_test_progress(15, "Loading test parameters...")
        wait(500)
        
        # Step 3: Generate sample data.
        set_test_progress(25, "Generating sample data...")
        x = np.linspace(0, 10, 100)
        y1 = np.sin(x)
        y2 = np.cos(x)
        wait(500)
        
        # Step 4: Process sine wave.
        set_test_progress(40, "Processing sine wave data...")
        wait(500)
        
        # Step 5: Process cosine wave.
        set_test_progress(55, "Processing cosine wave data...")
        wait(500)
        
        # Step 6: Create sine wave plot.
        set_test_progress(70, "Creating sine wave plot...")
        result.set_trace(
            "Sine Wave",
            x_data=x,
            y_data=y1,
            color="#FF0000"
        )
        wait(500)
        
        # Step 7: Create cosine wave plot.
        set_test_progress(85, "Creating cosine wave plot...")
        result.set_trace(
            "Cosine Wave",
            x_data=x,
            y_data=y2,
            color="#0000FF"
        )
        wait(500)
        
        # Final step: Complete the test.
        set_test_progress(100, "Test complete!")
        set_test_status("Pass")
        
        return True  # Test passed

    except Exception as e:
        # In case of any errors, update the test status to "Error"
        set_test_status("Error")
        set_test_progress(100, f"Test failed: {e}")
        return False
