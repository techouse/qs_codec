"""Decode utility methods used by the library."""

import re
import typing as t
from urllib.parse import unquote

from ..enums.charset import Charset


class DecodeUtils:
    """A collection of decode utility methods used by the library."""

    # Compile a pattern that matches either a %uXXXX sequence or a %XX sequence.
    UNESCAPE_PATTERN: t.Pattern[str] = re.compile(
        r"%u(?P<unicode>[0-9A-Fa-f]{4})|%(?P<hex>[0-9A-Fa-f]{2})",
        re.IGNORECASE,
    )

    # Compile a pattern that matches a dot followed by any characters except dots or brackets.
    DOT_TO_BRACKET: t.Pattern[str] = re.compile(r"\.([^.\[]+)")

    @classmethod
    def unescape(cls, string: str) -> str:
        """
        A Python representation of the deprecated JavaScript unescape function.

        This method replaces both "%XX" and "%uXXXX" escape sequences with
        their corresponding characters.

        Example:
            unescape("%u0041%20%42") -> "A B"
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
        """Decode a URL-encoded string.

        For non-UTF8 charsets (specifically Charset.LATIN1), it replaces plus
        signs with spaces and applies a custom unescape for percent-encoded hex
        sequences. Otherwise, it defers to urllib.parse.unquote.
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

    _DOT_TO_BRACKET = re.compile(r"\.([^.\[]+)")

    @classmethod
    def split_key_into_segments(
        cls,
        original_key: str,
        allow_dots: bool,
        max_depth: int,
        strict_depth: bool,
    ) -> t.List[str]:
        """
        Convert 'a.b[c][d]' -> ['a', '[b]', '[c]', '[d]'] with *balanced* bracket groups.

        Depth==0: do not split; never throw even if strict_depth=True (qs semantics).
        """
        key: str = cls.DOT_TO_BRACKET.sub(r"[\1]", original_key) if allow_dots else original_key

        if max_depth <= 0:
            return [key]

        segments: t.List[str] = []

        first: int = key.find("[")
        parent: str = key[:first] if first >= 0 else key
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

            segments.append(key[open_idx : close + 1])  # includes the surrounding [ ]
            depth += 1
            open_idx = key.find("[", close + 1)

        if open_idx >= 0:
            if strict_depth:
                raise IndexError(f"Input depth exceeded depth option of {max_depth} and strict_depth is True")
            # Stash the remainder as a single segment (qs behavior)
            segments.append("[" + key[open_idx:] + "]")

        return segments
