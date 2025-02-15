import numpy as np

def run_test():
    """
    Test script demonstrating multiple real-time plotting results.
    """
    try:
        # Create main group for all results
        main_group = create_group("Real-time Test Results")
        
        # First Analysis: Time Domain Signal
        signal_result = create_result("Time Domain Analysis")
        main_group.add(signal_result)
        
        # Create real-time plot for time domain
        time_plot = create_plot("Time Domain Signal")
        time_plot.x_label = "Time (s)"
        time_plot.y_label = "Amplitude"
        time_plot.grid_enabled = True
        time_plot.legend_enabled = True
        time_plot.x_lim = [0, 10]
        signal_result.add(time_plot)
        
        # Initialize data arrays
        total_points = 100
        time_data = []
        signal_data = []
        noise_data = []
        
        # Signal parameters
        frequency = 0.5  # Hz
        amplitude = 2.0
        noise_amplitude = 0.3
        
        # First phase: Time domain analysis
        for i in range(total_points):
            # Update progress for first analysis
            progress = (i / total_points) * 50  # First half of total progress
            set_test_progress(progress, f"Time domain analysis: point {i+1} of {total_points}")
            
            # Generate new data point
            t = i * 0.1
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
            
            # Update time domain traces
            time_plot.set_trace(
                "Clean Signal",
                t_array,
                s_array,
                color="#00ff00",
                width=2
            )
            
            time_plot.set_trace(
                "Noisy Signal",
                t_array,
                n_array,
                color="#ff0000",
                style="dot",
                width=1
            )
            
            # Add moving average
            if len(time_data) > 10:
                moving_avg = np.convolve(noise_data, np.ones(10)/10, mode='valid')
                ma_time = time_data[9:]
                
                time_plot.set_trace(
                    "Moving Average",
                    np.array(ma_time),
                    moving_avg,
                    color="#0000ff",
                    width=2,
                    style="dash"
                )
            
            wait(100)
        
        signal_result.status = "Pass"
        
        # Second Analysis: Frequency Domain
        freq_result = create_result("Frequency Domain Analysis")
        main_group.add(freq_result)
        
        # Create frequency domain plot
        freq_plot = create_plot("Frequency Analysis")
        freq_plot.x_label = "Frequency (Hz)"
        freq_plot.y_label = "Magnitude"
        freq_plot.grid_enabled = True
        freq_plot.legend_enabled = True
        freq_result.add(freq_plot)
        
        # Frequency analysis parameters
        window_sizes = [20, 40, 60, 80, 100]  # Different FFT window sizes
        
        # Second phase: Frequency domain analysis
        for i, window_size in enumerate(window_sizes):
            # Update progress for second analysis
            progress = 50 + (i / len(window_sizes)) * 50  # Second half of progress
            set_test_progress(progress, f"Frequency analysis: window size {window_size}")
            
            # Calculate FFT for clean signal
            if len(signal_data) >= window_size:
                sample_rate = 10  # 1/0.1 seconds
                windowed_signal = signal_data[-window_size:]
                
                # Apply Hanning window
                window = np.hanning(window_size)
                windowed_data = windowed_signal * window
                
                # Compute FFT
                fft_result = np.fft.fft(windowed_data)
                freqs = np.fft.fftfreq(window_size, 1/sample_rate)
                
                # Get positive frequencies
                pos_mask = freqs >= 0
                freqs = freqs[pos_mask]
                magnitudes = np.abs(fft_result)[pos_mask]
                
                # Normalize magnitudes
                magnitudes = magnitudes / np.max(magnitudes)
                
                # Plot frequency spectrum
                freq_plot.set_trace(
                    f"Window Size {window_size}",
                    freqs,
                    magnitudes,
                    color=f"#{i*50:02x}00ff",  # Varying colors
                    width=2,
                    style="solid" if i % 2 == 0 else "dash"
                )
            
            wait(200)
        
        freq_result.status = "Pass"
        
        # Final progress update
        set_test_progress(100, "All analyses complete!")
        
        return signal_result.status == "Pass" and freq_result.status == "Pass"
        
    except Exception as e:
        if signal_result:
            signal_result.status = "Error"
        if freq_result:
            freq_result.status = "Error"
        return False