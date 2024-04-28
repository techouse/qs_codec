"""Charset enum module."""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class _CharsetDataMixin:
    """Character set data mixin."""

    encoding: str


class Charset(_CharsetDataMixin, Enum):
    """Character set."""

    UTF8 = "utf-8"
    """UTF-8 character encoding."""

    LATIN1 = "iso-8859-1"
    """ISO-8859-1 (Latin-1) character encoding."""
