Command Parameters and Options
==============================

The `pymetr` library introduces an efficient, streamlined approach to instrument control, significantly reducing the complexity traditionally associated with direct device communication. Through the innovative use of factory functions `command_property` and `command_options`, `pymetr` enables developers to define instrument properties with minimal code, enhancing maintainability, readability, and error handling.

Simplifying Property Synchronization
-------------------------------------

Traditionally, interfacing with instruments involves verbose getters and setters to synchronize object properties with instrument states. This method, while effective, results in extensive boilerplate code, increasing the likelihood of errors and complicating code maintenance.

Consider this conventional approach:

.. code-block:: python

    from enum import Enum

    class Acquire:
        class Type(Enum):
            NORMAL = "NORM"
            AVERAGE = "AVER"

        def __init__(self, parent):
            self._parent = parent
            self._type = None
            self._depth = None

        @property
        def type(self):
            response = self._parent.query(":ACQuire:TYPE?")
            self._type = self.Type(response.strip())
            return self._type

        @type.setter
        def type(self, value):
            if isinstance(value, self.Type):
                self._parent.write(f":ACQuire:TYPE {value.value}")
                self._type = value
            else:
                raise ValueError("Invalid acquisition type")

        # Similar code for 'depth' property

This example, while functional, involves a lot of repetitive code for defining each property, significantly bloating the class definition.

Introducing `command_property` and `command_options`
-----------------------------------------------------

`command_property` and `command_options` factory functions dramatically simplify property definition. `command_property` allows for the creation of properties with integrated getters and setters, tailored to specific instrument commands. `command_options` facilitates the definition of valid command parameters, enforcing valid values through enums.

Refactoring the Acquire Subsystem
----------------------------------

Using `command_property` and `command_options`, we can refactor the `Acquire` subsystem to achieve the same functionality with less code and improved readability:

.. code-block:: python

    from pymetr.instruments import Subsystem, command_property, command_options

    class Acquire(InstrumentSubsystem):
        Type = command_options('Type', ['NORMAL', 'AVERAGE', 'HRES', 'PEAK'])
        type = command_property(":TYPE", Type, "Type of acquisition.")
        mode = command_property(":MODE", Mode, "Current acquisition mode.")
        
        def __init__(self, parent):
            super().__init__(parent, cmd_prefix=":ACQuire")

This refactor significantly reduces the amount of boilerplate code, making the class definition cleaner and more maintainable. The `cmd_prefix` initialization parameter further streamlines command construction, eliminating the need to repeat the command prefix for each property.

Conclusion
----------

By adopting `command_property` and `command_options`, `pymetr` offers a more efficient and error-resistant method for developing instrument control interfaces. This approach not only simplifies property definition but also ensures type safety and reduces the potential for bugs, making instrument control software development more accessible and maintainable.

