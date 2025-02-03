# hp8563a.py

"""
HP 8563A Spectrum Analyzer Driver with improved non-blocking trace acquisition
"""

import logging
from enum import Enum
import numpy as np

from pymetr.drivers.base import Subsystem
from pymetr.drivers.base import SCPIInstrument
from pymetr.drivers.base import (
    ValueProperty, SelectProperty, SwitchProperty, DataProperty
)

logger = logging.getLogger(__name__)

class TriggerMode(Enum):
    FREE = "FREE"
    SINGLE = "SNGLS"
    LINE = "LINE"
    VIDEO = "VID"
    EXTERNAL = "EXT"

class ScaleType(Enum):
    LINEAR = "LIN"
    LOG = "LOG"

class DetectorMode(Enum):
    NORMAL = "NRM"
    POSITIVE = "POS"
    NEGATIVE = "NEG"
    SAMPLE = "SMP"

class FrequencySubsystem(Subsystem):
    """Frequency control subsystem"""
    center = ValueProperty("CF", type="float", doc_str="Center freq (e.g. '1GHz')")
    span = ValueProperty("SP", type="float", doc_str="Span freq (e.g. '100MHz')")
    start = ValueProperty("FA", type="float", doc_str="Start frequency")
    stop = ValueProperty("FB", type="float", doc_str="Stop frequency")

class AmplitudeSubsystem(Subsystem):
    """Amplitude and attenuation control"""
    reference_level = ValueProperty("RL", type="float", range=(-139.9, 30), units="dBm", doc_str="Reference level")
    attenuation = ValueProperty("AT", type="float", range=(0, 70), units="dB", doc_str="Input attenuation")
    scale_type = SelectProperty("SCAL", ["LIN", "LOG"], doc_str="Amplitude scale type")

class BandwidthSubsystem(Subsystem):
    """Resolution and video bandwidth control"""
    resolution = ValueProperty("RB", type="float", range=(10, 3e6), units="Hz", doc_str="Resolution bandwidth")
    video = ValueProperty("VB", type="float", range=(1, 3e6), units="Hz", doc_str="Video bandwidth")

class SweepSubsystem(Subsystem):
    """Sweep control subsystem"""
    time = ValueProperty("ST", type="float", range=(20e-6, 100), units="s", doc_str="Sweep time")
    auto_time = SwitchProperty("ST AUTO", doc_str="Auto sweep time")
    trigger_mode = SelectProperty("TM", TriggerMode, doc_str="Trigger mode selection")
    continuous = SwitchProperty("CONTS", doc_str="Continuous sweep")

class TraceSubsystem(Subsystem):
    """Trace data and display control"""
    detector = SelectProperty("DET", DetectorMode, doc_str="Trace detector mode")
    data = DataProperty("TRA", access='read', doc_str="Trace A data (601 points)", 
                       container=np.array, converter=float, separator=',', terminator='\r\n')

class HP8563A(SCPIInstrument):
    """
    HP8563A Spectrum Analyzer driver with improved non-blocking trace acquisition.
    
    Features:
    - Full frequency control (start/stop/center/span)
    - Resolution and video bandwidth
    - Reference level and attenuation
    - Sweep and trigger controls
    - Non-blocking trace data acquisition
    """

    def __init__(self, connection):
        super().__init__(connection)
        logger.debug("Initializing HP8563A Spectrum Analyzer Driver")

        # Build subsystems
        logger.debug("Building subsystems")
        self.frequency = FrequencySubsystem.build(self, "")
        self.amplitude = AmplitudeSubsystem.build(self, "")
        self.bandwidth = BandwidthSubsystem.build(self, "")
        self.sweep = SweepSubsystem.build(self, "")
        self.trace = TraceSubsystem.build(self, "")
        logger.debug("Subsystems initialized successfully")

        # Initialize state
        self._sweep_in_progress = False
        self._sweep_complete = False

    def fetch_trace(self):
        """
        Start trace acquisition and emit signal when complete.
        Uses non-blocking reads to prevent UI blocking.
        """
        try:
            logger.debug("Starting trace acquisition")
            
            # Clear any previous sweep state
            self._sweep_in_progress = False
            self._sweep_complete = False
            
            # Put in single sweep mode and start sweep
            self.sweep.trigger_mode = TriggerMode.SINGLE
            self.write("SNGLS")
            self._sweep_in_progress = True
            
            # Get sweep parameters using property system
            start_freq = self.frequency.start
            stop_freq = self.frequency.stop
            sweep_time = self.sweep.time
            
            # Now read the trace data - this will use our non-blocking read implementation
            amp_data = self.trace.data
            
            # Create frequency axis
            freq_points = len(amp_data)
            freq_axis = np.linspace(start_freq, stop_freq, freq_points)
            
            # Emit the data
            self.traceDataReady.emit(freq_axis, amp_data)
            logger.debug(f"Emitted trace data: {freq_points} points")
            
            self._sweep_complete = True
            self._sweep_in_progress = False
            
            return freq_axis, amp_data
        
        except Exception as e:
            self._sweep_in_progress = False
            logger.error(f"Error in fetch_trace: {e}")
            self.exceptionOccured.emit(str(e))
            raise

    def is_sweep_complete(self) -> bool:
        """Check if the current sweep operation is complete."""
        if not self._sweep_in_progress:
            return self._sweep_complete
            
        try:
            # Check sweep status
            response = self.query("DONE?")
            if response.strip() == "1":
                self._sweep_in_progress = False
                self._sweep_complete = True
                
        except Exception as e:
            logger.error(f"Error checking sweep status: {e}")
            self._sweep_in_progress = False
            
        return self._sweep_complete

    def abort_sweep(self):
        """Abort the current sweep operation."""
        try:
            self.write("ABORT")
            self._sweep_in_progress = False
            self._sweep_complete = False
        except Exception as e:
            logger.error(f"Error aborting sweep: {e}")
            raise

    def single_sweep(self):
        """Initiates a single sweep."""
        logger.debug("Initiating single sweep")
        try:
            self.sweep.trigger_mode = TriggerMode.SINGLE
            self.write("SNGLS")
            self._sweep_in_progress = True
            self._sweep_complete = False
        except Exception as e:
            logger.error(f"Error initiating single sweep: {e}")
            raise

    def continuous_sweep(self):
        """Sets continuous sweep mode."""
        logger.debug("Setting continuous sweep mode")
        try:
            self.sweep.trigger_mode = TriggerMode.FREE
            self.write("CONT")
            self._sweep_in_progress = False
            self._sweep_complete = False
        except Exception as e:
            logger.error(f"Error setting continuous sweep mode: {e}")
            raise

    def preset(self):
        """Presets the instrument to default state."""
        logger.debug("Presetting instrument to default state")
        try:
            self.write("IP")
            self._sweep_in_progress = False
            self._sweep_complete = False
        except Exception as e:
            logger.error(f"Error presetting instrument: {e}")
            raise

    def get_identity(self) -> str:
        """
        Query the instrument identity (*IDN?).
        
        Returns:
            str: The instrument's identification string
        """
        logger.debug("Querying instrument identity")
        try:
            identity = self.query("ID?")
            logger.debug(f"Instrument identity: {identity}")
            return identity
        except Exception as e:
            logger.error(f"Error querying instrument identity: {e}")
            raise

    def check_error(self) -> tuple[int, str]:
        """
        Query the error queue.
        
        Returns:
            tuple: (error_code, error_message)
        """
        try:
            response = self.query("ERR?")
            code = int(response)
            msg = {
                0: "No error",
                -410: "Query INTERRUPTED",
                -420: "Query UNTERMINATED",
                -430: "Query DEADLOCKED"
            }.get(code, "Unknown error")
            return code, msg
        except Exception as e:
            logger.error(f"Error checking error queue: {e}")
            raise