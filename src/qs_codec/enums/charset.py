"""Charset enum module."""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class CharsetDataMixin:
    """Character set data mixin."""

    encoding: str


class Charset(CharsetDataMixin, Enum):
    """Character set."""

    UTF8 = "utf-8"
    LATIN1 = "iso-8859-1"
