PyMetr Documentation
==========================

Purpose
-------
This project empowers engineers to craft their own test routines and software, streamlining design verification automation. By providing a pristine example platform, it serves as the seed for future development, offering a crystalline foundation from which test scripts and virtual front panels for a variety of test equipment can be built.

Todo
----

- Standardize enumeration string format across subsystems.
- Add doc-strings to subsystem enum types explaining operation modes.
- Standardize doc-strings format away from the sphinx style parameters.
- Create subsystems.py to manage all subystems and refactor.
- Update subsystem abstract base class and allowed instrument subsystem calls.
- Documentation graphics and hyper-links.
- Start spectrum analyzer class.
- Start power meter class.
- Get package published. 
- Rework GUI controls.
- Refactor Oscilloscope GUI acquisition thread.

System Dependencies
-------------------
- **Python Version**: 3.12.0
- **pyvisa**: Instrument communication
- **pyside6**: Qt bindings and GUI application development
- **numpy**: Efficient numerical computations
- **vispy**: High-performance graphics

.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   quickstart
   instruments
   subsystems
   subsystem_theory
   factories
   design
   oscilloscope
   packaging
   doc-build
   sphinx
   bible
   logging
   unit-test
