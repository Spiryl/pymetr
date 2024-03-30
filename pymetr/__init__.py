# pymetr/__init__.py

# Update the __all__ list to include specific classes you want to expose.
__all__ = [
    'Instrument', 'Subsystem', 
    'DataProperty', 'SelectProperty', 'SwitchProperty', 'ValueProperty', 'StringProperty', 'Sources'
]

try:
    from .instrument import Instrument, Subsystem, Sources
    from .properties import DataProperty, SelectProperty, SwitchProperty, ValueProperty, StringProperty
except ImportError as e:
    print(f"Failed to import within pymetr: {e}")