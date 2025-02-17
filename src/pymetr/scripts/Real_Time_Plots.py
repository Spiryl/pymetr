import numpy as np

def run_test():
    """
    Real-time Multi-Plot Test
    Creates 4 different plots that update in real-time:
    1. Sine wave with varying frequency
    2. Random noise with envelope
    3. Random walk
    4. Spinning vector plot
    """
    
    # Create a result for our plots
    result = create_result("Real-Time Plots")
    
    # Show the result view which will display all plots in a grid
    result.show()
    
    # Create 4 plots with basic setup
    sine_plot = create_plot("Dynamic Sine Wave")
    sine_plot.x_label = "Sample"
    sine_plot.y_label = "Amplitude"
    sine_plot.y_unit = "Volts"
    sine_plot.x_unit = "Seconds"
    result.add(sine_plot)
    
    noise_plot = create_plot("Modulated Noise")
    noise_plot.x_label = "Sample"
    noise_plot.y_label = "Amplitude"
    result.add(noise_plot)
    
    walk_plot = create_plot("Random Walk")
    walk_plot.x_label = "Time"
    walk_plot.y_label = "Position"
    result.add(walk_plot)
    
    vector_plot = create_plot("Spinning Vector")
    vector_plot.x_label = "X Position"
    vector_plot.y_label = "Y Position"
    result.add(vector_plot)
    
    # Generate x points for different plots
    x_points = np.arange(1000)
    walk_points = np.zeros(200)  # Shorter for random walk
    vector_length = 100
    
    # Run for 1000 frames
    for frame in range(1000):
        # 1. Dynamic sine wave - frequency changes over time
        freq = 0.01 * (1 + 0.5 * np.sin(frame * 0.01))
        sine_data = np.sin(2 * np.pi * freq * x_points + frame * 0.1)
        sine_plot.set_trace("Sine", x_points, sine_data, color="#4CAF50")
        
        # 2. Random noise with envelope
        envelope = 1 + np.sin(2 * np.pi * 0.001 * x_points + frame * 0.05)
        noise = np.random.normal(0, 0.2, len(x_points))
        modulated_noise = noise * envelope
        noise_plot.set_trace("Noise", x_points, modulated_noise, color="#2196F3")
        
        # 3. Random walk
        walk_points = np.roll(walk_points, -1)
        walk_points[-1] = walk_points[-2] + np.random.normal(0, 0.1)
        walk_plot.set_trace("Walk", np.arange(len(walk_points)), walk_points, color="#9C27B0")
        
        # 4. Spinning vector
        angle = frame * 0.1
        radius = 1 + 0.5 * np.sin(frame * 0.05)
        x_vec = radius * np.cos(np.linspace(0, angle, vector_length))
        y_vec = radius * np.sin(np.linspace(0, angle, vector_length))
        vector_plot.set_trace("Vector", x_vec, y_vec, color="#FF5722")
        
        # Update progress every 20 frames
        if frame % 20 == 0:
            progress = (frame / 1000) * 100
            set_test_progress(progress, f"Frame {frame}/1000")
            
        # Small wait to prevent overwhelming the UI
        wait(35)  # 20ms wait
    
    set_test_progress(100, "Test complete!")
    result.status = "Pass"
    return True