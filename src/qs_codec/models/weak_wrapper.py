"""A wrapper that allows weak references to be used as dictionary keys."""

import typing as t
import weakref
from collections.abc import Mapping
from dataclasses import dataclass


# weak-value dictionary: values are kept **weakly**
_proxy_cache: "weakref.WeakValueDictionary[int, _Refable]" = weakref.WeakValueDictionary()


class _Refable:
    __slots__ = ("value", "__weakref__")  # allow weak-refs

    def __init__(self, value: t.Any):
        self.value = value


@dataclass(frozen=True)
class WeakWrapper:
    """Weakly wraps *any* object (even dicts/lists) with deep-content hashing and identity equality."""

    _proxy: _Refable  # strong ref while the wrapper lives
    _value_id: int
    _wref: weakref.ReferenceType["_Refable"]  # weak ref for hash/GC callbacks

    def __init__(self, value: t.Any):
        """Initialize the WeakWrapper with a value."""
        # obtain (or create) a shared proxy for this value
        proxy = _proxy_cache.get(id(value))
        if proxy is None:
            proxy = _Refable(value)
            _proxy_cache[id(value)] = proxy

        object.__setattr__(self, "_proxy", proxy)  # strong
        object.__setattr__(self, "_value_id", id(value))
        object.__setattr__(self, "_wref", weakref.ref(proxy))  # weak

    # Equality / hash
    def __eq__(self, other: object) -> bool:
        """Compare two `WeakWrapper` objects."""
        return isinstance(other, WeakWrapper) and self._value_id == other._value_id

    def __hash__(self) -> int:
        """Return the hash of the value."""
        return self._hash_recursive(self._proxy.value, seen=set(), stack=set())

    # Recursive hash with cycle/Depth checks
    def _hash_recursive(
        self,
        value: t.Any,
        seen: t.Set[int],
        stack: t.Set[int],
        depth: int = 0,
        max_depth: int = 400,  # default recursion limit
    ) -> int:
        """Recursively hash a value."""
        vid = id(value)
        if vid in stack:
            raise ValueError("Circular reference detected")
        if depth > max_depth:
            raise RecursionError("Maximum recursion depth exceeded")

        stack.add(vid)
        try:
            if isinstance(value, Mapping):
                return hash(
                    tuple(sorted((k, self._hash_recursive(v, seen, stack, depth + 1)) for k, v in value.items()))
                )
            elif isinstance(value, (list, set, tuple)):
                seq = (
                    self._hash_recursive(v, seen, stack, depth + 1)
                    for v in (sorted(value) if isinstance(value, set) else value)
                )
                return hash(tuple(seq))
            else:
                return hash(value)
        finally:
            stack.remove(vid)

    # Helpful property
    @property
    def value(self) -> t.Any:
        """Return the value of the weak reference."""
        proxy = self._wref()  # dereference weakly
        if proxy is None:
            raise ReferenceError("original object has been garbage-collected")
        return proxy.value
