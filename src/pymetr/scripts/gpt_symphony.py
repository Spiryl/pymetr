import numpy as np

def run_test(test):
    """
    Ultimate Mathematical Symphony with Enhanced Spirals and Fractal Patterns
    Showcases evolving mathematical beauty with intricate transitions and complex harmonic layers.
    """
    # Create result container and display it
    result = test.create_result("Ultimate Mathematical Symphony")
    
    # Create plot with defined axes and add it to the result
    plot = test.create_plot("Symphony of Spirals")
    plot.x_label = "Time (s)"
    plot.y_label = "Amplitude"
    plot.ylim = (-4, 4)
    result.add(plot)
    
    # Create an analysis table with poetic descriptions
    table = test.create_table("Symphony Movements Analysis")
    result.add(table)
    table.columns = ["Movement", "Mathematical Theme", "Emotional Quality", "Peak Complexity"]
    table.add_row([
        "Movement I",
        "Emergent Harmonics & Spiral Beginnings",
        "Curiosity, Awakening",
        "Moderate"
    ])
    
    result.show()
    
    # Define our consistent color scheme and x-axis data
    colors = ["#02FEE4", "#4BFF36", "#FF9535", "#F23CA6", "#5E57FF"]
    x_points = np.linspace(0, 10, 1000)
    
    # Initialize five voice traces with flat starting lines
    for idx, col in enumerate(colors):
        plot.set_trace(f"Voice{idx+1}", x_points, np.zeros_like(x_points), color=col)
    
    def transition_weight(frame, start_frame, end_frame):
        """Smooth cosine-based transition between 0 and 1"""
        if frame < start_frame:
            return 0.0
        if frame > end_frame:
            return 1.0
        progress = (frame - start_frame) / (end_frame - start_frame)
        return 0.5 * (1 - np.cos(np.pi * progress))
    
    total_frames = 1800  # Extended for even more evolving patterns
    
    # Animation loop with evolving complexity and spiral motifs
    for frame in range(total_frames):
        # Calculate multiple transition weights for smooth blending
        w1 = transition_weight(frame, 0, 300)
        w2 = transition_weight(frame, 250, 600)
        w3 = transition_weight(frame, 550, 900)
        w4 = transition_weight(frame, 850, 1200)
        w5 = transition_weight(frame, 1150, total_frames)
        
        # Add additional table movements at key transition frames
        if frame == 250:
            table.add_row([
                "Movement II",
                "Interwoven Quantum Spirals",
                "Mystery, Intrigue",
                "High"
            ])
        elif frame == 550:
            table.add_row([
                "Movement III",
                "Fractal Reverberations",
                "Contemplation, Recursion",
                "Very High"
            ])
        elif frame == 850:
            table.add_row([
                "Movement IV",
                "Chaotic Attractor & Spiral Vortices",
                "Tension, Uncertainty",
                "Extreme"
            ])
        elif frame == 1150:
            table.add_row([
                "Movement V",
                "Golden Spiral Convergence",
                "Transcendence, Unity",
                "Ultimate"
            ])
        
        # Update each voice with its evolving mathematical pattern
        for idx, col in enumerate(colors):
            t = frame * 0.035  # Adjusted base frequency for smoother evolution
            base_freq = 2.0 + idx * 0.8  # Spread between voices
            
            # Pattern A: Harmonic Spiral Awakening
            pA = (1.0 / (idx + 1)) * np.sin((idx + 1) * x_points * 1.3 + t) * \
                 np.exp(-0.12 * x_points * (1 - w1))
            
            # Pattern B: Quantum Interference with Spiral Modulation
            pB = np.sin(base_freq * x_points + t) * \
                 np.cos((idx + 1) * 0.9 * x_points - t * 1.1) * \
                 (1 + 0.6 * np.sin(0.35 * x_points + t))
            
            # Pattern C: Fractal Echoes and Recursive Spirals
            pC = np.sin(base_freq * x_points + t) * \
                 np.cos(2.8 * x_points - t * 1.4) * \
                 np.sin(0.75 * x_points + t * 0.9)
            
            # Pattern D: Chaotic Attractor with Embedded Spiral Curvature
            spiral_mod = np.sin(0.5 * x_points + t) * np.cos(0.5 * x_points - t)
            pD = np.sin(base_freq * x_points + spiral_mod * x_points * 1.2) * \
                 (1 + 0.7 * np.cos(0.45 * x_points - t * 1.0))
            
            # Pattern E: Golden Ratio Spiral and Harmonic Convergence
            golden = (1 + np.sqrt(5)) / 2
            pE = np.sin(base_freq * x_points * 1.3 + t) * \
                 np.cos(golden * x_points * 1.2 - t) * \
                 (1 + 0.5 * np.sin(0.25 * x_points + t)) + \
                 0.6 * np.sin((idx + 1) * golden * x_points - t * 0.8) * \
                 np.exp(-0.1 * x_points) * \
                 (1 + 0.4 * np.cos(0.35 * x_points + t * 1.1))
            
            # Combine the patterns with smooth transitions across the symphony
            y_data = pA * (1 - w1) + \
                     pB * (w1 * (1 - w2)) + \
                     pC * (w2 * (1 - w3)) + \
                     pD * (w3 * (1 - w4)) + \
                     pE * w4
            
            # Final modulation: integrate subtle spiral undulations over time
            modulation = 1 + 0.35 * w5 * np.sin(0.2 * x_points + t * (idx + 1) * 0.2)
            y_data *= modulation
            
            # Dynamic amplitude envelope for overall smoothness
            envelope = 1 - 0.3 * np.cos(0.3 * x_points + t * 0.2)
            y_data *= envelope
            
            # Update the corresponding trace for this voice
            plot.set_trace(f"Voice{idx+1}", x_points, y_data, color=col)
        
        # Wait a brief moment to render the updated frame
        test.wait(20)
        result.progress = int((frame + 1) / total_frames * 100)
    
    result.progress = 100
    result.status = "PASS"
    return True
