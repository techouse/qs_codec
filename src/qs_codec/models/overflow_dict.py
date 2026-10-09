"""Overflow marker for list limit conversions."""

from __future__ import annotations

import copy
import typing as t

# Subscripted at type-check time only; subclassing `t.Dict[...]` would add `Generic` to the MRO on 3.8.
if t.TYPE_CHECKING:
    _DictBase = t.Dict[t.Any, t.Any]
else:
    _DictBase = dict


class OverflowDict(_DictBase):
    """A mutable marker for list overflows when `list_limit` is exceeded."""

    def copy(self) -> "OverflowDict":
        """Return an OverflowDict copy to preserve the overflow marker."""
        return self.__class__(super().copy())

    def __copy__(self) -> "OverflowDict":
        """Return an OverflowDict copy to preserve the overflow marker."""
        return self.__class__(super().copy())

    def __deepcopy__(self, memo: t.Dict[int, t.Any]) -> "OverflowDict":
        """Return an OverflowDict deepcopy to preserve the overflow marker."""
        copied = self.__class__()
        memo[id(self)] = copied
        for key, value in self.items():
            copied[copy.deepcopy(key, memo)] = copy.deepcopy(value, memo)
        return copied


class CommaOverflowDict(OverflowDict):
    """Overflow marker for comma-split values that exceeded `list_limit`."""
