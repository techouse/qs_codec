"""Charset sentinel values and their percent-encoded forms.

Browsers sometimes include an ``utf8=…`` sentinel in
``application/x-www-form-urlencoded`` submissions to signal the character
encoding that was used. This module exposes those sentinels as an enum whose
members carry both the raw token emitted by the page and the fully URL-encoded
fragment that appears on the wire.
"""

from dataclasses import dataclass
from enum import Enum

__all__ = ("Sentinel",)


@dataclass(frozen=True)
class _SentinelDataMixin:
    """Common data carried by each charset sentinel.

    Attributes:
        raw: The unencoded token browsers start with, such as the HTML entity
            string ``"&#10003;"`` or the literal check mark ``"✓"``.
        encoded: The full URL-encoded ``key=value`` fragment, such as
            ``"utf8=%26%2310003%3B"`` or ``"utf8=%E2%9C%93"``.
    """

    raw: str
    encoded: str


class Sentinel(_SentinelDataMixin, Enum):
    """Charset sentinels recognized and emitted by the codec.

    Each member provides the source token through ``raw`` and the final
    percent-encoded ``utf8=…`` fragment through ``encoded``.
    """

    ISO = r"&#10003;", r"utf8=%26%2310003%3B"
    """HTML-entity sentinel used by non-UTF-8 submissions.

    When a check mark (✓) appears but the form encoding is ``iso-8859-1`` or
    another charset that lacks it, browsers HTML-entity-escape the character
    and then URL-encode it, producing ``utf8=%26%2310003%3B``.
    """

    CHARSET = r"✓", r"utf8=%E2%9C%93"
    """UTF-8 sentinel indicating that the request is UTF-8 encoded.

    The encoded form contains the percent-encoded UTF-8 sequence for ✓.
    """
