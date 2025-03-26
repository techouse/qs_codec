"""Undefined class definition."""

import typing as t


class Undefined:
    """Singleton class to represent undefined values."""

    _instance = None

    def __new__(cls: t.Type["Undefined"]) -> "Undefined":
        """Create a new instance of the class."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
