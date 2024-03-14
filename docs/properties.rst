Command Properties
==================

**This document has been updated but needs a lot of work**

The ``pymetr`` library presents a sleek and modernized methodology for instrument communication, cutting down on the traditional complexity associated with direct device interaction. The factory functions `switch_property`, `select_property`, and `value_property` enable developers to define instrument properties efficiently, promoting code clarity, robustness, and easier maintenance.

Streamlining Property Synchronization
-------------------------------------

The old-school way of syncing object properties with instrument states typically demanded verbose getters and setters. Although it gets the job done, it's prone to clutter up your codebase, making it prone to mistakes and harder to look after.

Peep this old-style example:

.. code-block:: python

    class Acquire:
        def __init__(self, parent):
            self._parent = parent
            self._type = None
            self._depth = None

        @property
        def type(self):
            response = self._parent.query(":ACQuire:TYPE?")
            self._type = response.strip()
            return self._type

        @type.setter
        def type(self, value):
            valid_types = ["NORM", "AVER"]
            if value in valid_types:
                self._parent.write(f":ACQuire:TYPE {value}")
                self._type = value
            else:
                raise ValueError("Invalid acquisition type")

        # And you gotta repeat this for every property...

It works, but man, that's a lot of typing for what should be a simple thing.

Revamping with `switch_property`, `select_property`, and `value_property`
--------------------------------------------------------------------------

`switch_property`, `select_property`, and `value_property` factory functions are straight game changers. They let you whip up properties with built-in getters and setters that are tuned to the specific commands of your instrument.

Check out the `Acquire` subsystem glow-up:

.. code-block:: python

    from pymetr.subsystem import Subsystem, switch_property, select_property, value_property

    class Acquire(Subsystem):
        type = select_property(":TYPE", ['NORMAL', 'AVERAGE', 'HRES', 'PEAK'], doc_str="Type of acquisition.")
        depth = value_property(":DEPTH", type="int", range=[1, 10000], doc_str="Acquisition depth.")
        
        def __init__(self, parent):
            super().__init__(parent, cmd_prefix=":ACQuire")

No more repetitive code, and it's all wrapped up in a much tidier package.

Conclusion
----------

Jumping on the `switch_property`, `select_property`, and `value_property` bandwagon, as rolled out by `pymetr`, leads to a more streamlined and robust way to roll out instrument control interfaces. This method is not only simpler but also solidifies type safety and slims down the chances of bugs creeping in, making the dev life a whole lot smoother.
