"""URI component formatting strategies.

This module defines the :class:`Format` enum that specifies how space and other
characters are normalized in a *percent-encoded* query string after encoding.
Two common profiles are provided:

- :attr:`Format.RFC1738` – replaces "%20" with "+" in the final output.
- :attr:`Format.RFC3986` – leaves "%20" as-is (default on the web today).

Use the functions on :class:`Formatter` if you need direct access to the
formatting operations.
"""

import typing as t
from dataclasses import dataclass
from enum import Enum


class Formatter:
    """Formatting helpers used by :class:`Format`.

    These functions expect **already percent-encoded** input and adjust only
    the representation of spaces (and related normalization) according to the
    selected RFC profile. They do not perform percent-encoding themselves.
    """

    @staticmethod
    def rfc1738(value: str) -> str:
        """Apply RFC 1738 post-processing.

        Replaces occurrences of ``"%20"`` with ``"+"`` to match the historical
        ``application/x-www-form-urlencoded`` semantics described in RFC 1738.
        The input is assumed to already be percent-encoded; only the space
        representation is changed.
        """
        return value.replace("%20", "+")

    @staticmethod
    def rfc3986(value: str) -> str:
        """Apply RFC 3986 post-processing.

        Returns the input unchanged (spaces remain encoded as ``"%20"``). This is
        the modern, conservative representation used by most tooling today.
        """
        return value


@dataclass(frozen=True)
class _FormatDataMixin:
    """Metadata carried by each :class:`Format` member.

    Attributes
    ----------
    format_name:
        Human-readable identifier (e.g. ``"RFC1738"``).
    formatter:
        Callable that applies the profile-specific post-processing to an
        already percent-encoded string.
    """

    format_name: str
    formatter: t.Callable[[str], str]


class Format(_FormatDataMixin, Enum):
    """Supported URI component formatting profiles.

    Each enum value packs a ``(format_name, formatter)`` tuple. After raw
    percent-encoding is performed by the encoder, the selected profile's
    ``formatter`` is called to adjust the final textual representation (e.g.,
    mapping ``"%20"`` to ``"+"`` for RFC 1738).
    """

    RFC1738 = "RFC1738", Formatter.rfc1738
    """`RFC 1738 <https://datatracker.ietf.org/doc/html/rfc1738>`_."""

    RFC3986 = "RFC3986", Formatter.rfc3986
    """`RFC 3986 <https://datatracker.ietf.org/doc/html/rfc3986>`_."""
