"""Weak-wrapper utilities for using arbitrary (incl. mutable) objects as keys.

This module exposes :class:`WeakWrapper`, a tiny helper that:
- keeps only a **weak reference** to the underlying value (so it won't keep it alive),
- compares **by identity** (two wrappers are equal iff they wrap the *same* object),
- computes a **deep, content-based hash** with cycle and depth protection.

⚠️ Caveat: because the hash is computed from the *current* content, mutating a
container *after* it has been used as a key in a dict/set can violate Python’s
hash contract and lead to look‑up anomalies. Only use this in contexts where
wrapped values are effectively immutable while they participate as keys.
"""

import typing as t
import weakref
from collections.abc import Mapping
from dataclasses import dataclass


# Global weak-value cache of lightweight proxy objects.
# Keyed by the CPython object id() of the wrapped value → value held **weakly**.
# This lets multiple WeakWrapper instances share the same proxy while ensuring
# the original object can still be garbage‑collected.
_proxy_cache: "weakref.WeakValueDictionary[int, _Refable]" = weakref.WeakValueDictionary()


class _Refable:
    """Simple holder that supports being weak‑referenced."""

    __slots__ = ("value", "__weakref__")  # allow weak-refs

    def __init__(self, value: t.Any):
        """Store the wrapped value."""
        self.value = value


@dataclass(frozen=True)
class WeakWrapper:
    """Weakly wrap *any* object with identity equality and deep content hashing.

    Equality: two wrappers are equal iff they wrap the **same** underlying object
    (i.e. their `id(value)` matches). This avoids the pitfalls of comparing
    mutable containers by content.

    Hashing: the hash is derived by recursively hashing the current content of
    the wrapped value (mappings by key/value pairs, sequences in order, sets as
    a sorted sequence). Cycles raise ``ValueError`` and recursion beyond
    ``max_depth`` raises ``RecursionError``.
    """

    # Strong ref while the wrapper lives; the cache holds a weak one.
    _proxy: _Refable
    # Captured object id() for cheap identity checks.
    _value_id: int
    # Weak reference used to avoid prolonging object lifetime.
    _wref: weakref.ReferenceType["_Refable"]

    def __init__(self, value: t.Any):
        """Initialize a wrapper around ``value`` using a shared proxy."""
        # Obtain (or create) a shared proxy for this value's id.
        proxy = _proxy_cache.get(id(value))
        if proxy is None:
            proxy = _Refable(value)
            _proxy_cache[id(value)] = proxy

        # dataclass(frozen=True) → assign via object.__setattr__
        object.__setattr__(self, "_proxy", proxy)  # strong edge
        object.__setattr__(self, "_value_id", id(value))  # identity stamp
        object.__setattr__(self, "_wref", weakref.ref(proxy))  # weak edge

    # -------------------------
    # Equality / hashing
    # -------------------------

    def __eq__(self, other: object) -> bool:
        """Return True if both wrappers reference the same underlying object."""
        return isinstance(other, WeakWrapper) and self._value_id == other._value_id

    def __hash__(self) -> int:
        """Compute a deep, content-based hash of the wrapped value."""
        return self._hash_recursive(self._proxy.value, seen=set(), stack=set())

    # Recursive hash with cycle and depth checks
    def _hash_recursive(
        self,
        value: t.Any,
        seen: t.Set[int],
        stack: t.Set[int],
        depth: int = 0,
        max_depth: int = 400,  # default recursion limit
    ) -> int:
        """Recursively hash ``value`` with cycle and depth protection.

        Mappings are hashed as an ordered tuple of (key, hashed-value) pairs
        sorted by key. Lists and tuples are hashed by element order. Sets are
        hashed by the tuple of their elements hashed after sorting to ensure a
        stable order across runs.

        Raises:
            ValueError: if a circular reference is encountered.
            RecursionError: if recursion exceeds ``max_depth``.
        """
        vid = id(value)
        if vid in stack:
            raise ValueError("Circular reference detected")
        if depth > max_depth:
            raise RecursionError("Maximum recursion depth exceeded")

        stack.add(vid)
        try:
            if isinstance(value, Mapping):
                # Hash as sorted (key, hashed(value)) pairs for stability.
                items = ((k, self._hash_recursive(v, seen, stack, depth + 1)) for k, v in value.items())
                return hash(tuple(sorted(items)))
            elif isinstance(value, (list, tuple, set)):
                # Sets are unordered → sort to get a stable hashing order.
                iterable = sorted(value) if isinstance(value, set) else value
                seq = (self._hash_recursive(v, seen, stack, depth + 1) for v in iterable)
                return hash(tuple(seq))
            else:
                return hash(value)
        finally:
            stack.remove(vid)

    # -------------------------
    # Accessors
    # -------------------------

    @property
    def value(self) -> t.Any:
        """Return the currently wrapped value or raise if it was GC'ed."""
        proxy = self._wref()  # dereference weakly
        if proxy is None:
            raise ReferenceError("Original object has been garbage-collected")
        return proxy.value
