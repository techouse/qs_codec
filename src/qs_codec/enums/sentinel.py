"""This module defines the Sentinel enum, which contains all available sentinel values."""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class _SentinelDataMixin:
    """Sentinel data mixin."""

    raw: str
    encoded: str


class Sentinel(_SentinelDataMixin, Enum):
    """An enum of all available sentinel values."""

    ISO = r"&#10003;", r"utf8=%26%2310003%3B"
    """This is what browsers will submit when the ``✓`` character occurs in an ``application/x-www-form-urlencoded``
    body and the encoding of the page containing the form is ``iso-8859-1``, or when the submitted form has an
    ``accept-charset`` attribute of ``iso-8859-1``. Presumably also with other charsets that do not contain the ``✓``
    character, such as ``us-ascii``."""

    CHARSET = r"✓", r"utf8=%E2%9C%93"
    """These are the percent-encoded ``utf-8`` octets representing a checkmark, indicating that the request actually is
    ``utf-8`` encoded."""
