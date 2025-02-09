import numpy as np

def run_test():
    """
    Test script demonstrating real-time plotting capabilities with progress updates.
    """
    try:
        # Create main group and results
        main_group = create_group("Real-time Test Results")
        signal_result = create_result("Signal Analysis")
        main_group.add(signal_result)
        
        # Create real-time plot
        realtime_plot = create_plot("Real-time Signal")
        realtime_plot.x_label = "Time (s)"
        realtime_plot.y_label = "Amplitude"
        realtime_plot.grid_enabled = True
        realtime_plot.legend_enabled = True
        signal_result.add(realtime_plot)
        
        # Initialize data arrays
        total_points = 100  # Reduced for testing
        time_data = []
        signal_data = []
        noise_data = []
        
        # Signal parameters
        frequency = 0.5  # Hz
        amplitude = 2.0
        noise_amplitude = 0.3
        
        # Simulate real-time data acquisition and plotting
        for i in range(total_points):
            # Update progress
            progress = (i / total_points) * 100
            set_test_progress(progress, f"Acquiring point {i+1} of {total_points}")
            
            # Generate new data point
            t = i * 0.1  # 100ms per point
            signal = amplitude * np.sin(2 * np.pi * frequency * t)
            noise = noise_amplitude * np.random.randn()
            
            # Append to data arrays
            time_data.append(t)
            signal_data.append(signal)
            noise_data.append(signal + noise)
            
            # Convert to numpy arrays
            t_array = np.array(time_data)
            s_array = np.array(signal_data)
            n_array = np.array(noise_data)
            
            # Update traces
            realtime_plot.set_trace(
                "Clean Signal",
                t_array,
                s_array,
                color="#00ff00",  # Green
                width=2
            )
            
            realtime_plot.set_trace(
                "Noisy Signal",
                t_array,
                n_array,
                color="#ff0000",  # Red
                style="dot",
                width=1
            )
            
            # Add moving average once we have enough points
            if len(time_data) > 10:
                moving_avg = np.convolve(noise_data, np.ones(10)/10, mode='valid')
                ma_time = time_data[9:]
                
                realtime_plot.set_trace(
                    "Moving Average",
                    np.array(ma_time),
                    moving_avg,
                    color="#0000ff",  # Blue
                    width=2,
                    style="dash"
                )
            
            # Small delay between points
            wait(100)  # 100ms delay
        
        # Final statistics
        table = create_table("Signal Statistics")
        table.add_row({
            "Measurement": "Peak Amplitude",
            "Value": f"{np.max(np.abs(signal_data)):.3f}",
            "Units": "V"
        })
        table.add_row({
            "Measurement": "RMS Noise",
            "Value": f"{np.std(np.array(noise_data) - np.array(signal_data)):.3f}",
            "Units": "V"
        })
        table.add_row({
            "Measurement": "Duration",
            "Value": f"{time_data[-1]:.1f}",
            "Units": "s"
        })
        
        signal_result.add(table)
        
        # Set status based on noise level
        rms_noise = np.std(np.array(noise_data) - np.array(signal_data))
        if rms_noise < noise_amplitude:
            signal_result.status = "Pass"
        else:
            signal_result.status = "Fail"
        
        # Final progress update
        set_test_progress(100, "Test complete!")
        
        return signal_result.status == "Pass"
        
    except Exception as e:
        if signal_result:
            signal_result.status = "Error"
        return False