import numpy as np

def run_test(test):
    """
    Celestial Dance
    An intricate animation of celestial bodies dancing through space,
    incorporating orbital mechanics and golden ratio harmonies.
    """
    # Create and configure the result container
    result = test.create_result("Celestial Dance")
    plot = test.create_plot("Celestial Dance")
    plot.x_label = "Space (AU)"
    plot.y_label = "Space (AU)"
    plot.xlim = (-5, 5)
    plot.ylim = (-5, 5)

    result.add(plot)
    
    # Create analysis table with celestial themes
    table = test.create_table("Celestial Analysis")
    table.columns = ["Celestial Phase", "Mathematical Theme", "Cosmic Energy", "Complexity"]
    
    # Add initial phase
    table.add_row([
        "Solar Birth",
        "Golden Spiral Genesis",
        "Primordial Creation",
        "Emerging"
    ])
    
    result.show()
    
    # Celestial color scheme
    colors = ["#02FEE4", "#4BFF36", "#FF9535", "#F23CA6", "#5E57FF"]
    points = 1000
    golden_ratio = (1 + np.sqrt(5)) / 2
    
    # Initialize traces
    for idx, color in enumerate(colors):
        plot.set_trace(f"Celestial{idx+1}", np.zeros(points), np.zeros(points), color=color)
    
    def create_spiral_orbit(t, base_radius, frequency, phase, evolution):
        """Generate evolving spiral patterns with orbital mechanics"""
        angle = np.linspace(0, t * 2 * np.pi, points)
        radius = base_radius * (1 + 0.3 * np.sin(frequency * angle + phase))
        spiral = 0.1 * angle * np.exp(evolution * np.cos(angle / golden_ratio))
        return radius * spiral
        
    def create_planetary_orbit(t, a, e, phase):
        """Generate elliptical orbit using orbital mechanics"""
        theta = np.linspace(0, 2 * np.pi, points)
        r = a * (1 - e**2) / (1 + e * np.cos(theta + phase))
        return r
        
    total_frames = 1200
    for frame in range(total_frames):
        t = frame * 0.02
        progress = frame / total_frames
        
        # Add new phases to the table at key moments
        if frame == 250:
            table.add_row([
                "Orbital Harmony",
                "Kepler's Waltz",
                "Gravitational Dance",
                "Resonant"
            ])
        elif frame == 500:
            table.add_row([
                "Galactic Spin",
                "Spiral Arm Evolution",
                "Cosmic Rotation",
                "Dynamic"
            ])
        elif frame == 750:
            table.add_row([
                "Nebula Weaving",
                "Quantum Harmonics",
                "Stellar Winds",
                "Complex"
            ])
        elif frame == 1000:
            table.add_row([
                "Cosmic Unity",
                "Universal Harmony",
                "Transcendent Flow",
                "Infinite"
            ])
        
        # Phase transitions
        phase1 = np.clip(frame / 250, 0, 1)
        phase2 = np.clip((frame - 250) / 250, 0, 1)
        phase3 = np.clip((frame - 500) / 250, 0, 1)
        phase4 = np.clip((frame - 750) / 250, 0, 1)
        phase5 = np.clip((frame - 1000) / 200, 0, 1)
        
        for idx, color in enumerate(colors):
            # Base parameters unique to each celestial body
            body_phase = idx * 2 * np.pi / len(colors)
            frequency = 1 + idx * 0.5
            
            # Time-varying parameters
            theta = np.linspace(0, 2 * np.pi * (idx + 1), points)
            evolution = 0.1 + 0.05 * np.sin(t * frequency)
            
            # Phase 1: Spiral Genesis
            spiral = create_spiral_orbit(t, 1 + 0.2 * idx, frequency, body_phase, evolution)
            x1 = spiral * np.cos(theta + t)
            y1 = spiral * np.sin(theta + t)
            
            # Phase 2: Orbital Harmony
            orbit = create_planetary_orbit(t, 2 + 0.5 * idx, 0.3, body_phase)
            x2 = orbit * np.cos(theta + t * frequency)
            y2 = orbit * np.sin(theta + t * frequency)
            
            # Phase 3: Galactic Spin
            r3 = (3 + idx * 0.5) * np.exp(-0.1 * theta)
            x3 = r3 * np.cos(theta + t + body_phase)
            y3 = r3 * np.sin(theta + t + body_phase)
            
            # Phase 4: Nebula Weaving
            r4 = 2 + np.sin(3 * theta + t + body_phase)
            x4 = r4 * np.cos(theta * golden_ratio + t)
            y4 = r4 * np.sin(theta * golden_ratio + t)
            
            # Phase 5: Cosmic Unity
            r5 = 3 * np.sin(theta * frequency + t)
            x5 = r5 * np.cos(theta * golden_ratio + t + body_phase)
            y5 = r5 * np.sin(theta * golden_ratio + t + body_phase)
            
            # Blend all phases smoothly
            x = x1 * (1 - phase2) + x2 * phase2 * (1 - phase3) + \
                x3 * phase3 * (1 - phase4) + x4 * phase4 * (1 - phase5) + x5 * phase5
            y = y1 * (1 - phase2) + y2 * phase2 * (1 - phase3) + \
                y3 * phase3 * (1 - phase4) + y4 * phase4 * (1 - phase5) + y5 * phase5
            
            # Add harmonic modulation
            modulation = 1 + 0.2 * np.sin(5 * theta + t * frequency)
            x *= modulation
            y *= modulation
            
            # Update trace
            plot.set_trace(f"Celestial{idx+1}", x, y, color=color)
        
        test.wait(20)
        result.progress = int((frame + 1) / total_frames * 100)
    
    result.status = "PASS"
    return True