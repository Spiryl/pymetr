# Pymetr/oscilloscope/__init__.py

from .core import Oscilloscope  # Assuming this is the correct class name

# Import subsystems
from .acquire import Acquire
from .channel import Channel
from .timebase import Timebase
from .trigger import Trigger
from .waveform import Waveform
from .wavegen import WaveGen

__all__ = [
    "Oscilloscope",
    "Acquire",
    "Channel",
    "Timebase",
    "Trigger",
    "Waveform",
    "WaveGen",
]