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

    @classmethod
    def escape(
        cls,
        string: str,
        format: t.Optional[Format] = Format.RFC3986,
    ) -> str:
        """A Python representation the deprecated JavaScript escape function.

        https://developer.mozilla.org/en-US/docs/web/javascript/reference/global_objects/escape
        """
        # Build a set of "safe" code points.
        safe: t.Set[int] = set(range(0x30, 0x3A)) | set(range(0x41, 0x5B)) | set(range(0x61, 0x7B))
        safe |= {0x40, 0x2A, 0x5F, 0x2D, 0x2B, 0x2E, 0x2F}  # @, *, _, -, +, ., /

        # For RFC1738, add the ASCII codes for ( and )
        if format == Format.RFC1738:
            safe |= {0x28, 0x29}

        buffer: t.List[str] = []

        i: int
        char: str
        for i, char in enumerate(string):
            # Use code_unit_at if it does more than ord()
            c: int = code_unit_at(string, i)
            if c in safe:
                buffer.append(char)
            elif c < 256:
                buffer.append(f"%{c:02X}")
            else:
                buffer.append(f"%u{c:04X}")
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

        string: str
        if isinstance(value, bytes):
            string = value.decode("utf-8")
        elif isinstance(value, bool):
            string = str(value).lower()
        elif isinstance(value, str):
            string = value
        else:
            string = str(value)

        if value == "":
            return ""

        if charset == Charset.LATIN1:
            return re.sub(
                r"%u[0-9a-f]{4}",
                lambda match: f"%26%23{int(match.group(0)[2:], 16)}%3B",
                cls.escape(cls.to_surrogates(string), format),
                flags=re.IGNORECASE,
            )

        buffer: t.List[str] = []

        i: int
        for i, _ in enumerate(string):
            c: int = code_unit_at(string, i)

            if (
                c == 0x2D  # -
                or c == 0x2E  # .
                or c == 0x5F  # _
                or c == 0x7E  # ~
                or (0x30 <= c <= 0x39)  # 0-9
                or (0x41 <= c <= 0x5A)  # a-z
                or (0x61 <= c <= 0x7A)  # A-Z
                or (format == Format.RFC1738 and (c == 0x28 or c == 0x29))  # ( )
            ):
                buffer.append(string[i])
                continue
            elif c < 0x80:  # ASCII
                buffer.extend([cls.HEX_TABLE[c]])
                continue
            elif c < 0x800:  # 2 bytes
                buffer.extend(
                    [
                        cls.HEX_TABLE[0xC0 | (c >> 6)],
                        cls.HEX_TABLE[0x80 | (c & 0x3F)],
                    ],
                )
                continue
            elif c < 0xD800 or c >= 0xE000:  # 3 bytes
                buffer.extend(
                    [
                        cls.HEX_TABLE[0xE0 | (c >> 12)],
                        cls.HEX_TABLE[0x80 | ((c >> 6) & 0x3F)],
                        cls.HEX_TABLE[0x80 | (c & 0x3F)],
                    ],
                )
                continue
            else:
                i += 1
                c = 0x10000 + (((c & 0x3FF) << 10) | (code_unit_at(string, i) & 0x3FF))
                buffer.extend(
                    [
                        cls.HEX_TABLE[0xF0 | (c >> 18)],
                        cls.HEX_TABLE[0x80 | ((c >> 12) & 0x3F)],
                        cls.HEX_TABLE[0x80 | ((c >> 6) & 0x3F)],
                        cls.HEX_TABLE[0x80 | (c & 0x3F)],
                    ],
                )

        return "".join(buffer)

    @staticmethod
    def to_surrogates(string: str) -> str:
        """Convert characters in the string that are outside the BMP (i.e. code points > 0xFFFF) into their corresponding surrogate pair."""
        result: t.List[str] = []

        ch: str
        for ch in string:
            cp: int = ord(ch)
            if cp > 0xFFFF:
                # Convert to surrogate pair.
                cp -= 0x10000
                high: int = 0xD800 + (cp >> 10)
                low: int = 0xDC00 + (cp & 0x3FF)
                result.append(chr(high))
                result.append(chr(low))
            else:
                result.append(ch)
        return "".join(result)

    @staticmethod
    def serialize_date(dt: datetime) -> str:
        """Serialize a `datetime` object to an ISO 8601 string."""
        return dt.isoformat()
