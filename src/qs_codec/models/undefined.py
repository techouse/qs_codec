"""Undefined class definition."""


class Undefined:
    """Singleton class to represent undefined values."""

    _instance = None

    def __new__(cls):
        """Create a new instance of the class."""
        if cls._instance is None:
            cls._instance = super(Undefined, cls).__new__(cls)
        return cls._instance
