"""Undefined sentinel.

This module defines a tiny singleton `Undefined` used as a *sentinel* to mean “no value provided / omit this key”,
similar to JavaScript’s `undefined`.

Unlike `None` (which commonly means an explicit null), `Undefined` is used by the encoder and helper utilities to *skip*
emitting a key or to signal that a value is intentionally absent and should not be serialized.

The sentinel is identity-based: every construction returns the same instance, so `is` comparisons are reliable
(e.g., `value is Undefined()`).
"""

import threading
import typing as t


class Undefined:
    """Singleton sentinel object representing an “undefined” value.

    Notes:
        * This is **not** the same as `None`. Use `None` to represent a *null* value and `Undefined()` to represent “no value / omit”.
        * All calls to ``Undefined()`` return the same instance. Prefer identity checks (``is``) over equality checks.

    Examples:
        >>> from qs_codec.models.undefined import Undefined
        >>> a = Undefined()
        >>> b = Undefined()
        >>> a is b
        True
        >>> # Use it to indicate a key should be omitted when encoding:
        >>> maybe_value = Undefined()
        >>> if maybe_value is Undefined():
        ...     pass  # skip emitting the key
    """

    __slots__ = ()
    _lock: t.ClassVar[threading.Lock] = threading.Lock()
    _instance: t.ClassVar[t.Optional["Undefined"]] = None

    def __new__(cls: t.Type["Undefined"]) -> "Undefined":
        """Return the singleton instance.

        Creating `Undefined()` multiple times always returns the same object reference. This ensures identity checks (``is``) are stable.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """Return a string representation of the singleton."""
        return "Undefined()"

    def __copy__(self):  # pragma: no cover - trivial
        """Ensure copies/pickles preserve the singleton identity."""
        return self

    def __deepcopy__(self, memo):  # pragma: no cover - trivial
        """Ensure deep copies preserve the singleton identity."""
        return self

    def __reduce__(self):  # pragma: no cover - trivial
        """Recreate via calling the constructor, which returns the singleton."""
        return Undefined, ()

    def __init_subclass__(cls, **kwargs):  # pragma: no cover - defensive
        """Prevent subclassing of Undefined."""
        raise TypeError("Undefined cannot be subclassed")


UNDEFINED: t.Final["Undefined"] = Undefined()
__all__ = ["Undefined", "UNDEFINED"]
