# pymetr/__init__.py

# Update the __all__ list to include specific classes you want to expose.
__all__ = ['Instrument', 'Subsystem', 'data_property', 'select_property', 'switch_property', 'value_property',]

try:
    from .instrument import Instrument, Subsystem  # Assuming Instrument is a class in the instruments module
    from .properties import data_property, select_property, switch_property, value_property
    
except ImportError as e:
    print(f"Failed to import within pymetr: {e}")
