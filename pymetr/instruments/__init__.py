# pymetr/instruments/__init__.py

# Update the __all__ list to include specific classes you want to expose.
__all__ = ['DSOX1204G']

try:
    from pymetr.instruments import DSOX1204G
    
except ImportError as e:
    print(f"Failed to import within pymetr: {e}")
