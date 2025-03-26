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
