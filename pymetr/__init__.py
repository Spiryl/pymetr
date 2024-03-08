# Update the __all__ list to include specific classes or modules you want to expose.
__all__ = ['Instrument', 'Oscilloscope', Subsystem]

try:
    from .instrument import Instrument # Assuming Instrument is a class in the instruments module
    from .subsystem import Subsystem
    from .oscilloscope import Oscilloscope
except ImportError as e:
    print(f"Failed to import within pymetr: {e}")
