"""Defines the StructuredKeyScan dataclass for representing the results of scanning for structured keys in query strings."""

import typing as t
from dataclasses import dataclass


@dataclass(frozen=True)
class StructuredKeyScan:
    """Represents the results of scanning for structured keys in query strings."""

    has_any_structured_syntax: bool
    structured_roots: t.FrozenSet[str]
    structured_keys: t.FrozenSet[str]

    @classmethod
    def empty(cls) -> "StructuredKeyScan":
        """Factory for an empty scan result when no structured syntax is detected."""
        return cls(has_any_structured_syntax=False, structured_roots=frozenset(), structured_keys=frozenset())
