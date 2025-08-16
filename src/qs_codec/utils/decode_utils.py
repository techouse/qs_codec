"""Utilities for decoding percent‑encoded query strings and splitting composite keys into bracketed path segments.

This mirrors the semantics of the Node `qs` library:

- Decoding handles both UTF‑8 and Latin‑1 code paths.
- Key splitting keeps bracket groups *balanced* and optionally treats dots as path separators when ``allow_dots=True``.
"""

import re
import typing as t
from urllib.parse import unquote

from ..enums.charset import Charset


class DecodeUtils:
    """Decode helpers compiled into a single, importable namespace.

    All methods are classmethods so they are easy to stub/patch in tests, and
    the compiled regular expressions are created once per interpreter session.
    """

    # Matches either a 16‑bit JavaScript-style %uXXXX sequence or a single‑byte
    # %XX sequence. Used by `unescape` to emulate legacy browser behavior.
    UNESCAPE_PATTERN: t.Pattern[str] = re.compile(
        r"%u(?P<unicode>[0-9A-Fa-f]{4})|%(?P<hex>[0-9A-Fa-f]{2})",
        re.IGNORECASE,
    )

    # When `allow_dots=True`, convert ".foo" segments into "[foo]" so that
    # "a.b[c]" becomes "a[b][c]" before bracket parsing.
    DOT_TO_BRACKET: t.Pattern[str] = re.compile(r"\.([^.\[]+)")

    @classmethod
    def unescape(cls, string: str) -> str:
        """
        Emulate legacy JavaScript unescape behavior.

        Replaces both ``%XX`` and ``%uXXXX`` escape sequences with the
        corresponding code points. This function is intentionally permissive
        and does not validate UTF‑8; it is used to model historical behavior
        in Latin‑1 mode.

        Examples
        --------
        >>> DecodeUtils.unescape("%u0041%20%42")
        'A B'
        >>> DecodeUtils.unescape("%7E")
        '~'
        """

        def replacer(match: t.Match[str]) -> str:
            if (unicode_val := match.group("unicode")) is not None:
                return chr(int(unicode_val, 16))
            elif (hex_val := match.group("hex")) is not None:
                return chr(int(hex_val, 16))
            return match.group(0)

        return cls.UNESCAPE_PATTERN.sub(replacer, string)

    @classmethod
    def decode(
        cls,
        string: t.Optional[str],
        charset: t.Optional[Charset] = Charset.UTF8,
    ) -> t.Optional[str]:
        """Decode a URL‑encoded scalar.

        Behavior:
        - Replace ``+`` with a literal space *before* decoding.
        - If ``charset`` is :data:`~qs_codec.enums.charset.Charset.LATIN1`,
        replace only ``%XX`` byte sequences using :meth:`DecodeUtils.unescape`.
        ``%uXXXX`` sequences are left as‑is here to mimic older browser/JS behavior.
        - Otherwise (UTF‑8), defer to :func:`urllib.parse.unquote`.

        Returns
        -------
        Optional[str]
            ``None`` when the input is ``None``.
        """
        if string is None:
            return None

        # Replace '+' with ' ' before processing.
        string_without_plus: str = string.replace("+", " ")

        if charset == Charset.LATIN1:
            # Only process hex escape sequences for Latin1.
            return re.sub(
                r"%[0-9A-Fa-f]{2}",
                lambda match: cls.unescape(match.group(0)),
                string_without_plus,
            )

        return unquote(string_without_plus)

    @classmethod
    def split_key_into_segments(
        cls,
        original_key: str,
        allow_dots: bool,
        max_depth: int,
        strict_depth: bool,
    ) -> t.List[str]:
        """
        Split a composite key into *balanced* bracket segments.

        - If ``allow_dots`` is True, convert dots to bracket groups first (``a.b[c]`` → ``a[b][c]``) while leaving existing brackets intact.
        - The *parent* (non‑bracket) prefix becomes the first segment, e.g. ``"a[b][c]"`` → ``["a", "[b]", "[c]"]``.
        - Bracket groups are *balanced* using a counter so nested brackets within a single group (e.g. ``"[with[inner]]"``) are treated as one segment.
        - When ``max_depth <= 0``, no splitting occurs; the key is returned as a single segment (qs semantics).
        - If there are more groups beyond ``max_depth`` and ``strict_depth`` is True, an ``IndexError`` is raised. Otherwise, the remainder is added as one final segment (again mirroring qs).

        This runs in O(n) time over the key string.
        """
        key: str = cls.DOT_TO_BRACKET.sub(r"[\1]", original_key) if allow_dots else original_key

        if max_depth <= 0:
            return [key]

        segments: t.List[str] = []

        first: int = key.find("[")
        parent: str = key[:first] if first >= 0 else key
        # Capture the non-bracket parent prefix (may be empty).
        if parent:
            segments.append(parent)

        n: int = len(key)
        open_idx: int = first
        depth: int = 0

        while open_idx >= 0 and depth < max_depth:
            level = 1
            i = open_idx + 1
            close = -1

            # Balance nested '[' and ']' inside the same group,
            # so "[withbracket[]]" is treated as *one* segment.
            while i < n:
                ch = key[i]
                if ch == "[":
                    level += 1
                elif ch == "]":
                    level -= 1
                    if level == 0:
                        close = i
                        break
                i += 1

            if close < 0:
                break  # unterminated group; stop collecting

            # Append the full balanced group, including the surrounding brackets.
            segments.append(key[open_idx : close + 1])  # includes the surrounding [ ]
            depth += 1
            open_idx = key.find("[", close + 1)

        if open_idx >= 0:
            if strict_depth:
                raise IndexError(f"Input depth exceeded depth option of {max_depth} and strict_depth is True")
            # Stash the remainder as a single segment (qs behavior)
            segments.append("[" + key[open_idx:] + "]")

        return segments
