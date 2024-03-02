# Update the __all__ list to include specific classes or modules you want to expose.
__all__ = ['Instrument', 'SCPIInstrument', 'Oscilloscope', 'interfaces']

try:
    from .instruments import Instrument, SCPIInstrument  # Assuming SCPIInstrument is a class in the instruments module
    from .oscilloscope.core import Oscilloscope
    from . import interfaces
except ImportError as e:
    print(f"Failed to import within pyinstrument: {e}")
