"""Internal undefined sentinel used while building codec data structures.

``Undefined`` represents a missing value that should be omitted, similar to
JavaScript's ``undefined``. It is distinct from ``None``, which represents an
explicit null value.

The sentinel is identity-based: every construction returns the same instance,
allowing reliable ``is`` comparisons throughout the codec internals.
"""

import threading
import typing as t

__all__ = ()


class Undefined:
    """Singleton sentinel representing a value that should be omitted.

    This is not equivalent to ``None``. The encoder and helper utilities use it
    temporarily to mark absent entries, then remove those entries before
    returning public results.
    """

    __slots__ = ()
    _lock: t.ClassVar[threading.Lock] = threading.Lock()
    _instance: t.ClassVar[t.Optional["Undefined"]] = None

    def __new__(cls):
        """Return the singleton instance.

        Repeated construction returns the same object reference so identity
        checks remain stable.
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
        """Preserve singleton identity when shallow-copied."""
        return self

    def __deepcopy__(self, memo):  # pragma: no cover - trivial
        """Preserve singleton identity when deep-copied."""
        return self

    def __reduce__(self):  # pragma: no cover - trivial
        """Reconstruct through the singleton constructor when unpickled."""
        return Undefined, ()

    def __init_subclass__(cls, **kwargs):  # pragma: no cover - defensive
        """Prevent subclassing to preserve singleton identity."""
        raise TypeError("Undefined cannot be subclassed")


UNDEFINED: t.Final["Undefined"] = Undefined()
