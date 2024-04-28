"""An enum of all supported URI component encoding formats."""

import typing as t
from dataclasses import dataclass
from enum import Enum


class Formatter:
    """A class for formatting URI components."""

    @staticmethod
    def rfc1738(value: str) -> str:
        """Format a string according to RFC 1738."""
        return value.replace("%20", "+")

    @staticmethod
    def rfc3986(value: str) -> str:
        """Format a string according to RFC 3986."""
        return value


@dataclass(frozen=True)
class _FormatDataMixin:
    """Format data mixin."""

    format_name: str
    formatter: t.Callable[[str], str]


class Format(_FormatDataMixin, Enum):
    """An enum of all supported URI component encoding formats."""

    RFC1738 = "RFC1738", Formatter.rfc1738
    """Format a string according to RFC 1738."""

    RFC3986 = "RFC3986", Formatter.rfc3986
    """Format a string according to RFC 3986."""
