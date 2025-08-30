"""Utilities for decoding percent‑encoded query strings and splitting composite keys into bracketed path segments.

This mirrors the semantics of the Node `qs` library:

- Decoding handles both UTF‑8 and Latin‑1 code paths.
- Key splitting keeps bracket groups *balanced* and optionally treats dots as path separators when ``allow_dots=True``.
- Top‑level dot splitting uses a character‑scanner that handles degenerate cases (leading '.' starts a bracket segment; '.[' is skipped; double dots preserve the first; trailing '.' is preserved) and never treats literal percent‑encoded sequences (e.g., '%2E') as split points; only actual '.' characters at depth 0 are split.
"""

import re
import typing as t
from urllib.parse import unquote

from ..enums.charset import Charset
from ..enums.decode_kind import DecodeKind


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

    @classmethod
    def dot_to_bracket_top_level(cls, s: str) -> str:
        """Convert top-level dot segments into bracket groups *after* percent-decoding.

        Notes
        -----
        - In the normal decode path, the key has already been percent-decoded by the upstream
          scanner, so sequences like ``%2E``/``%2e`` are already literal ``.`` when this function
          runs. As a result, with ``allow_dots=True``, any top-level ``.`` will be treated as a
          separator here. This is independent of ``decode_dot_in_keys`` (which only affects how
          encoded dots *inside bracket segments* are normalized later during object folding).
        - If a custom decoder returns raw tokens (i.e., bypasses percent-decoding), ``%2E``/``%2e``
          may still appear here; those percent sequences are preserved verbatim and are **not**
          used as separators.

        Rules
        -----
        - Only dots at depth == 0 split. Dots inside ``[]`` are preserved.
        - Degenerate cases:
          * leading ``.`` starts a bracket segment (``.a`` behaves like ``[a]``)
          * ``.[`` is skipped so ``a.[b]`` behaves like ``a[b]``
          * ``a..b`` preserves the first dot → ``a.[b]``
          * trailing ``.`` is preserved and ignored by the splitter

        Examples
        --------
        'user.email.name' -> 'user[email][name]'
        'a[b].c' -> 'a[b][c]'
        'a[.].c' -> 'a[.][c]'
        'a%2E[b]' -> 'a%2E[b]' (only if a custom decoder left it encoded)
        """
        if "." not in s:
            return s
        sb: t.List[str] = []
        depth = 0
        i = 0
        n = len(s)
        while i < n:
            ch = s[i]
            if ch == "[":
                depth += 1
                sb.append(ch)
                i += 1
            elif ch == "]":
                if depth > 0:
                    depth -= 1
                sb.append(ch)
                i += 1
            elif ch == ".":
                if depth == 0:
                    has_next = i + 1 < n
                    next_ch = s[i + 1] if has_next else "\0"
                    if next_ch == "[":
                        # skip the dot so 'a.[b]' acts like 'a[b]'
                        i += 1
                    elif next_ch == "]":
                        # preserve ambiguous '.]' as a literal to avoid constructing '[]]'
                        sb.append(".")
                        i += 1
                    elif i == 0:
                        # If input starts with '..', preserve the first dot like the 'a..b' case.
                        if has_next and next_ch == ".":
                            sb.append(".")
                            i += 1
                            continue
                        # leading '.' starts a bracket segment: ".a" -> "[a]"
                        start = i + 1
                        j = start
                        while j < n and s[j] != "." and s[j] != "[" and s[j] != "]":
                            j += 1
                        sb.append("[")
                        sb.append(s[start:j])
                        sb.append("]")
                        i = j
                    elif (not has_next) or next_ch == ".":
                        # trailing dot, or first of a double dot
                        sb.append(".")
                        i += 1
                    else:
                        # normal split at top level: convert a.b → a[b]
                        start = i + 1
                        j = start
                        while j < n and s[j] != "." and s[j] != "[" and s[j] != "]":
                            j += 1
                        sb.append("[")
                        sb.append(s[start:j])
                        sb.append("]")
                        i = j
                else:
                    sb.append(".")
                    i += 1
            else:
                # No special handling for percent sequences here; characters are appended as-is.
                # We never split on '%2E' at this stage.
                sb.append(ch)
                i += 1
        return "".join(sb)

    # Precompiled pattern for %XX hex bytes (Latin-1 path fast path)
    HEX2_PATTERN: t.Pattern[str] = re.compile(r"%([0-9A-Fa-f]{2})")

    @classmethod
    def unescape(cls, string: str) -> str:
        """Emulate legacy JavaScript unescape behavior.

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
        # Fast path: nothing to unescape
        if "%" not in string:
            return string

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
        kind: DecodeKind = DecodeKind.VALUE,  # pylint: disable=unused-argument
    ) -> t.Optional[str]:
        """Decode a URL‑encoded scalar.

        Notes
        -----
        The `kind` parameter is accepted for API compatibility but is currently
        ignored; keys and values are decoded identically. It may be removed in
        a future major release.

        Behavior:
        - Replace ``+`` with a literal space *before* decoding.
        - If ``charset`` is :data:`~qs_codec.enums.charset.Charset.LATIN1`, decode only ``%XX`` byte sequences (no ``%uXXXX``). ``%uXXXX`` sequences are left as‑is to mimic older browser/JS behavior.
        - Otherwise (UTF‑8), defer to :func:`urllib.parse.unquote`.
        - Keys and values are decoded identically; whether a literal ``.`` acts as a key separator is decided later by the key‑splitting logic.

        Returns
        -------
        Optional[str]
            ``None`` when the input is ``None``.
        """
        if string is None:
            return None

        # Replace '+' with ' ' only if present to avoid allocation.
        string_without_plus: str = string.replace("+", " ") if "+" in string else string

        if charset == Charset.LATIN1:
            # Only process %XX hex escape sequences for Latin-1 (no %uXXXX expansion here).
            s = string_without_plus
            if "%" not in s:
                return s
            _int, _chr = int, chr
            return cls.HEX2_PATTERN.sub(lambda m: _chr(_int(m.group(1), 16)), s)

        s = string_without_plus
        return s if "%" not in s else unquote(s)

    @classmethod
    def split_key_into_segments(
        cls,
        original_key: str,
        allow_dots: bool,
        max_depth: int,
        strict_depth: bool,
    ) -> t.List[str]:
        """Split a composite key into *balanced* bracket segments.

        - If ``allow_dots`` is True, convert **top‑level** dots to bracket groups using a character‑scanner (``a.b[c]`` → ``a[b][c]``), preserving dots inside brackets and degenerate cases.
        - The *parent* (non‑bracket) prefix becomes the first segment, e.g. ``"a[b][c]"`` → ``["a", "[b]", "[c]"]``.
        - Bracket groups are *balanced* using a counter so nested brackets within a single group (e.g. ``"[with[inner]]"``) are treated as one segment.
        - When ``max_depth <= 0``, no splitting occurs; the key is returned as a single segment (qs semantics).
        - If there are more groups beyond ``max_depth`` and ``strict_depth`` is True, an ``IndexError`` is raised. Otherwise, the remainder is added as one final segment (again mirroring qs).
        - Unterminated '[': the remainder after the first unmatched '[' is captured as a single synthetic bracket segment.

        Examples
        --------
        max_depth=2: "a[b][c][d]" -> ["a", "[b]", "[c]", "[[d]]"]
        unterminated: "a[b" -> ["a", "[[b]"]

        This runs in O(n) time over the key string.
        """
        if max_depth <= 0:
            return [original_key]

        key: str = cls.dot_to_bracket_top_level(original_key) if allow_dots else original_key

        segments: t.List[str] = []

        first: int = key.find("[")
        parent: str = key[:first] if first >= 0 else key
        # Capture the non-bracket parent prefix (may be empty).
        if parent:
            segments.append(parent)

        n: int = len(key)
        open_idx: int = first
        depth: int = 0

        unterminated = False
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
                unterminated = True  # unterminated group; stop collecting; remainder handled below
                break

            # Append the full balanced group, including the surrounding brackets.
            segments.append(key[open_idx : close + 1])  # includes the surrounding [ ]
            depth += 1
            open_idx = key.find("[", close + 1)

        if open_idx >= 0:
            # We only want to raise for true depth overflow under strict_depth,
            # not for unterminated bracket groups.
            depth_overflow = (depth >= max_depth) and not unterminated
            if strict_depth and depth_overflow:
                raise IndexError(f"Input depth exceeded depth option of {max_depth} and strict_depth is True")
            # Stash the remainder as a single segment (qs parity)
            segments.append("[" + key[open_idx:] + "]")

        return segments
