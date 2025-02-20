import numpy as np
import time

def run_test(test):
    # Setup frequency points
    freq_start, freq_stop = 0.1, 20.0  # GHz
    fine_freqs = np.arange(freq_start, freq_stop + 0.1, 0.5)  # 100 MHz steps for plots
    coarse_freqs = np.arange(0, freq_stop + 0.1, 2.0)  # 2 GHz steps for tables
    power_levels = np.arange(20, -25, -5)  # +20 to -20 dBm, 5 dB steps
    
    # Vibrant, neon-esque colors
    colors = [
        "#00F0FF",  # neon cyan
        "#00FF81",  # neon green
        "#FFA900",  # bright warm orange
        "#FF00B3",  # neon pink
        "#9D00FF",  # neon purple
        "#FFFF82",  # neon yellow
        "#FF6800",  # bright orange
        "#FFD700",  # gold
        "#5BFFB8",  # mint green
    ]
    
    try:
        # =============================================
        # First sweep: Overview plots
        # =============================================
        sweep_result = test.create_result("Power Sweep Overview")
        
        # Create main plots
        power_plot = test.create_plot("Power vs Frequency")
        power_plot.x_label = "Frequency"
        power_plot.y_label = "Power"
        power_plot.x_unit = "GHz"
        power_plot.y_unit = "dBm"
        
        error_plot = test.create_plot("Power Error vs Frequency")
        error_plot.x_label = "Frequency"
        error_plot.y_label = "Error"
        error_plot.x_unit = "GHz"
        error_plot.y_unit = "dB"

        sweep_result.add(power_plot)
        sweep_result.add(error_plot)
        
        # Create traces for each power level
        power_traces = {}
        error_traces = {}
        
        for i, power in enumerate(power_levels):
            color = colors[i % len(colors)]
            
            # Create traces directly with plot parent
            power_traces[power] = test.create_trace(
                f"{power:+d} dBm", 
                [], 
                [], 
                color=color
            )
            
            error_traces[power] = test.create_trace(
                f"{power:+d} dBm",
                [],
                [],
                color=color
            )
        
        # Perform fine sweep
        measured_data = {
            power: {'freqs': [], 'powers': [], 'errors': []} 
            for power in power_levels
        }
        
        for i, freq in enumerate(fine_freqs):
            test.progress = (i / len(fine_freqs)) * 100
            
            # Simulate frequency change delay
            test.wait(50)
            
            for power in power_levels:
                # Simulate measurement
                base_error = np.random.normal(0, 0.1)
                freq_error = freq * 0.002 * np.random.normal(0, 1)
                power_error = (20 - power) * 0.01 * np.random.normal(0, 1)
                total_error = base_error + freq_error + power_error
                
                measured_power = power + total_error
                
                # Store and update traces
                measured_data[power]['freqs'].append(freq)
                measured_data[power]['powers'].append(measured_power)
                measured_data[power]['errors'].append(measured_power - power)
                
                # Update trace data through properties
                power_traces[power].x_data = measured_data[power]['freqs']
                power_traces[power].y_data = measured_data[power]['powers']
                
                error_traces[power].x_data = measured_data[power]['freqs']
                error_traces[power].y_data = measured_data[power]['errors']
                
                # Simulate power measurement delay
                test.wait(20)
        
        sweep_result.status = 'PASS'
        
        # =============================================
        # Second phase: Individual power level sweeps
        # =============================================
        for power_idx, power in enumerate(power_levels):
            # Create result for this power level
            result = test.create_result(f"Power Level: {power:+d} dBm")
            
            # Create plot
            plot = test.create_plot(f"Power Accuracy at {power:+d} dBm")
            plot.x_label = "Frequency"
            plot.y_label = "Error"
            plot.x_unit = "GHz"
            plot.y_unit = "dB"
            
            # Create table
            table = test.create_table(f"Power Accuracy Data ({power:+d} dBm)")
            table.columns = ["Frequency (GHz)", "Requested (dBm)", 
                           "Measured (dBm)", "Error (dB)", 
                           "Uncertainty (dB)"]
            
            # Create trace for this power level
            trace = test.create_trace(
                "Error",
                [],
                [],
                color=colors[power_idx % len(colors)]
            )
            
            # Perform coarse sweep for this power level
            freqs = []
            errors = []
            
            for i, freq in enumerate(coarse_freqs):
                progress = (power_idx * len(coarse_freqs) + i) / (len(power_levels) * len(coarse_freqs)) * 100
                test.progress = progress
                
                # Simulate frequency change
                test.wait(50)
                
                # Simulate measurement
                base_error = np.random.normal(0, 0.1)
                freq_error = freq * 0.002 * np.random.normal(0, 1)
                power_error = (20 - power) * 0.01 * np.random.normal(0, 1)
                total_error = base_error + freq_error + power_error
                
                measured_power = power + total_error
                uncertainty = 0.1 + (freq/20)*0.2 + abs(20-power)*0.02
                
                # Update plot
                freqs.append(freq)
                errors.append(measured_power - power)
                trace.data = (freqs, errors)
                
                # Update table
                table.add_row([
                    f"{freq:.1f}",
                    f"{power:+.1f}",
                    f"{measured_power:.2f}",
                    f"{(measured_power - power):.2f}",
                    f"{uncertainty:.2f}"
                ])
                
                # Simulate measurement time
                test.wait(50)
            
            result.status = 'PASS'
            test.wait(100)  # Pause between power levels
        
        test.progress = 100
        return True
        
    except Exception as e:
        if 'sweep_result' in locals():
            sweep_result.status = 'ERROR'
        if 'result' in locals():
            result.status = 'ERROR'
        test.progress = 100
        return False