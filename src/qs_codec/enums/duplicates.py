"""This module contains an enum of all available duplicate key handling strategies."""

from enum import Enum


class Duplicates(Enum):
    """An enum of all available duplicate key handling strategies."""

    # Combine duplicate keys into a single key with an array of values.
    COMBINE = 1

    # Use the first value for duplicate keys.
    FIRST = 2

    # Use the last value for duplicate keys.
    LAST = 3
