"""Duplicate-key handling strategies used during decoding.

When a query string contains the same key multiple times, decoders need a policy
to resolve them. The ``Duplicates`` enum is referenced by ``DecodeOptions`` to
control that behavior.
"""

from enum import Enum, auto


class Duplicates(Enum):
    """Defines how to resolve duplicate keys produced during parsing.

    This is consulted by the decoder when more than one value is encountered for
    the same key. It does not affect encoding.

    Members
    -------
    COMBINE
        Combine duplicate keys into a single list of values (preserves order).
    FIRST
        Keep only the first occurrence and discard subsequent ones.
    LAST
        Keep only the last occurrence, overwriting prior ones.
    """

    COMBINE = auto()
    """Combine duplicate keys into a single list of values (preserves order)."""

    FIRST = auto()
    """Keep only the first value encountered for the key."""

    LAST = auto()
    """Keep only the last value encountered for the key."""
