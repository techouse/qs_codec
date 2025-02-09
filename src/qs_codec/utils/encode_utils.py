"""A collection of encode utility methods used by the library."""

import re
import typing as t
from datetime import datetime
from decimal import Decimal
from enum import Enum

from ..enums.charset import Charset
from ..enums.format import Format
from .str_utils import code_unit_at


class EncodeUtils:
    """A collection of encode utility methods used by the library."""

    HEX_TABLE: t.Tuple[str, ...] = tuple(f"%{i:02X}" for i in range(256))
    """Hex table of all 256 characters"""

    SAFE_ALPHA: t.Set[int] = set(range(0x30, 0x3A)) | set(range(0x41, 0x5B)) | set(range(0x61, 0x7B))
    """0-9, A-Z, a-z"""

    SAFE_POINTS: t.Set[int] = SAFE_ALPHA | {0x40, 0x2A, 0x5F, 0x2D, 0x2B, 0x2E, 0x2F}
    """0-9, A-Z, a-z, @, *, _, -, +, ., /"""

    RFC1738_SAFE_POINTS: t.Set[int] = SAFE_POINTS | {0x28, 0x29}
    """0-9, A-Z, a-z, @, *, _, -, +, ., /, (, )"""

    SAFE_CHARS: t.Set[int] = SAFE_ALPHA | {0x2D, 0x2E, 0x5F, 0x7E}
    """0-9, A-Z, a-z, -, ., _, ~"""

    RFC1738_SAFE_CHARS = SAFE_CHARS | {0x28, 0x29}
    """0-9, A-Z, a-z, -, ., _, ~, (, )"""

    @classmethod
    def escape(
        cls,
        string: str,
        format: t.Optional[Format] = Format.RFC3986,
    ) -> str:
        """A Python representation the deprecated JavaScript escape function.

        https://developer.mozilla.org/en-US/docs/web/javascript/reference/global_objects/escape
        """
        # Convert any non-BMP character into its surrogate pair representation.
        string = cls._to_surrogates(string)

        safe_points: t.Set[int] = cls.RFC1738_SAFE_POINTS if format == Format.RFC1738 else cls.SAFE_POINTS

        buffer: t.List[str] = []

        i: int = 0
        while i < len(string):
            c: int = code_unit_at(string, i)
            # If we detect a high surrogate and there is a following low surrogate, encode both.
            if 0xD800 <= c <= 0xDBFF and i + 1 < len(string):
                next_c: int = code_unit_at(string, i + 1)
                if 0xDC00 <= next_c <= 0xDFFF:
                    buffer.append(f"%u{c:04X}")
                    buffer.append(f"%u{next_c:04X}")
                    i += 2
                    continue

            if c in safe_points:
                buffer.append(string[i])
            elif c < 256:
                buffer.append(f"%{c:02X}")
            else:
                buffer.append(f"%u{c:04X}")
            i += 1

        return "".join(buffer)

    @classmethod
    def encode(
        cls,
        value: t.Any,
        charset: t.Optional[Charset] = Charset.UTF8,
        format: t.Optional[Format] = Format.RFC3986,
    ) -> str:
        """Encode a value to a URL-encoded string."""
        if value is None or not isinstance(value, (int, float, Decimal, Enum, str, bool, bytes)):
            return ""

        string: str = cls._convert_value_to_string(value)

        if not string:
            return ""

        if charset == Charset.LATIN1:
            return re.sub(
                r"%u[0-9a-f]{4}",
                lambda match: f"%26%23{int(match.group(0)[2:], 16)}%3B",
                cls.escape(cls._to_surrogates(string), format),
                flags=re.IGNORECASE,
            )

        return cls._encode_string(string, format)

    @staticmethod
    def _convert_value_to_string(value: t.Any) -> str:
        """Convert the value to a string based on its type."""
        if isinstance(value, bytes):
            return value.decode("utf-8")
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, str):
            return value
        else:
            return str(value)

    @classmethod
    def _encode_string(cls, string: str, format: t.Optional[Format]) -> str:
        """Encode the string to a URL-encoded format."""
        buffer: t.List[str] = []

        i: int
        for i, _ in enumerate(string):
            c: int = code_unit_at(string, i)

            if cls._is_safe_char(c, format):
                buffer.append(string[i])
            else:
                buffer.extend(cls._encode_char(string, i, c))

        return "".join(buffer)

    @classmethod
    def _is_safe_char(cls, c: int, format: t.Optional[Format]) -> bool:
        """Check if the character (given by its code point) is safe to be included in the URL without encoding."""
        return c in cls.RFC1738_SAFE_CHARS if format == Format.RFC1738 else c in cls.SAFE_CHARS

    @classmethod
    def _encode_char(cls, string: str, i: int, c: int) -> t.List[str]:
        """Encode a single character to its URL-encoded representation."""
        if c < 0x80:  # ASCII
            return [cls.HEX_TABLE[c]]
        elif c < 0x800:  # 2 bytes
            return [
                cls.HEX_TABLE[0xC0 | (c >> 6)],
                cls.HEX_TABLE[0x80 | (c & 0x3F)],
            ]
        elif c < 0xD800 or c >= 0xE000:  # 3 bytes
            return [
                cls.HEX_TABLE[0xE0 | (c >> 12)],
                cls.HEX_TABLE[0x80 | ((c >> 6) & 0x3F)],
                cls.HEX_TABLE[0x80 | (c & 0x3F)],
            ]
        else:
            return cls._encode_surrogate_pair(string, i, c)

    @classmethod
    def _encode_surrogate_pair(cls, string: str, i: int, c: int) -> t.List[str]:
        """Encode a surrogate pair character to its URL-encoded representation."""
        buffer: t.List[str] = []
        c = 0x10000 + (((c & 0x3FF) << 10) | (code_unit_at(string, i + 1) & 0x3FF))
        buffer.extend(
            [
                cls.HEX_TABLE[0xF0 | (c >> 18)],
                cls.HEX_TABLE[0x80 | ((c >> 12) & 0x3F)],
                cls.HEX_TABLE[0x80 | ((c >> 6) & 0x3F)],
                cls.HEX_TABLE[0x80 | (c & 0x3F)],
            ],
        )
        return buffer

    @staticmethod
    def _to_surrogates(string: str) -> str:
        """Convert characters in the string that are outside the BMP (i.e. code points > 0xFFFF) into their corresponding surrogate pair."""
        buffer: t.List[str] = []

        ch: str
        for ch in string:
            cp: int = ord(ch)
            if cp > 0xFFFF:
                # Convert to surrogate pair.
                cp -= 0x10000
                high: int = 0xD800 + (cp >> 10)
                low: int = 0xDC00 + (cp & 0x3FF)
                buffer.append(chr(high))
                buffer.append(chr(low))
            else:
                buffer.append(ch)
        return "".join(buffer)

    @staticmethod
    def serialize_date(dt: datetime) -> str:
        """Serialize a `datetime` object to an ISO 8601 string."""
        return dt.isoformat()
