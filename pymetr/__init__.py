# Update the __all__ list to include specific classes or modules you want to expose.
__all__ = ['Instrument', 'Instrument', 'Oscilloscope', 'interfaces']

try:
    from .instruments import Instrument # Assuming Instrument is a class in the instruments module
    from .oscilloscope.core import Oscilloscope
    from . import interfaces
except ImportError as e:
    print(f"Failed to import within pymetr: {e}")
