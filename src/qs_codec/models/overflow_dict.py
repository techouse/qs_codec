"""Overflow marker for list limit conversions."""

from __future__ import annotations

import copy


class OverflowDict(dict):
    """A mutable marker for list overflows when `list_limit` is exceeded."""

    def copy(self) -> "OverflowDict":
        """Return an OverflowDict copy to preserve the overflow marker."""
        return self.__class__(super().copy())

    def __copy__(self) -> "OverflowDict":
        """Return an OverflowDict copy to preserve the overflow marker."""
        return self.__class__(super().copy())

    def __deepcopy__(self, memo: dict[int, object]) -> "OverflowDict":
        """Return an OverflowDict deepcopy to preserve the overflow marker."""
        copied = self.__class__()
        memo[id(self)] = copied
        for key, value in self.items():
            copied[copy.deepcopy(key, memo)] = copy.deepcopy(value, memo)
        return copied


class CommaOverflowDict(OverflowDict):
    """Overflow marker for comma-split values that exceeded `list_limit`."""
