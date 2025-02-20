import numpy as np

def run_test(test):
    """
    Enhanced Plot Animation Test with evolving mathematical patterns.
    
    This test creates two results—each with one plot and one analysis table.
    Each result is updated over four sections (each ~5 seconds long), showing
    real-time plot updates and table updates. The first result finishes as PASS,
    while the second is marked as FAIL.
    
    Color scheme for traces:
      - "#02FEE4"
      - "#4BFF36"
      - "#FF9535"
      - "#F23CA6"
      - "#5E57FF"
    """
    colors = ["#02FEE4", "#4BFF36", "#FF9535", "#F23CA6", "#5E57FF"]
    x_points = np.linspace(0, 10, 1000)
    frames_per_section = 150  # Approximately 5 seconds if wait time is 30 ms
    
    # --- Helper Pattern Functions ---
    def harmonic_pattern(idx, frame, x):
        harmonic = idx + 1
        amplitude = 1.0 / harmonic
        phase = frame * 0.02 * harmonic
        y = amplitude * np.sin(harmonic * x + phase)
        return y * np.exp(-0.1 * x)
    
    def interference_pattern(idx, frame, x):
        freq1 = 1 + idx * 0.5
        freq2 = 2 + idx * 0.3
        y = np.sin(freq1 * x + frame * 0.05) + np.sin(freq2 * x - frame * 0.03)
        return y * np.cos(0.5 * x + frame * 0.02)
    
    def lissajous_pattern(idx, frame, x):
        t = frame * 0.02
        freq = 1 + idx * 0.2
        y = np.sin(freq * x + t) * np.cos((idx + 1) * x - t)
        envelope = 1 - 0.5 * np.cos(0.2 * x)
        return y * envelope
    
    def convergence_pattern(idx, frame, x):
        convergence = frame / frames_per_section
        base_freq = 2 + idx * 0.5
        phase = frame * 0.03
        complex_pattern = np.sin(base_freq * x + phase) * np.cos((5-idx) * x - phase)
        simple_pattern = np.sin(base_freq * x + phase)
        y = (1 - convergence) * complex_pattern + convergence * simple_pattern
        return y * (1 + 0.5 * np.sin(0.1 * x + phase))
    
    # --- Create and update Result 1 (expected PASS) ---
    result1 = test.create_result("Evolving Plot Test - Result 1")
    result1.show()
    
    plot1 = test.create_plot("Symphony 1")
    plot1.x_label = "Time (s)"
    plot1.y_label = "Amplitude"
    plot1.title = "Symphony 1"
    plot1.x_unit = "s"
    plot1.y_unit = "A.U."
    plot1.grid_enabled = True
    plot1.legend_enabled = True
    plot1.roi_visible = True
    result1.add(plot1)
    
    table1 = test.create_table("Analysis 1")
    table1.columns = ["Section", "Pattern Type", "Max Amplitude", "Frequency"]
    result1.add(table1)
    
    # Initialize traces in plot1
    for idx, col in enumerate(colors):
        plot1.set_trace(f"Trace{idx+1}", x_points, np.zeros_like(x_points), color=col)
    
    result1.progress = 0
    
    # Section 1: Harmonic Series Evolution
    for frame in range(frames_per_section):
        progress = frame / frames_per_section
        for idx, col in enumerate(colors):
            y = harmonic_pattern(idx, frame, x_points)
            plot1.set_trace(f"Trace{idx+1}", x_points, y, color=col)
        test.wait(30)
        result1.progress = int(progress * 25)
    table1.add_row(["Section 1", "Harmonic Series", "1.0", "1-5 Hz"])
    
    # Section 2: Interference Patterns
    for frame in range(frames_per_section):
        progress = frame / frames_per_section
        for idx, col in enumerate(colors):
            y = interference_pattern(idx, frame, x_points)
            plot1.set_trace(f"Trace{idx+1}", x_points, y, color=col)
        test.wait(30)
        result1.progress = 25 + int(progress * 25)
    table1.add_row(["Section 2", "Interference", "2.0", "1.5-3.5 Hz"])
    
    # Section 3: Lissajous-inspired Patterns
    for frame in range(frames_per_section):
        progress = frame / frames_per_section
        for idx, col in enumerate(colors):
            y = lissajous_pattern(idx, frame, x_points)
            plot1.set_trace(f"Trace{idx+1}", x_points, y, color=col)
        test.wait(30)
        result1.progress = 50 + int(progress * 25)
    table1.add_row(["Section 3", "Lissajous", "1.0", "1.2-2.0 Hz"])
    
    # Section 4: Final Convergence
    for frame in range(frames_per_section):
        progress = frame / frames_per_section
        for idx, col in enumerate(colors):
            y = convergence_pattern(idx, frame, x_points)
            plot1.set_trace(f"Trace{idx+1}", x_points, y, color=col)
        test.wait(30)
        result1.progress = 75 + int(progress * 25)
    table1.add_row(["Section 4", "Convergence", "1.5", "2.0-4.5 Hz"])
    
    result1.progress = 100
    result1.status = "PASS"
    
    # --- Create and update Result 2 (expected FAIL) ---
    result2 = test.create_result("Evolving Plot Test - Result 2")
    result2.show()
    
    plot2 = test.create_plot("Symphony 2")
    plot2.x_label = "Time (s)"
    plot2.y_label = "Amplitude"
    plot2.title = "Symphony 2"
    plot2.x_unit = "s"
    plot2.y_unit = "A.U."
    plot2.grid_enabled = True
    plot2.legend_enabled = True
    plot2.roi_visible = True
    result2.add(plot2)
    
    table2 = test.create_table("Analysis 2")
    table2.columns = ["Section", "Pattern Type", "Max Amplitude", "Frequency"]
    result2.add(table2)
    
    # Initialize traces in plot2
    for idx, col in enumerate(colors):
        plot2.set_trace(f"Trace{idx+1}", x_points, np.zeros_like(x_points), color=col)
    
    result2.progress = 0
    
    # Section 1: Harmonic Series Evolution
    for frame in range(frames_per_section):
        progress = frame / frames_per_section
        for idx, col in enumerate(colors):
            y = harmonic_pattern(idx, frame, x_points)
            plot2.set_trace(f"Trace{idx+1}", x_points, y, color=col)
        test.wait(30)
        result2.progress = int(progress * 25)
    table2.add_row(["Section 1", "Harmonic Series", "1.0", "1-5 Hz"])
    
    # Section 2: Interference Patterns
    for frame in range(frames_per_section):
        progress = frame / frames_per_section
        for idx, col in enumerate(colors):
            y = interference_pattern(idx, frame, x_points)
            plot2.set_trace(f"Trace{idx+1}", x_points, y, color=col)
        test.wait(30)
        result2.progress = 25 + int(progress * 25)
    table2.add_row(["Section 2", "Interference", "2.0", "1.5-3.5 Hz"])
    
    # Section 3: Lissajous-inspired Patterns
    for frame in range(frames_per_section):
        progress = frame / frames_per_section
        for idx, col in enumerate(colors):
            y = lissajous_pattern(idx, frame, x_points)
            plot2.set_trace(f"Trace{idx+1}", x_points, y, color=col)
        test.wait(30)
        result2.progress = 50 + int(progress * 25)
    table2.add_row(["Section 3", "Lissajous", "1.0", "1.2-2.0 Hz"])
    
    # Section 4: Final Convergence (simulate failure by slightly distorting the pattern)
    for frame in range(frames_per_section):
        progress = frame / frames_per_section
        for idx, col in enumerate(colors):
            t = frame * 0.02
            base_freq = 2 + idx * 0.5
            # Introduce a phase error to simulate a failure.
            phase = frame * 0.05  
            complex_pattern = np.sin(base_freq * x_points + phase) * np.cos((5-idx) * x_points - phase)
            simple_pattern = np.sin(base_freq * x_points + phase)
            y = 0.5 * complex_pattern + 0.5 * simple_pattern
            plot2.set_trace(f"Trace{idx+1}", x_points, y, color=col)
        test.wait(30)
        result2.progress = 75 + int(progress * 25)
    table2.add_row(["Section 4", "Convergence", "1.5", "2.0-4.5 Hz"])
    
    result2.progress = 100
    result2.status = "PASS"
    
    return True
