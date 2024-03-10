Understanding Subsystems
========================

Welcome to the deeper dive into our instrumentation framework, focusing on the strategic use of subsystems to streamline instrument control. This section aims to illuminate the theory behind subsystems and their pivotal role in simplifying interaction with test equipment.

Overview
--------

The `Subsystem` is a foundational concept in our design philosophy, representing a logical component or a distinct functional unit within an instrument. Examples include waveform generators, oscilloscope channels, or power supply modules. Modeling these functions as separate subsystems enables us to encapsulate functionality, thereby simplifying the complex and making the inaccessible readily manageable.

Why Subsystems?
---------------

- **Modularity**: Breaks down complex instruments into manageable units for easier development and upkeep.
- **Reusability**: Allows for development once and deployment everywhere, reducing code duplication across instruments.
- **Extensibility**: Facilitates the addition of new features to existing instruments with minimal disruption.

How It Works
------------

Our approach leverages Python classes to encapsulate each subsystem. We utilize a base `Subsystem` class for common functionalities such as command execution and querying. Specialized subsystems inherit from this base class, tailoring it with specific capabilities.

The alignment with the SCPI command tree is particularly noteworthy. Instruments are often structured in a hierarchical command system, mirroring our subsystem model. This similarity allows our subsystem prefixes to closely match those of the SCPI commands, minimizing code duplication and maximizing efficiency.

.. note:: 

   The power of our model lies in its direct alignment with the SCPI command structure, utilizing subsystem prefixes to streamline command execution. This approach reduces code duplication and leverages modern IDEs for autocompletion, enabling script creation without constant reference to the programming manual.

Example: Setting Parameters
---------------------------

Consider setting parameters on an oscilloscope. Our subsystem approach abstracts the SCPI commands into intuitive property calls, making script development straightforward and IDE-friendly.

.. code-block:: python

    # Here `oscope` is an instance of an Oscilloscope class with an Acquire subsystem

    oscope.acquire.type = Acquire.Type.NORMAL  # Sets acquisition type to normal
    # Behind the scenes: scope.acquire.write(":ACQuire:TYPE NORM")

    oscope.acquire.sample_rate = 1e6  # Sets sample rate to 1 MSa/s
    # Behind the scenes: scope.acquire.write(":ACQuire:SRATe 1e6")

    print(scope.acquire.depth)  # Queries the current acquisition depth
    # Behind the scenes: scope.acquire.query(":ACQuire:DEPTh?")

This snippet demonstrates how each property or method call on a subsystem translates into a write or query to the instrument, abstracting the complexity of SCPI commands into user-friendly operations.
