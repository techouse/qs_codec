"""Overflow marker for list limit conversions."""

from __future__ import annotations


class OverflowDict(dict):
    """A mutable marker for list overflows when `list_limit` is exceeded."""

    def copy(self) -> "OverflowDict":
        """Return an OverflowDict copy to preserve the overflow marker."""
        return OverflowDict(super().copy())

    def __copy__(self) -> "OverflowDict":
        """Return an OverflowDict copy to preserve the overflow marker."""
        return OverflowDict(super().copy())
