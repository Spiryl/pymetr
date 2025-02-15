import numpy as np

def run_test():
    """
    Cosmic Visual Showcase
    ------------------------
    This demo consists of two parts:

    1. Celestial Orbits:
       Simulates a mini solar system where several "planets" orbit a central star.
       Their orbits, dynamic trails, and speeds change over time to create an engaging animation.
       
    2. Cosmic Nebula:
       Creates an abstract nebula effect by combining interference patterns.
       Shifting contour lines and a pulsating core produce a vibrant, otherworldly display.
    """
    celestial_result = None
    nebula_result = None

    try:
        # Create a main group for the cosmic visual showcase.
        main_group = create_group("Cosmic Visual Showcase")
        
        # =====================================================
        # PART 1: Celestial Orbits Animation
        # =====================================================
        celestial_result = create_result("Celestial Orbits")
        main_group.add(celestial_result)
        
        celestial_plot = create_plot("Celestial Orbits")
        celestial_plot.x_label = "X Coordinate"
        celestial_plot.y_label = "Y Coordinate"
        celestial_plot.grid_enabled = True
        celestial_plot.legend_enabled = True
        celestial_result.add(celestial_plot)
        
        # Setup parameters for our "planetary system"
        center_x, center_y = 0, 0
        num_planets = 5
        # Radii for each planet's orbit (from inner to outer)
        radii = np.linspace(2, 10, num_planets)
        # Angular speeds (radians per frame) differ for each planet
        angular_speeds = np.linspace(0.02, 0.1, num_planets)
        
        # Prepare arrays to store past positions for trailing effects.
        trails_length = 100
        trails = [np.zeros((trails_length, 2)) for _ in range(num_planets)]
        
        # Animate over a number of frames.
        frames = 300
        for frame in range(frames):
            progress = (frame / frames) * 50
            set_test_progress(progress, "Animating Celestial Orbits...")
            
            for i in range(num_planets):
                # Compute the current angle for each planet.
                angle = angular_speeds[i] * frame
                planet_x = center_x + radii[i] * np.cos(angle)
                planet_y = center_y + radii[i] * np.sin(angle)
                
                # Update the trail for the planet (simulate fading by shifting positions).
                trails[i] = np.roll(trails[i], shift=-1, axis=0)
                trails[i][-1, :] = [planet_x, planet_y]
                
                # Draw the orbit circle (for reference) as a dashed line.
                theta = np.linspace(0, 2 * np.pi, 200)
                orbit_x = center_x + radii[i] * np.cos(theta)
                orbit_y = center_y + radii[i] * np.sin(theta)
                celestial_plot.set_trace(
                    f"Orbit {i+1}",
                    orbit_x, orbit_y,
                    color="#888888",
                    width=1,
                    style="dash",
                    opacity=0.3
                )
                
                # Draw the trail (using a unique color per planet).
                # Here, we mix colors based on the planet index.
                r = int(128 + 127 * (i / num_planets))
                b = int(128 + 127 * (1 - i / num_planets))
                trail_color = f"#{r:02X}80{b:02X}"
                trail_x = trails[i][:, 0]
                trail_y = trails[i][:, 1]
                celestial_plot.set_trace(
                    f"Trail {i+1}",
                    trail_x, trail_y,
                    color=trail_color,
                    width=2,
                    style="solid",
                    opacity=0.6
                )
                
                # Draw the planet as a bright marker.
                celestial_plot.set_trace(
                    f"Planet {i+1}",
                    np.array([planet_x]),
                    np.array([planet_y]),
                    color="#FFFF00",  # Bright yellow
                    width=12,
                    style="solid",
                    marker_style="o"
                )
            wait(40)  # Pause briefly for smooth animation
        
        celestial_result.status = "Pass"
        
        # =====================================================
        # PART 2: Cosmic Nebula Animation
        # =====================================================
        nebula_result = create_result("Cosmic Nebula")
        main_group.add(nebula_result)
        
        nebula_plot = create_plot("Cosmic Nebula")
        nebula_plot.x_label = "X Coordinate"
        nebula_plot.y_label = "Y Coordinate"
        nebula_plot.grid_enabled = False  # A clean background is preferred.
        nebula_plot.legend_enabled = False
        nebula_result.add(nebula_plot)
        
        # Create a grid for our nebula simulation.
        x_vals = np.linspace(-10, 10, 400)
        y_vals = np.linspace(-10, 10, 400)
        X, Y = np.meshgrid(x_vals, y_vals)
        
        nebula_frames = 300
        for frame in range(nebula_frames):
            progress = 50 + (frame / nebula_frames) * 50
            set_test_progress(progress, "Animating Cosmic Nebula...")
            
            phase = frame * 0.1
            # Generate two interference patterns.
            Z1 = np.sin(0.5 * X + phase) * np.cos(0.5 * Y + phase)
            Z2 = np.sin(np.sqrt(X**2 + Y**2) - phase)
            # Combine the patterns to simulate a nebula texture.
            Z = (Z1 + Z2) / 2.0
            
            # Extract several contour "slices" from the nebula.
            contour_levels = np.linspace(np.min(Z), np.max(Z), 10)
            for idx, level in enumerate(contour_levels):
                # Identify points near the contour level.
                mask = np.abs(Z - level) < 0.1
                if np.sum(mask) < 10:
                    continue  # Skip if too few points.
                contour_x = X[mask].flatten()
                contour_y = Y[mask].flatten()
                # Create a shifting color based on phase and contour index.
                r = int(128 + 127 * np.sin(phase + idx))
                g = int(128 + 127 * np.sin(phase + idx + 2))
                b = int(128 + 127 * np.sin(phase + idx + 4))
                color = f"#{r:02X}{g:02X}{b:02X}"
                
                nebula_plot.set_trace(
                    f"Contour {idx}",
                    contour_x, contour_y,
                    color=color,
                    width=1,
                    style="solid",
                    opacity=0.4
                )
            
            # Add a pulsating core at the center.
            core_intensity = 1 + 0.5 * np.sin(2 * phase)
            nebula_plot.set_trace(
                "Nebula Core",
                np.array([0]),
                np.array([0]),
                color="#FFFFFF",
                width=int(10 * core_intensity),
                style="solid",
                marker_style="o",
                opacity=0.8
            )
            wait(30)
        
        nebula_result.status = "Pass"
        set_test_progress(100, "Cosmic visual showcase complete!")
        return True

    except Exception as e:
        if celestial_result:
            celestial_result.status = "Error"
        if nebula_result:
            nebula_result.status = "Error"
        return False
