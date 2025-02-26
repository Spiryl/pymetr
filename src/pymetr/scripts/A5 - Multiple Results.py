import numpy as np
# Multiple results with plots and data
def run_test(test):
    """
    A more in-depth test demonstrating:
      - Two separate Result containers
      - Multiple plots in the first Result
      - Multiple traces per plot
      - A single plot + a table in the second Result
      - Animated data updates and progress changes
    """

    # -------------------------
    # 1) FIRST RESULT: 2 PLOTS
    # -------------------------
    result1 = test.create_result("First Result")
    result1.show()

    # -- Plot A --
    plotA = test.create_plot("Plot A")
    plotA.x_label = "Time (s)"
    plotA.y_label = "Voltage (V)"
    plotA.title = "Plot A (Sine/Cosine)"
    result1.add(plotA)

    # -- Plot B --
    plotB = test.create_plot("Plot B")
    plotB.x_label = "Time (s)"
    plotB.y_label = "Amplitude"
    plotB.title = "Plot B (Random Data)"
    result1.add(plotB)

    # We'll animate each plot for 50 frames
    x = np.linspace(0, 10, 1000)

    for frame in range(50):
        # --- Plot A: Sine & Cosine ---
        phase = frame * 0.2
        y_sine = np.sin(x + phase)
        y_cosine = np.cos(x + phase)

        plotA.set_trace("Sine A", x, y_sine, color="#FF0000")   # Red
        plotA.set_trace("Cosine A", x, y_cosine, color="#00FF00")  # Green

        # --- Plot B: Random data ---
        y_rand1 = np.random.normal(0, 0.1, len(x)) + (frame * 0.01)
        y_rand2 = np.random.normal(0, 0.1, len(x)) - (frame * 0.01)

        plotB.set_trace("Random1 B", x, y_rand1, color="#0000FF")   # Blue
        plotB.set_trace("Random2 B", x, y_rand2, color="#FFA500")   # Orange

        # Update progress for the first result
        pct = int((frame / 49) * 50)  # e.g. goes from 0 to ~50
        result1.progress = pct

        # Wait a bit to see updates
        test.wait(20)

    # Final status for result #1
    result1.progress = 100
    result1.status = "PASS"

    # ----------------------------------
    # 2) SECOND RESULT: 1 PLOT + 1 TABLE
    # ----------------------------------
    result2 = test.create_result("Second Result")
    result2.show()

    # -- Single Plot C --
    plotC = test.create_plot("Plot C")
    plotC.x_label = "Sample"
    plotC.y_label = "Value"
    plotC.title = "Plot C (Random Sine)"
    result2.add(plotC)

    # -- One Table --
    table = test.create_table("Data Table")
    table.columns = ["Index", "Random A", "Random B"]
    result2.add(table)

    x2 = np.arange(1000)
    for frame in range(50):
        # Generate random sine data
        y_sine_rand = np.sin((x2 * 0.05) + frame * 0.2) + np.random.normal(0, 0.1, len(x2))

        plotC.set_trace("Random Sine C", x2, y_sine_rand, color="#4CAF50")

        # Insert a row in the table
        row = [
            f"{frame}",
            f"{np.random.uniform(0, 1):.3f}",
            f"{np.random.uniform(0, 1):.3f}"
        ]
        table.add_row(row)

        # Update progress for the second result
        pct = int((frame / 49) * 100)
        result2.progress = pct

        test.wait(20)

    result2.progress = 100
    result2.status = "PASS"

    return True
