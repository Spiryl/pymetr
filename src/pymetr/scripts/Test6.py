import numpy as np

def run_test():
    """
    Visual showcase of real-time plotting capabilities with upgraded, dynamic animations.
    
    The first part animates a set of Rainbow Lissajous curves with moving markers.
    The second part animates a pulsating Wave Interference pattern with sparkle points 
    and a sweeping peak marker.
    """
    # Initialize result variables for error handling
    lissajous_result = None
    wave_result = None

    try:
        # Create a main group to hold both demos
        main_group = create_group("Visual Showcase")
        
        # =====================================================
        # PART 1: Rainbow Lissajous Animation with Moving Markers
        # =====================================================
        lissajous_result = create_result("Lissajous Patterns")
        main_group.add(lissajous_result)
        
        lissajous_plot = create_plot("Dynamic Rainbow Lissajous")
        lissajous_plot.x_label = "X Position"
        lissajous_plot.y_label = "Y Position"
        lissajous_plot.grid_enabled = True
        lissajous_plot.legend_enabled = True
        lissajous_result.add(lissajous_plot)
        
        # Define the time array for generating the curves
        t = np.linspace(0, 2*np.pi, 1000)
        # Increase the number of animation frames for a smoother effect
        phases = np.linspace(0, 4*np.pi, 300)
        # Base colors that will be cycled and shifted as the animation evolves
        base_colors = ["#FF1493", "#00FF00", "#4169E1", "#FFD700", "#FF4500"]
        
        for i, phase in enumerate(phases):
            # Use the first half (0-50%) of the overall progress for this animation
            progress = (i / len(phases)) * 50
            set_test_progress(progress, "Animating Rainbow Lissajous Patterns...")
            
            # Loop over a set of frequency pairs to create multiple curves
            for j, (freq_x, freq_y) in enumerate([(2, 3), (3, 4), (5, 4), (5, 6)]):
                # Compute the full curve for the current phase
                x = np.sin(freq_x * t + phase)
                y = np.cos(freq_y * t + phase)
                
                # Dynamically vary the line width and opacity to add visual depth
                dynamic_width = 2 + 1.5 * np.sin(phase + j)
                dynamic_opacity = 0.5 + 0.5 * (np.cos(phase + j) * 0.5 + 0.5)
                # Cycle through the color list, shifting with the phase
                color_index = (j + int(phase * 10)) % len(base_colors)
                color = base_colors[color_index]
                
                # Update (or create) the curve trace for this pattern
                lissajous_plot.set_trace(
                    f"Lissajous Curve {j+1}",
                    x, y,
                    color=color,
                    width=int(dynamic_width),
                    style="solid",
                    opacity=dynamic_opacity
                )
                
                # Add a moving marker along the curve.
                # The marker's index advances with the animation so it seems to travel along the curve.
                marker_index = int((i / len(phases)) * (len(t) - 1))
                marker_x = x[marker_index]
                marker_y = y[marker_index]
                lissajous_plot.set_trace(
                    f"Marker {j+1}",
                    np.array([marker_x]),
                    np.array([marker_y]),
                    color=color,
                    width=12,            # Marker size
                    style="solid",
                    marker_style="o"     # Circular marker
                )
            
            wait(30)  # A shorter wait creates a smoother animation
        
        lissajous_result.status = "Pass"
        
        # =====================================================
        # PART 2: Wave Interference Animation with Pulsating Envelope
        # =====================================================
        wave_result = create_result("Wave Interference")
        main_group.add(wave_result)
        
        wave_plot = create_plot("Dynamic Wave Interference")
        wave_plot.x_label = "Position"
        wave_plot.y_label = "Amplitude"
        wave_plot.grid_enabled = True
        wave_plot.legend_enabled = True
        wave_result.add(wave_plot)
        
        # Create a fixed x-array for the wave calculations
        x = np.linspace(-10, 10, 1000)
        
        for i, phase in enumerate(phases):
            # Map progress to the range 50%-100% for this second animation segment
            progress = 50 + (i / len(phases)) * 50
            set_test_progress(progress, "Animating Wave Interference Patterns...")
            
            # Modulate the wave amplitude over time
            amp_mod = 1 + 0.3 * np.sin(phase / 2)
            # Define two primary waves with decaying amplitude away from the center
            wave1 = np.sin(x + phase) * np.exp(-0.1 * x**2) * amp_mod
            wave2 = np.cos(2*x - phase) * np.exp(-0.1 * x**2) * amp_mod
            interference = wave1 + wave2
            # A dynamic envelope that pulsates in amplitude with the phase
            envelope = (2 + 0.5 * np.sin(phase)) * np.exp(-0.1 * x**2)
            
            wave_plot.set_trace(
                "Wave 1",
                x, wave1,
                color="#FF1493",
                width=2,
                style="solid",
                opacity=0.5
            )
            
            wave_plot.set_trace(
                "Wave 2",
                x, wave2,
                color="#4169E1",
                width=2,
                style="solid",
                opacity=0.5
            )
            
            wave_plot.set_trace(
                "Interference",
                x, interference,
                color="#FFD700",
                width=3,
                style="solid"
            )
            
            wave_plot.set_trace(
                "Envelope",
                x, envelope,
                color="#FF4500",
                width=2,
                style="dash",
                opacity=0.7
            )
            
            wave_plot.set_trace(
                "Negative Envelope",
                x, -envelope,
                color="#FF4500",
                width=2,
                style="dash",
                opacity=0.7
            )
            
            # Add some sparkling oscillating points around the pattern
            for k in range(5):
                point_x = 5 * np.sin(phase + k * 2 * np.pi / 5)
                point_y = 5 * np.cos(phase + k * 2 * np.pi / 5)
                wave_plot.set_trace(
                    f"Sparkle {k+1}",
                    np.array([point_x]),
                    np.array([point_y]),
                    color="#00FF00",
                    width=10,
                    style="solid",
                    marker_style="o"
                )
            
            # Add a moving marker that sweeps across the x-axis.
            # This marker highlights a moving “peak” of the interference pattern.
            peak_index = int((i / len(phases)) * len(x))
            peak_marker_x = x[peak_index]
            peak_marker_y = interference[peak_index]
            wave_plot.set_trace(
                "Moving Peak",
                np.array([peak_marker_x]),
                np.array([peak_marker_y]),
                color="#FFFFFF",  # White for contrast
                width=14,
                style="solid",
                marker_style="*"
            )
            
            wait(30)
        
        wave_result.status = "Pass"
        set_test_progress(100, "Visual showcase complete!")
        return True

    except Exception as e:
        # If an error occurs, mark the respective results as having errors
        if lissajous_result:
            lissajous_result.status = "Error"
        if wave_result:
            wave_result.status = "Error"
        return False
