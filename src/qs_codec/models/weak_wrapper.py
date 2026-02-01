"""Weakly wrap *any* object with identity equality and stable hashing."""

from __future__ import annotations

import reprlib
import typing as t
from threading import RLock
from weakref import ReferenceType, WeakValueDictionary, ref


class _Proxy:
    """Container for the original object.

    NOTE: Proxies must be weak-referenceable because the cache holds them in a WeakValueDictionary. That requires "__weakref__" in __slots__.
    """

    __slots__ = ("value", "__weakref__")

    def __init__(self, value: t.Any) -> None:
        """Strong ref to the value so hash/equality can access it while a wrapper keeps this proxy alive."""
        self.value = value


__all__ = ["WeakWrapper", "_proxy_cache"]


# Exported for tests
_proxy_cache: "WeakValueDictionary[int, _Proxy]" = WeakValueDictionary()
_proxy_cache_lock = RLock()


def _get_proxy(value: t.Any) -> "_Proxy":
    """Return a per-object proxy, cached by id(value)."""
    key = id(value)
    with _proxy_cache_lock:
        proxy = _proxy_cache.get(key)
        if proxy is None:
            proxy = _Proxy(value)
            _proxy_cache[key] = proxy
        return proxy


class WeakWrapper:
    """Wrapper suitable for use as a WeakKeyDictionary key.

    - Holds a *strong* reference to the proxy (keeps proxy alive while wrapper exists).
    - Exposes a weakref to the proxy via `_wref` so tests can observe/force GC.
    - Equality is proxy identity; hash is the proxy identity (stable across mutations).
    """

    __slots__ = ("_proxy", "_wref", "__weakref__")
    _proxy: _Proxy
    _wref: ReferenceType[_Proxy]

    def __init__(self, value: t.Any) -> None:
        """Initialize the wrapper with a value."""
        proxy = _get_proxy(value)
        # Strong edge: wrapper -> proxy
        object.__setattr__(self, "_proxy", proxy)
        # Weak edge so tests can observe GC of the proxy
        object.__setattr__(self, "_wref", ref(proxy))

    @property
    def value(self) -> t.Any:
        """Guard with the weakref so tests can simulate GC by swapping _wref."""
        if self._wref() is None:
            raise ReferenceError("Original object has been garbage-collected")
        return self._proxy.value

    def __repr__(self) -> str:
        """Return a string representation of the wrapper."""
        if self._wref() is None:
            return "WeakWrapper(<gc'd>)"
        # Use reprlib to avoid excessive size and recursion issues without broad exception handling.
        return f"WeakWrapper({reprlib.repr(self._proxy.value)})"

    def __eq__(self, other: object) -> bool:
        """Check equality by comparing the proxy identity."""
        if not isinstance(other, WeakWrapper):
            return NotImplemented
        # Same underlying object => same cached proxy instance
        return self._proxy is other._proxy

    def __hash__(self) -> int:
        """Return a stable hash based on the proxy identity."""
        return hash(self._proxy)
