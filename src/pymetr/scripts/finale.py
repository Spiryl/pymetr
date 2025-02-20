import numpy as np

def run_test(test):
    """
    The Grand Finale
    A dual-plot mathematical symphony showcasing harmonic relationships
    and complex pattern evolution across dimensions.
    """
    # Create the result container
    result = test.create_result("The Grand Finale")
    
    # Create two plots
    plot1 = test.create_plot("Temporal Symphony")
    plot2 = test.create_plot("Spatial Harmony")
    
    # Configure first plot
    plot1.x_label = "Time Dimension"
    plot1.y_label = "Temporal Amplitude"
    plot1.x_unit = "τ"
    plot1.y_unit = "φ"
    plot1.grid_enabled = True
    plot1.grid_alpha = 0.15
    plot1.background_color = "#050510"
    plot1.grid_color = "#101030"
    plot1.foreground_color = "#FFFFFF"
    
    # Configure second plot
    plot2.x_label = "Spatial Dimension"
    plot2.y_label = "Spatial Amplitude"
    plot2.x_unit = "ξ"
    plot2.y_unit = "ψ"
    plot2.grid_enabled = True
    plot2.grid_alpha = 0.15
    plot2.background_color = "#050510"
    plot2.grid_color = "#101030"
    plot2.foreground_color = "#FFFFFF"
    
    # Add plots to result
    result.add(plot1)
    result.add(plot2)
    
    # Create analysis table
    table = test.create_table("Symphony Analysis")
    table.columns = ["Movement", "Mathematical Theme", "Temporal Nature", "Spatial Nature", "Complexity"]
    
    # Add initial analysis
    table.add_row([
        "Opening",
        "Quantum Genesis",
        "Wave Function Birth",
        "Spatial Emergence",
        "Foundational"
    ])
    
    result.show()
    
    # Our signature color scheme
    colors = ["#02FEE4", "#4BFF36", "#FF9535", "#F23CA6", "#5E57FF"]
    points = 1000
    golden_ratio = (1 + np.sqrt(5)) / 2
    silver_ratio = 1 + np.sqrt(2)
    
    # Initialize traces for both plots
    for idx, color in enumerate(colors):
        plot1.set_trace(f"Temporal{idx+1}", np.zeros(points), np.zeros(points), color=color)
        plot2.set_trace(f"Spatial{idx+1}", np.zeros(points), np.zeros(points), color=color)
    
    def create_temporal_evolution(t, idx, phase):
        """Generate complex temporal patterns"""
        theta = np.linspace(0, 8 * np.pi, points)
        frequency = 1 + idx * 0.5
        
        # Primary wave with quantum fluctuations
        wave = np.sin(frequency * theta + t) * np.cos(theta * golden_ratio)
        
        # Add quantum uncertainty
        uncertainty = 0.3 * np.sin(theta * silver_ratio + t * 0.5)
        
        # Add harmonic overtones
        overtones = 0.2 * np.sin(2 * frequency * theta + t * 1.5)
        
        return wave + uncertainty + overtones
    
    def create_spatial_pattern(t, idx, phase):
        """Generate complex spatial patterns"""
        r = np.linspace(0, 4 * np.pi, points)
        base_freq = 2 + idx * 0.7
        
        # Create spiral arms with varying density
        spiral = np.sin(base_freq * r + t) * np.exp(-0.1 * r)
        
        # Add quantum-inspired fluctuations
        quantum = 0.3 * np.cos(r * golden_ratio + t * 0.7)
        
        # Add relativistic corrections
        relativity = 0.2 * np.sin(r * silver_ratio - t * 0.5)
        
        return spiral + quantum + relativity
    
    total_frames = 1800  # Extended for a grand finale
    for frame in range(total_frames):
        t = frame * 0.03
        progress = frame / total_frames
        
        # Add new movement descriptions at key points
        if frame == 400:
            table.add_row([
                "Development",
                "Quantum Interference",
                "Probability Waves",
                "Field Interactions",
                "Intricate"
            ])
        elif frame == 800:
            table.add_row([
                "Evolution",
                "Relativistic Dance",
                "Time Dilation",
                "Space Curvature",
                "Complex"
            ])
        elif frame == 1200:
            table.add_row([
                "Synthesis",
                "Grand Unification",
                "Temporal Weaving",
                "Spatial Braiding",
                "Transcendent"
            ])
        elif frame == 1600:
            table.add_row([
                "Finale",
                "Cosmic Symphony",
                "Time Crystallization",
                "Space Harmonization",
                "Ultimate"
            ])
        
        # Calculate phase transitions
        phase1 = np.clip(frame / 400, 0, 1)
        phase2 = np.clip((frame - 350) / 400, 0, 1)
        phase3 = np.clip((frame - 700) / 400, 0, 1)
        phase4 = np.clip((frame - 1050) / 400, 0, 1)
        phase5 = np.clip((frame - 1400) / 400, 0, 1)
        
        for idx, color in enumerate(colors):
            # Base parameters with complex evolution
            phase = idx * 2 * np.pi / len(colors)
            frequency = (1 + idx * 0.5) * (1 + 0.2 * np.sin(t * 0.1))
            
            # Generate temporal data
            temporal_x = np.linspace(-10, 10, points)
            temporal_y = create_temporal_evolution(t, idx, phase)
            
            # Generate spatial data
            theta = np.linspace(0, 2 * np.pi, points)
            r = create_spatial_pattern(t, idx, phase)
            spatial_x = r * np.cos(theta + t * (1 + 0.1 * np.sin(t * 0.2)))
            spatial_y = r * np.sin(theta + t * (1 + 0.1 * np.cos(t * 0.2)))
            
            # Apply complex modulations
            modulation = (1 + 0.3 * np.sin(5 * theta + t * frequency) * 
                        np.cos(3 * theta + t * 0.5) * 
                        np.sin(theta * golden_ratio + t * 0.3))
            
            # Update both plots with modulated data
            plot1.set_trace(f"Temporal{idx+1}", temporal_x, temporal_y * modulation)
            plot2.set_trace(f"Spatial{idx+1}", spatial_x * modulation, spatial_y * modulation)
        
        # Set appropriate view limits
        if frame == 0:
            plot1.x_lim = (-10, 10)
            plot1.y_lim = (-3, 3)
            plot2.x_lim = (-6, 6)
            plot2.y_lim = (-6, 6)
        
        test.wait(20)
        result.progress = int((frame + 1) / total_frames * 100)
    
    result.status = "PASS"
    return True