"""Definitions for character set handling.

This module exposes :class:`Charset`, an enum of supported character sets used by the
encoder/decoder. Each member’s value is the canonical Python codec name (e.g. ``"utf-8"``)
that can be passed directly to ``str.encode`` / ``bytes.decode``.
"""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class _CharsetDataMixin:
    """Lightweight mixin that stores the canonical codec name.

    Attributes
    ----------
    encoding : str
        Canonical Python codec identifier (e.g., ``"utf-8"`` or ``"iso-8859-1"``).
    """

    encoding: str


class Charset(_CharsetDataMixin, Enum):
    """Supported character sets for query-string processing.

    Each enum member’s value is the codec string understood by Python’s encoding APIs.
    Prefer accessing :attr:`encoding` instead of hard-coding literals.
    """

    UTF8 = "utf-8"
    """UTF-8 character encoding."""

    LATIN1 = "iso-8859-1"
    """ISO-8859-1 (Latin-1) character encoding."""
