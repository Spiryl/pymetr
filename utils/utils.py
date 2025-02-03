
def si_str_to_float(value_str):
    """
    Convert SCPI string with unit suffix to float.

    Args:
        value_str (str): The SCPI string to convert, e.g., '100M', '50k', '200m'.

    Returns:
        float: The converted float value.
    """
    # Define a dictionary mapping suffixes to their multiplier values
    suffix_multipliers = {
        'Y': 1e24,  # Yotta
        'Z': 1e21,  # Zetta
        'E': 1e18,  # Exa
        'P': 1e15,  # Peta
        'T': 1e12,  # Tera
        'G': 1e9,   # Giga
        'M': 1e6,   # Mega
        'k': 1e3,   # Kilo
        'h': 1e2,   # Hecto
        'da': 1e1,  # Deca
        'd': 1e-1,  # Deci
        'c': 1e-2,  # Centi
        'm': 1e-3,  # Milli
        'u': 1e-6,  # Micro
        'n': 1e-9,  # Nano
        'p': 1e-12, # Pico
        'f': 1e-15, # Femto
        'a': 1e-18, # Atto
        'z': 1e-21, # Zepto
        'y': 1e-24, # Yocto
    }

    # Check if the last character is a digit (no suffix)
    if value_str[-1].isdigit():
        return float(value_str)

    # Extract the numeric part and the suffix
    numeric_part = value_str[:-1]
    suffix = value_str[-1]

    # Special handling for 'da' since it's the only two-letter suffix
    if value_str.endswith("da"):
        numeric_part = value_str[:-2]
        suffix = "da"

    # Convert the numeric part to float and multiply by the suffix multiplier
    if suffix in suffix_multipliers:
        return float(numeric_part) * suffix_multipliers[suffix]
    else:
        raise ValueError(f"Unsupported SCPI suffix: '{suffix}' in value '{value_str}'")

