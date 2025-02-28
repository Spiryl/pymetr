import numpy as np

def run_test(test):
    """
    Enhanced Plot Animation Test with continuously evolving mathematical patterns
    Features smooth transitions between sections and progressive table updates
    """
    # Create a result container and show it
    result = test.create_result("Continuous Evolution")

   
    # Create a plot and add it to the result
    plot = test.create_plot("Mathematical Symphony")
    plot.x_label = "Time (s)"
    plot.y_label = "Amplitude"
    plot.ylim = (-3, 3)
    result.add(plot)

    # Create analysis table with poetic descriptions
    table = test.create_table("Pattern Symphony Analysis")
    result.add(table)
    result.show()

    # Initialize table with headers
    table.columns = ["Movement", "Mathematical Theme", "Emotional Quality", "Peak Complexity"]

    # Define our color scheme
    colors = ["#02FEE4", "#4BFF36", "#FF9535", "#F23CA6", "#5E57FF"]
    x_points = np.linspace(0, 10, 1000)

    # Initialize traces
    for idx, col in enumerate(colors):
        plot.set_trace(f"Voice{idx+1}", x_points, np.zeros_like(x_points), color=col)

    def transition_weight(frame, start_frame, end_frame):
        """Smooth transition function using cosine"""
        if frame < start_frame:
            return 0.0
        if frame > end_frame:
            return 1.0
        progress = (frame - start_frame) / (end_frame - start_frame)
        return 0.5 * (1 - np.cos(np.pi * progress))

    # Animation loop with continuous transitions
    total_frames = 300  # Extended for more elaborate patterns
    
    # Add first movement to table immediately
    table.add_row([
        "Opening Movement",
        "Harmonic Series with Exponential Decay",
        "Awakening, Emergence",
        "Medium"
    ])

    for frame in range(total_frames):
        # Calculate various transition weights
        w1 = transition_weight(frame, 0, 350)
        w2 = transition_weight(frame, 250, 600)
        w3 = transition_weight(frame, 500, 850)
        w4 = transition_weight(frame, 750, 1100)
        w5 = transition_weight(frame, 1000, total_frames)

        # Add table rows at transition points
        if frame == 250:
            table.add_row([
                "Second Movement",
                "Quantum Interference Patterns",
                "Complexity, Interaction",
                "High"
            ])
        elif frame == 500:
            table.add_row([
                "Third Movement",
                "Fractal Self-Similarity",
                "Reflection, Recursion",
                "Very High"
            ])
        elif frame == 750:
            table.add_row([
                "Fourth Movement",
                "Chaotic Attractor Patterns",
                "Tension, Resolution",
                "Extreme"
            ])
        elif frame == 1000:
            table.add_row([
                "Final Movement",
                "Golden Ratio Harmonics",
                "Transcendence, Unity",
                "Ultimate"
            ])

        for idx, col in enumerate(colors):
            # Enhanced parameters that evolve throughout
            t = frame * 0.03  # Increased base frequency
            base_freq = 2.5 + idx * 0.7  # More spread between frequencies
            harmonic = idx + 1
            
            # Pattern 1: Enhanced Harmonic Awakening
            p1 = (1.0 / harmonic) * np.sin(harmonic * x_points * 1.2 + t) * \
                 np.exp(-0.15 * x_points * (1 - w1))
            
            # Pattern 2: Complex Quantum Interference
            p2 = np.sin(base_freq * x_points + t) * \
                 np.cos((idx + 1) * 0.8 * x_points - t * 1.2) * \
                 (1 + 0.7 * np.sin(0.3 * x_points))
            
            # Pattern 3: Intricate Fractal Echoes
            p3 = np.sin(base_freq * x_points + t) * \
                 np.cos(2.5 * x_points - t * 1.3) * \
                 np.sin(0.7 * x_points + t * 0.8)
            
            # Pattern 4: Enhanced Chaotic Harmony
            p4 = np.sin(base_freq * x_points + np.sin(t * 0.15) * x_points * 1.5) * \
                 (1 + 0.8 * np.cos(0.4 * x_points - t * 0.9))
            
            # Pattern 5: Complex Mathematical Transcendence
            golden_ratio = (1 + np.sqrt(5)) / 2
            p5 = np.sin(base_freq * x_points * 1.2 + t) * \
                 np.cos(golden_ratio * x_points * 1.1 - t) * \
                 (1 + 0.5 * np.sin(0.2 * x_points + t)) + \
                 0.7 * np.sin(harmonic * golden_ratio * x_points - t * 0.7) * \
                 np.exp(-0.08 * x_points) * \
                 (1 + 0.3 * np.cos(0.4 * x_points + t * 1.2))

            # Combine patterns with smooth transitions
            y_data = p1 * (1 - w1) + \
                    p2 * (w1 * (1 - w2)) + \
                    p3 * (w2 * (1 - w3)) + \
                    p4 * (w3 * (1 - w4)) + \
                    p5 * w4

            # Enhanced final modulation
            modulation = 1 + 0.4 * w5 * np.sin(0.15 * x_points + t * harmonic * 0.15)
            y_data *= modulation

            # Dynamic amplitude envelope
            envelope = 1 - 0.4 * np.cos(0.25 * x_points + t * 0.15)
            y_data *= envelope

            plot.set_trace(f"Voice{idx+1}", x_points, y_data, color=col)
            
        test.wait(20) 
        result.progress = int((frame + 1) / total_frames * 100)

    result.progress = 100
    result.status = "PASS"
    return True