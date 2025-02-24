from typing import Optional, Any, Tuple, TYPE_CHECKING
import numpy as np
from pymetr.models.base import BaseModel
from pymetr.core.logging import logger

if TYPE_CHECKING:
    from pymetr.models.trace import Trace  # Import only for type checking
    from pymetr.models.plot import Plot
    from pymetr.models.marker import Marker
    from pymetr.models.cursor import Cursor

class Analysis(BaseModel):
    """
    Base analysis model that generates and manages plot objects.
    Results are shown in parent plot through child objects.
    """
    def __init__(
        self, 
        name: str,
        input_trace_id: str,  # Required input trace
        model_id: Optional[str] = None
    ):
        super().__init__(model_type='Analysis', model_id=model_id, name=name)
        self._input_trace_id = input_trace_id
        
        logger.debug(f"Analysis {self.id} created for trace {input_trace_id}")

    @property
    def input_trace(self) -> Optional["Trace"]:  # Use string annotation to avoid runtime import
        """Get input trace model."""
        return self.state.get_model(self._input_trace_id)

    @property
    def parent_plot(self) -> Optional["Plot"]:  # Use string annotation
        """Get parent plot model."""
        return self.state.get_parent(self.id)

    def create_marker(self, **kwargs) -> "Marker":
        """Create a marker as a child of this analysis."""
        marker = self.state.create_model(Marker, **kwargs)
        self.add_child(marker)
        logger.debug(f"Analysis {self.id} created marker {marker.id}")
        return marker

    def create_cursor(self, **kwargs) -> "Cursor":
        """Create a cursor as a child of this analysis."""
        cursor = self.state.create_model(Cursor, **kwargs)
        self.add_child(cursor)
        logger.debug(f"Analysis {self.id} created cursor {cursor.id}")
        return cursor

    def create_trace(self, **kwargs) -> "Trace":
        """Create a trace as a child of this analysis."""
        from pymetr.models.trace.trace_model import Trace  # Deferred import
        trace = self.state.create_model(Trace, **kwargs)
        self.add_child(trace)
        logger.debug(f"Analysis {self.id} created trace {trace.id}")
        return trace

    def update(self):
        """Update analysis results."""
        raise NotImplementedError

    def _handle_model_change(self, model_id: str, model_type: str, prop: str, value: Any):
        """Handle model changes affecting analysis."""
        try:
            # Update if input trace data changes
            if model_id == self._input_trace_id and prop == "data":
                self.update()
                
            # Update if plot ROI changes
            if self.parent_plot and model_id == self.parent_plot.id:
                if prop in ("roi", "roi_visible"):
                    self.update()
                    
        except Exception as e:
            logger.error(f"Error handling model change in {self.id}: {e}")

    def get_analysis_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get data to analyze, respecting ROI if active."""
        trace = self.input_trace
        if not trace:
            return np.array([]), np.array([])
            
        x_data, y_data = trace.data
        
        # Check if we should use ROI
        if self.parent_plot and self.parent_plot.roi_visible:
            roi = self.parent_plot.roi
            if roi and len(roi) == 2:
                mask = (x_data >= roi[0]) & (x_data <= roi[1])
                return x_data[mask], y_data[mask]
                
        return x_data, y_data
    
class EdgeMeasurement(Analysis):
    """Base class for edge timing measurements."""
    def __init__(self, name: str, input_trace_id: str, edge_type: str = "rise", **kwargs):
        super().__init__(name, input_trace_id, **kwargs)
        self.edge_type = edge_type  # "rise" or "fall"
        
        # Create level cursors
        self._low = self.create_cursor(
            position=0, axis='y', name="10%",
            color="#00FF00"
        )
        self._high = self.create_cursor(
            position=0, axis='y', name="90%",
            color="#00FF00"
        )
        
        # Create edge cursors
        self._start = self.create_cursor(
            position=0, axis='x', name="Start",
            color="#FFFF00"
        )
        self._end = self.create_cursor(
            position=0, axis='x', name="End",
            color="#FFFF00"
        )
        
        # Result marker
        self._result = self.create_marker(
            x=0, y=0, name=f"{edge_type.title()} Time"
        )
        
        self.update()
        
    def update(self):
        """Update edge measurement."""
        x_data, y_data = self.get_analysis_data()
        if len(y_data) < 2:
            return
            
        # Find reference levels
        y_min, y_max = y_data.min(), y_data.max()
        y_range = y_max - y_min
        
        low_level = y_min + y_range * 0.1  # 10%
        high_level = y_min + y_range * 0.9  # 90%
        
        # Update level cursors
        self._low.position = low_level
        self._high.position = high_level
        
        # Find edge crossing points
        if self.edge_type == "rise":
            low_idx = np.where(y_data >= low_level)[0][0]
            high_idx = np.where(y_data >= high_level)[0][0]
        else:  # fall
            low_idx = np.where(y_data <= low_level)[0][0]
            high_idx = np.where(y_data <= high_level)[0][0]
            
        # Update edge cursors
        self._start.position = x_data[low_idx]
        self._end.position = x_data[high_idx]
        
        # Calculate edge time
        edge_time = abs(x_data[high_idx] - x_data[low_idx])
        
        # Update result
        self._result.x = (x_data[high_idx] + x_data[low_idx]) / 2
        self._result.y = (high_level + low_level) / 2
        self._result.label = f"{self.edge_type.title()} Time: {edge_time:.2e}s"

class RiseTime(EdgeMeasurement):
    """Rise time measurement (10% to 90%)."""
    def __init__(self, input_trace_id: str, **kwargs):
        super().__init__("Rise Time", input_trace_id, edge_type="rise", **kwargs)

class FallTime(EdgeMeasurement):
    """Fall time measurement (90% to 10%)."""
    def __init__(self, input_trace_id: str, **kwargs):
        super().__init__("Fall Time", input_trace_id, edge_type="fall", **kwargs)

class PulseWidth(Analysis):
    """Measure pulse width at 50% threshold."""
    def __init__(self, input_trace_id: str, **kwargs):
        super().__init__("Pulse Width", input_trace_id, **kwargs)
        
        self._threshold = self.create_cursor(
            position=0, axis='y', name="50%",
            color="#00FFFF",
            style="dash"
        )
        
        self._start = self.create_cursor(
            position=0, axis='x', name="Start",
            color="#FFFF00"
        )
        self._end = self.create_cursor(
            position=0, axis='x', name="End",
            color="#FFFF00"
        )
        
        self._result = self.create_marker(
            x=0, y=0, name="Width"
        )
        
        self.update()

    def update(self):
        x_data, y_data = self.get_analysis_data()
        if len(y_data) < 2:
            return
            
        # Find 50% threshold
        threshold = y_data.mean()
        self._threshold.position = threshold
        
        # Find crossings
        crossings = np.where(np.diff(y_data > threshold))[0]
        if len(crossings) >= 2:
            self._start.position = x_data[crossings[0]]
            self._end.position = x_data[crossings[1]]
            
            width = abs(x_data[crossings[1]] - x_data[crossings[0]])
            
            self._result.x = (x_data[crossings[0]] + x_data[crossings[1]]) / 2
            self._result.y = threshold * 1.2  # Place above line
            self._result.label = f"Width: {width:.2e}s"

class PhaseDifference(Analysis):
    """Measure phase difference between two traces."""
    def __init__(self, input_trace_id: str, reference_trace_id: str, **kwargs):
        super().__init__("Phase", input_trace_id, **kwargs)
        self._ref_trace_id = reference_trace_id
        
        # Reference trace zero crossing
        self._ref_cursor = self.create_cursor(
            position=0, axis='x', name="Ref",
            color="#FF00FF"
        )
        
        # Input trace crossing
        self._input_cursor = self.create_cursor(
            position=0, axis='x', name="Input",
            color="#00FFFF"
        )
        
        self._result = self.create_marker(
            x=0, y=0, name="Phase"
        )
        
        self.update()
        
    def update(self):
        ref_trace = self.state.get_model(self._ref_trace_id)
        input_trace = self.input_trace
        if not ref_trace or not input_trace:
            return
            
        # Get first zero crossing of each
        ref_x, ref_y = ref_trace.data
        in_x, in_y = input_trace.data
        
        # Find zero crossings
        ref_cross = ref_x[np.where(np.diff(np.signbit(ref_y)))[0][0]]
        in_cross = in_x[np.where(np.diff(np.signbit(in_y)))[0][0]]
        
        self._ref_cursor.position = ref_cross
        self._input_cursor.position = in_cross
        
        # Calculate phase difference
        time_diff = abs(in_cross - ref_cross)
        period = self._find_period(ref_x, ref_y)
        if period:
            phase_deg = (time_diff / period) * 360.0
            
            self._result.x = (ref_cross + in_cross) / 2
            self._result.y = max(ref_y.max(), in_y.max())
            self._result.label = f"Phase: {phase_deg:.1f}°"
            
    def _find_period(self, x: np.ndarray, y: np.ndarray) -> Optional[float]:
        """Find signal period from zero crossings."""
        crossings = np.where(np.diff(np.signbit(y)))[0]
        if len(crossings) >= 2:
            return abs(x[crossings[1]] - x[crossings[0]]) * 2
        return None

class SlewRate(EdgeMeasurement):
    """Measure slew rate (V/s) on edges."""
    def __init__(self, input_trace_id: str, edge_type: str = "rise", **kwargs):
        super().__init__("Slew Rate", input_trace_id, edge_type=edge_type, **kwargs)
        
    def update(self):
        super().update()  # Get basic edge timing
        
        # Calculate dV/dt
        if self._start.position and self._end.position:
            dv = abs(self._high.position - self._low.position)
            dt = abs(self._end.position - self._start.position)
            slew = dv/dt if dt else 0
            
            self._result.label = f"Slew: {slew:.2e}V/s"

class DutyCycle(Analysis):
    """Measure duty cycle of periodic signal."""
    def __init__(self, input_trace_id: str, **kwargs):
        super().__init__("Duty Cycle", input_trace_id, **kwargs)
        
        self._threshold = self.create_cursor(
            position=0, axis='y', name="50%",
            color="#00FFFF",
            style="dash"
        )
        
        self._high_time = self.create_cursor(
            position=0, axis='x', name="High",
            color="#FFFF00"
        )
        
        self._period = self.create_cursor(
            position=0, axis='x', name="Period",
            color="#FF00FF"
        )
        
        self._result = self.create_marker(
            x=0, y=0, name="Duty"
        )
        
        self.update()
        
    def update(self):
        x_data, y_data = self.get_analysis_data()
        if len(y_data) < 2:
            return
            
        # Find 50% threshold
        threshold = (y_data.max() + y_data.min()) / 2
        self._threshold.position = threshold
        
        # Find high/low transitions
        crossings = np.where(np.diff(y_data > threshold))[0]
        if len(crossings) >= 2:
            # Time above threshold
            high_time = x_data[crossings[1]] - x_data[crossings[0]]
            
            # Total period
            if len(crossings) >= 3:
                period = x_data[crossings[2]] - x_data[crossings[0]]
                duty = (high_time / period) * 100 if period else 0
                
                self._high_time.position = x_data[crossings[0]] + high_time
                self._period.position = x_data[crossings[0]] + period
                
                self._result.x = x_data[crossings[0]] + period/2
                self._result.y = threshold * 1.2
                self._result.label = f"Duty: {duty:.1f}%"

class Overshoot(Analysis):
    """Measure overshoot/undershoot on edges."""
    def __init__(self, input_trace_id: str, **kwargs):
        super().__init__("Overshoot", input_trace_id, **kwargs)
        
        # Steady state levels
        self._high = self.create_cursor(
            position=0, axis='y', name="High",
            color="#00FF00"
        )
        self._low = self.create_cursor(
            position=0, axis='y', name="Low",
            color="#00FF00"
        )
        
        # Overshoot/undershoot markers
        self._over = self.create_marker(
            x=0, y=0, name="Over",
            color="#FF0000"
        )
        self._under = self.create_marker(
            x=0, y=0, name="Under",
            color="#FF0000"
        )
        
        self.update()
        
    def update(self):
        x_data, y_data = self.get_analysis_data()
        if len(y_data) < 2:
            return
            
        # Find steady state levels (using histogram)
        hist, bins = np.histogram(y_data, bins=50)
        peaks = np.where(hist > np.mean(hist))[0]
        if len(peaks) >= 2:
            low_level = bins[peaks[0]]
            high_level = bins[peaks[-1]]
            
            self._high.position = high_level
            self._low.position = low_level
            
            # Find overshoots
            over_idx = np.argmax(y_data)
            under_idx = np.argmin(y_data)
            
            over_amount = ((y_data[over_idx] - high_level) / 
                         (high_level - low_level) * 100)
            under_amount = ((low_level - y_data[under_idx]) / 
                          (high_level - low_level) * 100)
            
            # Update markers
            self._over.x = x_data[over_idx]
            self._over.y = y_data[over_idx]
            self._over.label = f"Over: {over_amount:.1f}%"
            
            self._under.x = x_data[under_idx]
            self._under.y = y_data[under_idx]
            self._under.label = f"Under: {under_amount:.1f}%"

class Jitter(Analysis):
    """Edge jitter measurement."""
    def __init__(self, input_trace_id: str, **kwargs):
        super().__init__("Jitter", input_trace_id, **kwargs)
        
        # Threshold cursor
        self._threshold = self.create_cursor(
            position=0, axis='y', name="50%",
            color="#00FFFF"
        )
        
        # Create markers for min/max timing
        self._early = self.create_cursor(
            position=0, axis='x', name="Early",
            color="#FF0000"
        )
        self._late = self.create_cursor(
            position=0, axis='x', name="Late",
            color="#FF0000"
        )
        
        self._result = self.create_marker(
            x=0, y=0, name="Jitter"
        )
        
        self.update()
        
    def update(self):
        x_data, y_data = self.get_analysis_data()
        if len(y_data) < 2:
            return
            
        # Find threshold
        threshold = (y_data.max() + y_data.min()) / 2
        self._threshold.position = threshold
        
        # Find all edge crossings
        crossings = []
        for i in range(1, len(y_data)):
            if (y_data[i-1] < threshold and y_data[i] >= threshold):
                # Interpolate precise crossing
                t = (threshold - y_data[i-1]) / (y_data[i] - y_data[i-1])
                cross_time = x_data[i-1] + t * (x_data[i] - x_data[i-1])
                crossings.append(cross_time)
                
        if len(crossings) >= 2:
            # Find average period
            periods = np.diff(crossings)
            avg_period = np.mean(periods)
            
            # Calculate timing variations
            deviations = periods - avg_period
            pk_pk_jitter = np.ptp(deviations)
            rms_jitter = np.std(deviations)
            
            # Update cursors to show extremes
            min_idx = np.argmin(periods)
            max_idx = np.argmax(periods)
            
            self._early.position = crossings[min_idx]
            self._late.position = crossings[max_idx]
            
            # Update result
            mid_x = (crossings[min_idx] + crossings[max_idx]) / 2
            self._result.x = mid_x
            self._result.y = threshold * 1.2
            self._result.label = (f"Jitter:\nPk-Pk: {pk_pk_jitter:.2e}s\n"
                                f"RMS: {rms_jitter:.2e}s")

class EyeDiagram(Analysis):
    """Eye diagram analysis using trace overlay."""
    def __init__(self, input_trace_id: str, **kwargs):
        super().__init__("Eye", input_trace_id, **kwargs)
        
        # Create overlaid trace for eye
        self._eye_trace = self.create_trace(
            x_data=np.array([]),
            y_data=np.array([]),
            name="Eye",
            color="#00FFFF",
            opacity=0.5
        )
        
        # Measurements
        self._height = self.create_marker(
            x=0, y=0, name="Height"
        )
        self._width = self.create_marker(
            x=0, y=0, name="Width"
        )
        
        self.update()
        
    def update(self):
        x_data, y_data = self.get_analysis_data()
        if len(y_data) < 2:
            return
            
        # Find bit period (assuming NRZ)
        threshold = (y_data.max() + y_data.min()) / 2
        crossings = np.where(np.diff(y_data > threshold))[0]
        if len(crossings) < 2:
            return
            
        # Estimate bit period
        periods = np.diff(crossings)
        bit_period = np.median(periods) * (x_data[1] - x_data[0])
        
        # Create eye by overlaying bit periods
        eye_x = []
        eye_y = []
        
        for i in range(len(crossings)-1):
            start_idx = crossings[i]
            end_idx = min(start_idx + int(bit_period*2), len(x_data))
            
            # Normalize to bit period
            segment_x = x_data[start_idx:end_idx]
            segment_x = (segment_x - x_data[start_idx]) / bit_period
            
            eye_x.extend(segment_x)
            eye_y.extend(y_data[start_idx:end_idx])
        
        # Update eye trace
        self._eye_trace.data = (np.array(eye_x), np.array(eye_y))
        
        # Measure eye parameters
        if len(eye_y) > 0:
            eye_height = np.percentile(eye_y, 95) - np.percentile(eye_y, 5)
            eye_width = bit_period * 0.8  # Approximate from histogram
            
            self._height.x = 0.5  # Center of eye
            self._height.y = threshold
            self._height.label = f"Eye Height: {eye_height:.2e}"
            
            self._width.x = 0.5
            self._width.y = threshold * 0.8
            self._width.label = f"Eye Width: {eye_width:.2e}s"

class SpectralAnalysis(Analysis):
    """Base class for FFT-based analysis."""
    
    WINDOWS = {
        'rectangular': (np.ones, 'Uniform'),
        'hanning': (np.hanning, 'Hanning'),
        'hamming': (np.hamming, 'Hamming'),
        'flattop': (lambda N: np.blackman(N), 'Flat Top'),
        'blackman': (np.blackman, 'Blackman')
    }
    
    def __init__(self, input_trace_id: str, **kwargs):
        super().__init__("FFT", input_trace_id, **kwargs)
        
        # Analysis settings
        self._window_type = kwargs.get('window', 'hanning')
        self._remove_dc = kwargs.get('remove_dc', True)
        self._db_ref = kwargs.get('db_ref', 1.0)  # For dB conversion
        
        # Create magnitude trace
        self._mag_trace = self.create_trace(
            x_data=np.array([]),
            y_data=np.array([]),
            name="Magnitude",
            color="#00FFFF"
        )
        
        # Peak marker
        self._peak = self.create_marker(
            x=0, y=0,
            name="Peak",
            color="#FF00FF"
        )
        
        self.update()
        
    def _apply_window(self, data: np.ndarray) -> np.ndarray:
        """Apply selected window function."""
        window_func = self.WINDOWS[self._window_type][0]
        return data * window_func(len(data))
        
    def _compute_freq_axis(self, x_data: np.ndarray) -> np.ndarray:
        """Compute frequency axis."""
        dt = np.mean(np.diff(x_data))
        fs = 1/dt
        freqs = np.fft.rfftfreq(len(x_data), dt)
        return freqs
        
    def _to_db(self, magnitude: np.ndarray) -> np.ndarray:
        """Convert to dB."""
        return 20 * np.log10(np.abs(magnitude) / self._db_ref)

class FFT(SpectralAnalysis):
    """Single trace FFT analysis."""
    def __init__(self, input_trace_id: str, **kwargs):
        super().__init__(input_trace_id, **kwargs)
        self._mag_trace.name = "FFT Magnitude"
        
        # Add phase trace
        self._phase_trace = self.create_trace(
            x_data=np.array([]),
            y_data=np.array([]),
            name="Phase",
            color="#FF8800"
        )
        
        self.update()
        
    def update(self):
        x_data, y_data = self.get_analysis_data()
        if len(y_data) < 2:
            return
            
        # Remove DC if requested
        if self._remove_dc:
            y_data = y_data - np.mean(y_data)
            
        # Apply window
        windowed = self._apply_window(y_data)
        
        # Compute FFT
        spectrum = np.fft.rfft(windowed)
        freqs = self._compute_freq_axis(x_data)
        
        # Convert to dB
        magnitude = self._to_db(spectrum)
        phase = np.angle(spectrum, deg=True)
        
        # Update traces
        self._mag_trace.data = (freqs, magnitude)
        self._phase_trace.data = (freqs, phase)
        
        # Find peak
        peak_idx = np.argmax(magnitude)
        self._peak.x = freqs[peak_idx]
        self._peak.y = magnitude[peak_idx]
        self._peak.label = (f"Peak:\n{freqs[peak_idx]:.2f}Hz\n"
                          f"{magnitude[peak_idx]:.1f}dB")
        
class PeriodMeasurement(Analysis):
    """Period/frequency measurement between two cursors."""
    def __init__(self, input_trace_id: str, **kwargs):
        super().__init__("Period Measurement", input_trace_id, **kwargs)
        
        # Create cursors
        self._x1 = self.create_cursor(
            position=0, axis='x', name="X1",
            color="#FFFF00"
        )
        self._x2 = self.create_cursor(
            position=0, axis='x', name="X2",
            color="#FFFF00"
        )
        
        # Create result marker
        self._result = self.create_marker(
            x=0, y=0, name="Period",
            color="#FFFF00"
        )
        
        self._auto_place_cursors()
        
    def _auto_place_cursors(self):
        """Place cursors at zero crossings."""
        trace = self.input_trace
        if not trace:
            return
            
        x_data, y_data = trace.data
        if len(y_data) < 2:
            return
            
        # Find zero crossings
        zero_crossings = np.where(np.diff(np.signbit(y_data)))[0]
        if len(zero_crossings) >= 2:
            self._x1.position = x_data[zero_crossings[0]]
            self._x2.position = x_data[zero_crossings[1]]
            
        self.update()
        
    def update(self):
        """Update measurement."""
        period = abs(self._x2.position - self._x1.position)
        freq = 1.0 / period if period != 0 else 0
        
        # Update marker position and label
        mid_x = (self._x1.position + self._x2.position) / 2
        y_pos = self.input_trace.y_data.max() * 0.9  # Place near top
        
        self._result.x = mid_x
        self._result.y = y_pos
        self._result.label = f"Period: {period:.2e}s\nFreq: {freq:.2f}Hz"

class PeakToPeak(Analysis):
    """Peak-to-peak measurement with horizontal cursors."""
    def __init__(self, input_trace_id: str, **kwargs):
        super().__init__("Peak-to-Peak", input_trace_id, **kwargs)
        
        # Create cursors at min/max
        self._y_max = self.create_cursor(
            position=0, axis='y', name="Max",
            color="#FF00FF"
        )
        self._y_min = self.create_cursor(
            position=0, axis='y', name="Min",
            color="#FF00FF"
        )
        
        self._result = self.create_marker(
            x=0, y=0, name="P-P",
            color="#FF00FF"
        )
        
        self.update()
        
    def update(self):
        """Update min/max cursors and measurement."""
        trace = self.input_trace
        if not trace:
            return
            
        x_data, y_data = trace.data
        if len(y_data) < 2:
            return
            
        y_min, y_max = y_data.min(), y_data.max()
        self._y_min.position = y_min
        self._y_max.position = y_max
        
        # Place result marker
        x_pos = x_data[len(x_data)//2]  # Middle of x range
        y_pos = (y_max + y_min) / 2  # Middle of y range
        
        self._result.x = x_pos
        self._result.y = y_pos
        self._result.label = f"P-P: {y_max - y_min:.2f}"