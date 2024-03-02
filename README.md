# PyInstrument

PyInstrument is a Python library designed to simplify the communication and control of various test and measurement instruments. Whether you're working with GPIB, USB, Serial, or Ethernet-connected devices, PyInstrument provides a unified interface for managing these connections.

## Features

- **Unified Interface**: Communicate seamlessly with instruments regardless of the connection protocol.
- **Modular Design**: Easily extendable to support new types of instruments or communication protocols.
- **CLI Integration**: Comes with a built-in command line interface for direct interaction with instruments.
- **Example Scripts**: Includes examples to get you started with common tasks.

## Installation

You can install PyInstrument directly from GitHub using pip:

```bash
pip install git+https://github.com/yourusername/pyinstrument.git
```

## Quick Start

Here's a quick example of how to use PyInstrument to query an instrument's identity:

```python
from pyinstrument import SCPIInstrument

# Replace 'RESOURCE_STRING' with your instrument's resource string
instrument = SCPIInstrument('RESOURCE_STRING')
instrument.open()

print(instrument.query('*IDN?'))

instrument.close()
```

## Documentation

For detailed documentation, visit [Link to Documentation](#).

## Examples

Check out the `examples/` directory for more examples on how to use PyInstrument.

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on how to submit pull requests, how to report bugs, and how to request new features.

## License

PyInstrument is licensed under the [MIT License](LICENSE).

## Authors

- Ryan C. Smith
- Metatron

## Acknowledgments

Thanks to all the contributors who have helped shape PyInstrument into what it is today!
