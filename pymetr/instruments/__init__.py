# pymetr/instruments/__init__.py

# Update the __all__ list to include specific classes you want to expose.
__all__ = ['dsox1204g']

try:
    from pymetr.instruments import dsox1204g
    
except ImportError as e:
    print(f"Failed to import within pymetr: {e}")
