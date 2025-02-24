
from typing import Optional, Any, Tuple
import numpy as np
from pymetr.models.analysis import Analysis, SpectralAnalysis
from pymetr.core.logging import logger

class DualTraceAnalysis(Analysis):
    """Base class for analyses requiring two input traces."""
    def __init__(
        self, 
        name: str,
        trace_a_id: str,
        trace_b_id: str,
        **kwargs
    ):
        super().__init__(name, trace_a_id, **kwargs)
        self._trace_b_id = trace_b_id
        
        # Result trace for computed output
        self._result_trace = self.create_trace(
            x_data=np.array([]),
            y_data=np.array([]),
            name=f"{name} Result"
        )
        
    @property
    def trace_a(self):
        """First input trace."""
        return self.input_trace  # From base class
        
    @property
    def trace_b(self):
        """Second input trace."""
        return self.state.get_model(self._trace_b_id)
        
    def _get_aligned_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Get x-aligned data from both traces."""
        if not self.trace_a or not self.trace_b:
            return np.array([]), np.array([]), np.array([])
            
        # Get data respecting ROI
        xa, ya = self.get_analysis_data()
        xb, yb = self.trace_b.data
        
        # Interpolate trace B to match trace A x points
        yb_interp = np.interp(xa, xb, yb)
        
        return xa, ya, yb_interp

class TraceMath(DualTraceAnalysis):
    """Basic math operations between traces."""
    OPERATIONS = {
        'add': (lambda a,b: a + b, '+'),
        'subtract': (lambda a,b: a - b, '-'),
        'multiply': (lambda a,b: a * b, '×'),
        'divide': (lambda a,b: np.divide(a, b, where=b!=0), '÷'),
        'min': (np.minimum, 'min'),
        'max': (np.maximum, 'max'),
        'average': (lambda a,b: (a + b)/2, 'avg')
    }
    
    def __init__(
        self, 
        trace_a_id: str,
        trace_b_id: str,
        operation: str = 'add',
        **kwargs
    ):
        name = f"Trace {self.OPERATIONS[operation][1]}"
        super().__init__(name, trace_a_id, trace_b_id, **kwargs)
        self._operation = operation
        self._result_trace.color = "#00FFFF"  # Make result stand out
        
        # Add label marker to show operation
        self._label = self.create_marker(
            x=0, y=0,
            name="Operation",
            label=f"{trace_a_id} {self.OPERATIONS[operation][1]} {trace_b_id}"
        )
        
        self.update()
        
    def update(self):
        x, ya, yb = self._get_aligned_data()
        if len(x) == 0:
            return
            
        # Apply operation
        op_func = self.OPERATIONS[self._operation][0]
        result = op_func(ya, yb)
        
        # Update result trace
        self._result_trace.data = (x, result)
        
        # Update label position
        self._label.x = x[len(x)//2]
        self._label.y = result[len(result)//2]

class CrossCorrelation(DualTraceAnalysis):
    """Cross-correlation analysis between traces."""
    def __init__(self, trace_a_id: str, trace_b_id: str, **kwargs):
        super().__init__("Cross Correlation", trace_a_id, trace_b_id, **kwargs)
        self._result_trace.color = "#FF00FF"
        
        # Add lag cursor
        self._lag_cursor = self.create_cursor(
            position=0,
            axis='x',
            name="Peak Lag"
        )
        
        # Add correlation value marker
        self._corr_marker = self.create_marker(
            x=0, y=0,
            name="Correlation"
        )
        
        self.update()
        
    def update(self):
        x, ya, yb = self._get_aligned_data()
        if len(x) == 0:
            return
            
        # Compute cross correlation
        correlation = np.correlate(ya - ya.mean(), 
                                 yb - yb.mean(), 
                                 mode='full')
        
        # Normalize
        correlation = correlation / (len(ya) * ya.std() * yb.std())
        
        # Create lag axis
        dt = x[1] - x[0]
        lags = np.arange(-(len(x)-1), len(x)) * dt
        
        # Find peak correlation
        peak_idx = np.argmax(np.abs(correlation))
        peak_lag = lags[peak_idx]
        peak_corr = correlation[peak_idx]
        
        # Update result trace
        self._result_trace.data = (lags, correlation)
        
        # Update markers
        self._lag_cursor.position = peak_lag
        self._corr_marker.x = peak_lag
        self._corr_marker.y = peak_corr
        self._corr_marker.label = f"Correlation: {peak_corr:.2f}\nLag: {peak_lag:.2e}s"

class CrossSpectrum(DualTraceAnalysis, SpectralAnalysis):
    """Cross-spectral analysis between two traces."""
    def __init__(self, trace_a_id: str, trace_b_id: str, **kwargs):
        DualTraceAnalysis.__init__(self, "Cross Spectrum", 
                                 trace_a_id, trace_b_id, **kwargs)
        SpectralAnalysis.__init__(self, trace_a_id, **kwargs)
        
        # Override trace names
        self._mag_trace.name = "Cross Magnitude"
        self._phase_trace = self.create_trace(
            x_data=np.array([]),
            y_data=np.array([]),
            name="Cross Phase",
            color="#FF8800"
        )
        
        # Coherence trace
        self._coherence = self.create_trace(
            x_data=np.array([]),
            y_data=np.array([]),
            name="Coherence",
            color="#00FF00"
        )
        
        self.update()
        
    def update(self):
        x, ya, yb = self._get_aligned_data()
        if len(x) == 0:
            return
            
        # Remove DC if requested
        if self._remove_dc:
            ya = ya - np.mean(ya)
            yb = yb - np.mean(yb)
            
        # Apply windows
        ya_win = self._apply_window(ya)
        yb_win = self._apply_window(yb)
        
        # Compute FFTs
        fft_a = np.fft.rfft(ya_win)
        fft_b = np.fft.rfft(yb_win)
        freqs = self._compute_freq_axis(x)
        
        # Compute cross spectrum
        cross_spec = fft_a * np.conj(fft_b)
        
        # Compute coherence
        auto_a = np.abs(fft_a)**2
        auto_b = np.abs(fft_b)**2
        coherence = np.abs(cross_spec)**2 / (auto_a * auto_b)
        
        # Update traces
        self._mag_trace.data = (freqs, self._to_db(cross_spec))
        self._phase_trace.data = (freqs, np.angle(cross_spec, deg=True))
        self._coherence.data = (freqs, coherence)
        
        # Update peak at most coherent frequency
        peak_idx = np.argmax(coherence)
        self._peak.x = freqs[peak_idx]
        self._peak.y = coherence[peak_idx]
        self._peak.label = (f"Max Coherence:\n{freqs[peak_idx]:.2f}Hz\n"
                          f"{coherence[peak_idx]:.3f}")