"""Decode utility methods used by the library."""

import re
import typing as t
from urllib.parse import unquote

from ..enums.charset import Charset
from .str_utils import code_unit_at


class DecodeUtils:
    """A collection of decode utility methods used by the library."""

    @classmethod
    def unescape(cls, string: str) -> str:
        """A Python representation of the deprecated JavaScript unescape function.

        https://developer.mozilla.org/en-US/docs/web/javascript/reference/global_objects/unescape
        """
        buffer: t.List[str] = []

        i: int = 0
        while i < len(string):
            c: int = code_unit_at(string, i)

            if c == 0x25:  # '%'
                if string[i + 1] == "u":
                    buffer.append(cls._unescape_unicode(string, i))
                    i += 6
                else:
                    buffer.append(cls._unescape_hex(string, i))
                    i += 3
            else:
                buffer.append(string[i])
                i += 1

        return "".join(buffer)

    @staticmethod
    def _unescape_unicode(string: str, i: int) -> str:
        """Unescape a unicode escape sequence."""
        return chr(int(string[i + 2 : i + 6], 16))

    @staticmethod
    def _unescape_hex(string: str, i: int) -> str:
        """Unescape a hex escape sequence."""
        return chr(int(string[i + 1 : i + 3], 16))

    @classmethod
    def decode(
        cls,
        string: t.Optional[str],
        charset: t.Optional[Charset] = Charset.UTF8,
    ) -> t.Optional[str]:
        """Decode a URL-encoded string."""
        if string is None:
            return None

        string_without_plus: str = string.replace("+", " ")

        if charset == Charset.LATIN1:
            return re.sub(
                r"%[0-9a-f]{2}",
                lambda match: cls.unescape(match.group(0)),
                string_without_plus,
                flags=re.IGNORECASE,
            )

        return unquote(string_without_plus)
