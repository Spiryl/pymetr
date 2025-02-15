import numpy as np

def run_test():
    """
    Visual showcase of real-time plotting capabilities with dynamic patterns.
    """
    try:
        # Create main group and results
        main_group = create_group("Visual Showcase")
        
        # Lissajous Pattern Result
        lissajous_result = create_result("Lissajous Patterns")
        main_group.add(lissajous_result)
        
        # Create Lissajous plot
        lissajous_plot = create_plot("Dynamic Lissajous Patterns")
        lissajous_plot.x_label = "X Position"
        lissajous_plot.y_label = "Y Position"
        lissajous_plot.grid_enabled = True
        lissajous_plot.legend_enabled = True
        lissajous_result.add(lissajous_plot)
        
        # Wave Interference Result
        wave_result = create_result("Wave Interference")
        main_group.add(wave_result)
        
        # Create interference plot
        wave_plot = create_plot("Wave Interference Patterns")
        wave_plot.x_label = "Position"
        wave_plot.y_label = "Amplitude"
        wave_plot.grid_enabled = True
        wave_plot.legend_enabled = True
        wave_result.add(wave_plot)
        
        # Time parameters
        t = np.linspace(0, 2*np.pi, 1000)
        phases = np.linspace(0, 4*np.pi, 200)  # Phase evolution
        
        # Color gradients
        colors = [
            "#FF1493",  # Deep Pink
            "#00FF00",  # Lime
            "#4169E1",  # Royal Blue
            "#FFD700",  # Gold
            "#FF4500"   # Orange Red
        ]
        
        # Animation loop
        for i, phase in enumerate(phases):
            progress = (i / len(phases)) * 100
            set_test_progress(progress, "Creating visual patterns...")
            
            # Lissajous patterns
            for j, (freq_x, freq_y) in enumerate([(2,3), (3,4), (5,4), (5,6)]):
                x = np.sin(freq_x * t + phase)
                y = np.cos(freq_y * t + phase)
                
                # Create gradient effect
                color = colors[j % len(colors)]
                width = 2 + np.sin(phase/2)  # Dynamic line width
                
                lissajous_plot.set_trace(
                    f"Pattern {j+1}",
                    x, y,
                    color=color,
                    width=int(width),
                    style="solid",
                    opacity=0.7
                )
            
            # Wave interference patterns
            x = np.linspace(-10, 10, 1000)
            
            # Primary waves
            wave1 = np.sin(x + phase) * np.exp(-0.1 * x**2)
            wave2 = np.cos(2*x - phase) * np.exp(-0.1 * x**2)
            interference = wave1 + wave2
            
            # Envelope pattern
            envelope = 2 * np.exp(-0.1 * x**2)
            
            # Plot waves
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
            
            # Add some sparkle with oscillating points
            for k in range(5):
                point_x = 5 * np.sin(phase + k*2*np.pi/5)
                point_y = 5 * np.cos(phase + k*2*np.pi/5)
                
                wave_plot.set_trace(
                    f"Point {k+1}",
                    np.array([point_x]),
                    np.array([point_y]),
                    color="#00FF00",
                    width=10,
                    style="solid",
                    marker_style="o"
                )
            
            wait(50)  # Smooth animation
        
        lissajous_result.status = "Pass"
        wave_result.status = "Pass"
        
        set_test_progress(100, "Visual showcase complete!")
        return True
        
    except Exception as e:
        if lissajous_result:
            lissajous_result.status = "Error"
        if wave_result:
            wave_result.status = "Error"
        return False