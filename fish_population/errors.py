"""Error type carrying the location of invalid input."""


class ConfigError(ValueError):
    """Raised when the input configuration is invalid.

    The message always identifies the offending location, for example
    ``scenarios[0].yearly[2].fishing[1]``.
    """
