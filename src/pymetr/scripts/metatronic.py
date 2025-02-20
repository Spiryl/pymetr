import numpy as np

def run_test(test):
    """
    The Grand Finale: Masterpiece
    --------------------------------
    Creates 5 results. Each result includes a plot and an analysis table.
    Each result is updated over 5 movements (phases) with evolving mathematical patterns.
    At the end of each result, progress is set to 100% and status is marked as PASS.
    
    Signature color scheme (traces):
      "#02FEE4", "#4BFF36", "#FF9535", "#F23CA6", "#5E57FF"
    """
    # --- Configuration ---
    colors = ["#02FEE4", "#4BFF36", "#FF9535", "#F23CA6", "#5E57FF"]
    points = 1000
    golden_ratio = (1 + np.sqrt(5)) / 2
    silver_ratio = 1 + np.sqrt(2)
    
    total_movements = 5
    frames_per_movement = 150  # ~5 seconds per movement if wait=20ms
    
    # --- Define Movement Pattern Functions ---
    def movement_pattern1(t, idx, x):
        # Harmonic decay pattern
        return np.sin((idx+1)*x + t) * np.exp(-0.05 * np.abs(x))
    
    def movement_pattern2(t, idx, x):
        # Interference of sine and cosine waves with a twist
        return np.sin((idx+1)*x + t) + 0.3 * np.cos(x * golden_ratio + t*0.5)
    
    def movement_pattern3(t, idx, x):
        # Product of sine and cosine, creating a Lissajous-like effect
        return np.sin(x * (idx+1) + t) * np.cos(x * silver_ratio + t)
    
    def movement_pattern4(t, idx, x):
        # Harmonic modulation: a sine wave modulated by another sine
        return np.sin((idx+1)*x + t) * (1 + 0.4 * np.sin(0.5*x + t*0.8))
    
    def movement_pattern5(t, idx, x):
        # Composite pattern: sum of two sine waves of different frequencies
        return np.sin((idx+1)*x + t) + 0.35 * np.sin((idx+2)*x + t*1.2)
    
    movement_funcs = [movement_pattern1, movement_pattern2,
                      movement_pattern3, movement_pattern4, movement_pattern5]
    
    # --- Loop over 5 Results ---
    for res_index in range(5):
        # Create the result container
        res_name = f"Masterpiece Result {res_index+1}"
        result = test.create_result(res_name)
        result.show()
        
        # Create and configure the plot for this result.
        plot = test.create_plot(f"Dynamic Plot {res_index+1}")
        plot.x_label = "X Axis"
        plot.y_label = "Y Axis"
        plot.title = f"Evolution {res_index+1}"
        plot.x_unit = ""
        plot.y_unit = ""
        plot.grid_enabled = True
        # Optional: adjust view limits as needed (e.g., plot.x_lim, plot.y_lim)
        result.add(plot)
        
        # Create and configure the analysis table.
        table = test.create_table(f"Analysis {res_index+1}")
        table.columns = ["Movement", "Theme", "Peak Amplitude", "Notes"]
        result.add(table)
        
        # Initialize one trace per color.
        for idx, col in enumerate(colors):
            plot.set_trace(f"Trace{idx+1}", np.zeros(points), np.zeros(points), color=col)
        
        result.progress = 0
        
        # --- Update the result through 5 Movements ---
        for movement in range(total_movements):
            for frame in range(frames_per_movement):
                t = frame * 0.03
                x = np.linspace(-10, 10, points)
                func = movement_funcs[movement % len(movement_funcs)]
                for idx, col in enumerate(colors):
                    y = func(t, idx, x)
                    plot.set_trace(f"Trace{idx+1}", x, y, color=col)
                test.wait(20)
                # Update progress proportionally within this result:
                overall_progress = int(((movement * frames_per_movement + frame + 1) /
                                          (total_movements * frames_per_movement)) * 100)
                result.progress = overall_progress
            # After each movement, add a new row to the analysis table.
            # (Here, we simply use the movement number as theme info; customize as needed.)
            table.add_row([
                f"Movement {movement+1}",
                f"Theme {movement+1}",
                f"{np.max(np.abs(y)):.2f}",
                "Dynamic pattern evolving"
            ])
        
        result.progress = 100
        result.status = "PASS"
    
    return True
