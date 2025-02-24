import numpy as np

def run_test(test):
    """
    Enhanced Plot Animation Test with evolving mathematical patterns
    Features multiple sections with different mathematical behaviors
    """
    # Create a result container and show it
    result = test.create_result("Complex Evolving Plot Test")
    result.show()
    
    # Create a plot and add it to the result
    plot = test.create_plot("Symphony")
    plot.x_label = "Time (s)"
    plot.y_label = "Amplitude"
    result.add(plot)

    # Set plot properties
    plot.title = "Symphony"
    plot.x_unit = "s"
    plot.y_unit = "A.U."
    plot.grid_enabled = True
    plot.legend_enabled = True
    plot.roi_visible = True

    # Create analysis table
    table = test.create_table("Pattern Analysis")
    result.add(table)
    table.columns = ["Section", "Pattern Type", "Max Amplitude", "Frequency"]

    # Define our color scheme
    colors = ["#02FEE4", "#4BFF36", "#FF9535", "#F23CA6", "#5E57FF"]
    x_points = np.linspace(0, 10, 1000)

    # Initialize traces
    for idx, col in enumerate(colors):
        plot.set_trace(f"Trace{idx+1}", x_points, np.zeros_like(x_points), color=col)

    # Section 1: Harmonic Series Evolution (0-250 frames)
    for frame in range(250):
        progress = frame / 250
        for idx, col in enumerate(colors):
            harmonic = idx + 1
            amplitude = 1.0 / harmonic
            phase = frame * 0.02 * harmonic
            y_data = amplitude * np.sin(harmonic * x_points + phase)
            y_data *= np.exp(-0.1 * x_points)  # Decay envelope
            plot.set_trace(f"Trace{idx+1}", x_points, y_data, color=col)
        test.wait(30)
        result.progress = int(progress * 25)

    # Section 2: Interference Patterns (250-500 frames)
    for frame in range(250):
        progress = frame / 250
        for idx, col in enumerate(colors):
            freq1 = 1 + idx * 0.5
            freq2 = 2 + idx * 0.3
            y_data = np.sin(freq1 * x_points + frame * 0.05) + \
                     np.sin(freq2 * x_points - frame * 0.03)
            y_data *= np.cos(0.5 * x_points + frame * 0.02)  # Modulation
            plot.set_trace(f"Trace{idx+1}", x_points, y_data, color=col)
        test.wait(30)
        result.progress = 25 + int(progress * 25)

    # Section 3: Lissajous-inspired Patterns (500-750 frames)
    for frame in range(250):
        progress = frame / 250
        for idx, col in enumerate(colors):
            t = frame * 0.02
            freq = 1 + idx * 0.2
            y_data = np.sin(freq * x_points + t) * \
                     np.cos((idx + 1) * x_points - t)
            envelope = 1 - 0.5 * np.cos(0.2 * x_points)
            y_data *= envelope
            plot.set_trace(f"Trace{idx+1}", x_points, y_data, color=col)
        test.wait(30)
        result.progress = 50 + int(progress * 25)

    # Section 4: Final Convergence (750-1000 frames)
    for frame in range(250):
        progress = frame / 250
        convergence = frame / 250.0  # Goes from 0 to 1
        for idx, col in enumerate(colors):
            base_freq = 2 + idx * 0.5
            phase = frame * 0.03
            # Start with complex pattern and converge to simple sine
            complex_pattern = np.sin(base_freq * x_points + phase) * \
                            np.cos((5-idx) * x_points - phase)
            simple_pattern = np.sin(base_freq * x_points + phase)
            y_data = (1 - convergence) * complex_pattern + \
                     convergence * simple_pattern
            # Add final flourish
            y_data *= (1 + 0.5 * np.sin(0.1 * x_points + phase))
            plot.set_trace(f"Trace{idx+1}", x_points, y_data, color=col)
        test.wait(30)
        result.progress = 75 + int(progress * 25)

    # Update analysis table with section information
    table.add_row(["Section 1", "Harmonic Series", "1.0", "1-5 Hz"])
    table.add_row(["Section 2", "Interference", "2.0", "1.5-3.5 Hz"])
    table.add_row(["Section 3", "Lissajous", "1.0", "1.2-2.0 Hz"])
    table.add_row(["Section 4", "Convergence", "1.5", "2.0-4.5 Hz"])

    result.progress = 100
    result.status = "PASS"
    return True