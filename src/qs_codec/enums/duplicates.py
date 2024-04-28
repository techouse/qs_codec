"""This module contains an enum of all available duplicate key handling strategies."""

from enum import Enum


class Duplicates(Enum):
    """An enum of all available duplicate key handling strategies."""

    COMBINE = 1
    """Combine duplicate keys into a single key with an array of values."""

    FIRST = 2
    """Use the first value for duplicate keys."""

    LAST = 3
    """Use the last value for duplicate keys."""
