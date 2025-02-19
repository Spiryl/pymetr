import numpy as np

def run_test(test):
    """
    Real-time Multi-Plot Test with interactive markers and cursors.
    Creates 4 different plots that update in real-time:
    1. Sine wave with varying frequency + peak markers
    2. Random noise with envelope + threshold cursors
    3. Random walk + position markers
    4. Spinning vector plot + radius markers
    """
    
    # Create a result for our plots
    result = test.create_result("Real-Time Plots")
    result.progress = 0
    
    # Create 4 plots with basic setup
    sine_plot = test.create_plot("Dynamic Sine Wave")
    sine_plot.x_label = "Sample"
    sine_plot.y_label = "Amplitude"
    sine_plot.y_unit = "Volts"
    sine_plot.x_unit = "Seconds"
    
    # Add threshold cursors to show amplitude bounds
    upper_cursor = test.create_cursor("Upper Bound")
    upper_cursor.axis = 'y'
    upper_cursor.position = 1.0
    upper_cursor.color = "#FF4081"
    upper_cursor.style = "dash"
    
    lower_cursor = test.create_cursor("Lower Bound")
    lower_cursor.axis = 'y'
    lower_cursor.position = -1.0
    lower_cursor.color = "#FF4081"
    lower_cursor.style = "dash"
    
    noise_plot = test.create_plot("Modulated Noise")
    noise_plot.x_label = "Sample"
    noise_plot.y_label = "Amplitude"
    
    # Add envelope cursors
    upper_env = test.create_cursor("Upper Envelope")
    upper_env.axis = 'y'
    upper_env.position = 1.0
    upper_env.color = "#2196F3"
    upper_env.style = "dot"
    
    lower_env = test.create_cursor("Lower Envelope")
    lower_env.axis = 'y'
    lower_env.position = -1.0
    lower_env.color = "#2196F3"
    lower_env.style = "dot"
    
    walk_plot = test.create_plot("Random Walk")
    walk_plot.x_label = "Time"
    walk_plot.y_label = "Position"
    
    vector_plot = test.create_plot("Spinning Vector")
    vector_plot.x_label = "X Position"
    vector_plot.y_label = "Y Position"
    
    # Generate x points for different plots
    x_points = np.arange(1000)
    walk_points = np.zeros(200)  # Shorter for random walk
    vector_length = 100
    
    # Create traces (note: we initialize with empty data as a tuple)
    sine_trace = test.create_trace("Sine", ([], []), color="#4CAF50")
    noise_trace = test.create_trace("Noise", ([], []), color="#2196F3")
    walk_trace = test.create_trace("Walk", ([], []), color="#9C27B0")
    vector_trace = test.create_trace("Vector", ([], []), color="#FF5722")
    
    # Create peak markers for sine wave
    peak_marker = test.create_marker("Peak")
    peak_marker.color = "#4CAF50"
    peak_marker.symbol = "t"  # triangle
    
    trough_marker = test.create_marker("Trough")
    trough_marker.color = "#4CAF50"
    trough_marker.symbol = "t"
    
    # Create markers for random walk extremes
    max_pos = test.create_marker("Max Position")
    max_pos.color = "#9C27B0"
    max_pos.symbol = "d"  # diamond
    
    min_pos = test.create_marker("Min Position")
    min_pos.color = "#9C27B0"
    min_pos.symbol = "d"
    
    # Create radius markers for vector plot
    radius_marker = test.create_marker("Radius")
    radius_marker.color = "#FF5722"
    radius_marker.symbol = "o"
    
    # Run for 1000 frames
    for frame in range(1000):
        # 1. Dynamic sine wave - frequency changes over time
        freq = 0.01 * (1 + 0.5 * np.sin(frame * 0.01))
        sine_data = np.sin(2 * np.pi * freq * x_points + frame * 0.1)
        sine_trace.data = (x_points, sine_data)
        
        # Update peak/trough markers
        peak_idx = np.argmax(sine_data)
        trough_idx = np.argmin(sine_data)
        
        peak_marker.x = x_points[peak_idx]
        peak_marker.y = sine_data[peak_idx]
        trough_marker.x = x_points[trough_idx]
        trough_marker.y = sine_data[trough_idx]
        
        # 2. Random noise with envelope
        envelope = 1 + np.sin(2 * np.pi * 0.001 * x_points + frame * 0.05)
        noise = np.random.normal(0, 0.2, len(x_points))
        modulated_noise = noise * envelope
        noise_trace.data = (x_points, modulated_noise)
        
        # Update envelope cursors
        upper_env.position = 1 + envelope.max()
        lower_env.position = -(1 + envelope.max())
        
        # 3. Random walk
        walk_points = np.roll(walk_points, -1)
        walk_points[-1] = walk_points[-2] + np.random.normal(0, 0.1)
        walk_trace.data = (np.arange(len(walk_points)), walk_points)
        
        # Update position markers
        max_idx = np.argmax(walk_points)
        min_idx = np.argmin(walk_points)
        
        max_pos.x = max_idx
        max_pos.y = walk_points[max_idx]
        min_pos.x = min_idx
        min_pos.y = walk_points[min_idx]
        
        # 4. Spinning vector
        angle = frame * 0.1
        radius = 1 + 0.5 * np.sin(frame * 0.05)
        x_vec = radius * np.cos(np.linspace(0, angle, vector_length))
        y_vec = radius * np.sin(np.linspace(0, angle, vector_length))
        vector_trace.data = (x_vec, y_vec)
        
        # Update radius marker
        radius_marker.x = x_vec[-1]
        radius_marker.y = y_vec[-1]
        radius_marker.uncertainty_visible = True
        radius_marker.uncertainty_upper = 0.1
        radius_marker.uncertainty_lower = 0.1
        
        # Update progress every 20 frames
        if frame % 20 == 0:
            test.progress = (frame / 1000) * 100
            
        # Small wait to prevent overwhelming the UI
        test.wait(30)
    
    test.progress = 100
    result.status = 'PASS'
    return True
