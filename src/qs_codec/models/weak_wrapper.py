"""A wrapper that allows weak references to be used as dictionary keys."""

import typing as t
from dataclasses import dataclass


@dataclass(frozen=True)
class WeakWrapper:
    """A wrapper that allows weak references to be used as dictionary keys."""

    value: t.Any

    def __hash__(self) -> int:
        """Return the hash of the value."""
        return hash(self._hash_recursive(self.value, seen=set(), stack=set()))

    def _hash_recursive(
        self, value: t.Any, seen: set, stack: set, depth: int = 0, max_depth: int = 1000
    ) -> t.Union[t.Tuple, t.Any]:
        """Recursively hash a value."""
        if id(value) in stack:
            raise ValueError("Circular reference detected")

        seen.add(id(value))
        stack.add(id(value))

        if depth > max_depth:
            raise ValueError("Maximum recursion depth exceeded")

        if isinstance(value, t.Mapping):
            result = tuple((k, self._hash_recursive(v, seen, stack, depth + 1)) for k, v in sorted(value.items()))
        elif isinstance(value, (t.List, t.Set)):
            result = tuple(self._hash_recursive(v, seen, stack, depth + 1) for v in value)
        else:
            result = value

        stack.remove(id(value))

        return result
