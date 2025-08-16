"""Sentinel values and their percent-encoded forms.

Browsers sometimes include an ``utf8=…`` “sentinel” in
``application/x-www-form-urlencoded`` submissions to signal the character
encoding that was used. This module exposes those sentinels as an ``Enum``,
where each member carries both the raw token (what the page emits) and the
fully URL-encoded fragment (what appears on the wire).
"""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class _SentinelDataMixin:
    """Common data carried by each sentinel.

    Attributes:
        raw: The unencoded token browsers start with. For example, the HTML
            entity string ``"&#10003;"`` or the literal check mark ``"✓"``.
        encoded: The full ``key=value`` fragment after URL-encoding, e.g.
            ``"utf8=%26%2310003%3B"`` or ``"utf8=%E2%9C%93"``.
    """

    raw: str
    encoded: str


class Sentinel(_SentinelDataMixin, Enum):
    """All supported ``utf8`` sentinels.

    Each enum member provides:
        - ``raw``: the source token a browser starts with, and
        - ``encoded``: the final, percent-encoded ``utf8=…`` fragment.
    """

    ISO = r"&#10003;", r"utf8=%26%2310003%3B"
    """HTML‑entity sentinel used by non‑UTF‑8 submissions.

    When a check mark (✓) appears but the page/form encoding is ``iso-8859-1``
    (or another charset that lacks ✓), browsers first HTML‑entity‑escape it as
    ``"&#10003;"`` and then URL‑encode it, producing ``utf8=%26%2310003%3B``.
    """

    CHARSET = r"✓", r"utf8=%E2%9C%93"
    """UTF‑8 sentinel indicating the request is UTF‑8 encoded.

    This is the percent‑encoded UTF‑8 sequence for ✓, yielding the fragment
    ``utf8=%E2%9C%93``.
    """
