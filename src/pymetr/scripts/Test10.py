import numpy as np
import time

def run_test():
    """
    New Test Script:
    1. Create a result with 2 plots and update them for 5 seconds.
    2. Add 2 more plots to the same result and update for another 5 seconds.
    3. Create a new result with a table and a plot, updating both for 5 seconds.
    """

    # -----------------------------
    # STEP 1: Create a result with 2 plots
    # -----------------------------
    result1 = create_result("Result: Two Initial Plots")
    result1.show()

    # Create first plot: Dynamic Sine Wave
    sine_plot = create_plot("Dynamic Sine Wave")
    sine_plot.set_property("x_label", "Time (s)")
    sine_plot.set_property("y_label", "Amplitude")
    result1.add(sine_plot)

    # Create second plot: Dynamic Cosine Wave
    cosine_plot = create_plot("Dynamic Cosine Wave")
    cosine_plot.set_property("x_label", "Time (s)")
    cosine_plot.set_property("y_label", "Amplitude")
    result1.add(cosine_plot)

    # Prepare x axis data
    x = np.linspace(0, 2 * np.pi, 500)
    
    # Update these plots for 5 seconds
    duration1 = 5  # seconds
    start_time = time.time()
    frame = 0
    while (time.time() - start_time) < duration1:
        frame += 1
        phase = frame * 0.1
        # Update sine plot
        y_sine = np.sin(x + phase)
        sine_plot.set_trace("Sine", x, y_sine, color="#4CAF50")
        
        # Update cosine plot
        y_cosine = np.cos(x + phase)
        cosine_plot.set_trace("Cosine", x, y_cosine, color="#2196F3")
        
        # Update progress (0 to 50% for step 1)
        progress = ((time.time() - start_time) / duration1) * 50
        set_test_progress(progress, f"Step 1: Frame {frame}")
        
        wait(50)  # Wait 50ms between frames

    # -----------------------------
    # STEP 2: Add 2 more plots and update for 5 seconds
    # -----------------------------
    # Create third plot: Random Noise
    noise_plot = create_plot("Random Noise")
    noise_plot.set_property("x_label", "Sample")
    noise_plot.set_property("y_label", "Value")
    result1.add(noise_plot)

    # Create fourth plot: Random Walk
    walk_plot = create_plot("Random Walk")
    walk_plot.set_property("x_label", "Step")
    walk_plot.set_property("y_label", "Position")
    result1.add(walk_plot)

    # Prepare data for random walk
    walk_data = np.zeros(200)
    duration2 = 5  # seconds
    start_time = time.time()
    frame = 0
    while (time.time() - start_time) < duration2:
        frame += 1
        # Update noise plot with random data
        noise = np.random.normal(0, 1, 500)
        noise_plot.set_trace("Noise", x, noise, color="#FF5722")
        
        # Update random walk: shift data and add new random step
        walk_data = np.roll(walk_data, -1)
        walk_data[-1] = walk_data[-2] + np.random.normal(0, 0.2)
        walk_plot.set_trace("Walk", np.arange(200), walk_data, color="#9C27B0")
        
        # Update progress (50% to 100% for step 2)
        progress = 50 + ((time.time() - start_time) / duration2) * 50
        set_test_progress(progress, f"Step 2: Frame {frame}")
        
        wait(50)
    
    # -----------------------------
    # STEP 3: Create a new result with a table and a plot
    # -----------------------------
    result2 = create_result("Result: Table")
    result2.show()

    # Create a table with two columns: Time and Value
    table = create_table("Data Table")
    table.set_columns(["Time", "Value"])
    result2.add(table)

    frame = 0
    while (frame < 20):
        frame += 1
        value = np.random.random()  # generate a random value
        table.add_row([current_time, value])

        wait(50)

    set_test_progress(100, f"Step 3: Updating table and plot, frame {frame}")    
    # Mark both results as complete
    result1.status = "Pass"
    result2.status = "Pass"
    set_test_progress(100, "Test complete!")
    return True
