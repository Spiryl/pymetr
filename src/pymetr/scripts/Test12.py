# Example test script with debug prints
# e.g. "Test12.py"

import numpy as np
import time

def run_test():
    result = create_result("Row Debug Test")
    result.show()

    table = create_table("Debug Table")
    table.columns = ["Frame", "Time", "Value"]
    result.add(table)

    duration_s = 5
    start_time = time.time()
    frame = 0

    while (time.time() - start_time) < duration_s:
        frame += 1
        current_time_s = round(time.time() - start_time, 2)
        value = np.random.random()

        # Create new row data and use the fixed add_row method
        row_data = [frame, current_time_s, value]
        table.add_row(row_data)
        
        # Update progress
        progress_percent = (time.time() - start_time)/duration_s * 100
        set_test_progress(progress_percent, f"Frame {frame}")

        wait(200)  # ms

    result.status = "Pass"
    return True
