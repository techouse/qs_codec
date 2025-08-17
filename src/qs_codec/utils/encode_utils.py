"""A collection of encode utility methods used by the library."""

import re
import typing as t
from datetime import datetime
from decimal import Decimal
from enum import Enum

from ..enums.charset import Charset
from ..enums.format import Format


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

    RFC1738_SAFE_CHARS: t.Set[int] = SAFE_CHARS | {0x28, 0x29}
    """0-9, A-Z, a-z, -, ., _, ~, (, )"""

    _RE_UXXXX = re.compile(r"%u([0-9a-fA-F]{4})")

    @classmethod
    def escape(
        cls,
        string: str,
        format: t.Optional[Format] = Format.RFC3986,
    ) -> str:
        """Emulate the legacy JavaScript escaping behavior.

        This function operates on UTF‑16 *code units* to emulate JavaScript's legacy `%uXXXX` behavior. Non‑BMP code
        points are first expanded into surrogate pairs via `_to_surrogates`, then each code unit is processed.

        - Safe set: when `format == Format.RFC1738`, the characters `(` and `)` are additionally treated as safe. Otherwise, the RFC3986 safe set is used.
        - ASCII characters in the safe set are emitted unchanged.
        - Code units &lt; 256 are emitted as `%XX`.
        - Other code units are emitted as `%uXXXX`.

        Reference: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/escape
        """
        # Convert any non-BMP character into its surrogate pair representation.
        string = cls._to_surrogates(string)

        safe_points: t.Set[int] = cls.RFC1738_SAFE_POINTS if format == Format.RFC1738 else cls.SAFE_POINTS

        buffer: t.List[str] = []

        i: int = 0
        n: int = len(string)
        while i < n:
            c: int = ord(string[i])
            # If we detect a high surrogate and there is a following low surrogate, encode both.
            if 0xD800 <= c <= 0xDBFF and (i + 1) < n:
                next_c: int = ord(string[i + 1])
                if 0xDC00 <= next_c <= 0xDFFF:
                    buffer.append(f"%u{c:04X}")
                    buffer.append(f"%u{next_c:04X}")
                    i += 2
                    continue

            if c in safe_points:
                buffer.append(string[i])
            elif c < 256:
                buffer.append(cls.HEX_TABLE[c])
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
        """Encode a scalar value to a URL‑encoded string.

        - Accepts numbers, `Decimal`, `Enum`, `str`, `bool`, and `bytes`. Any other type (including `None`) yields an empty string, matching the Node `qs` behavior.
        - For `Charset.LATIN1`, the output mirrors the JS `%uXXXX` + numeric entity trick so the result can be safely transported as latin‑1.
        - Otherwise, values are encoded as UTF‑8 using `_encode_string`.
        """
        if value is None or not isinstance(value, (int, float, Decimal, Enum, str, bool, bytes)):
            return ""

        string: str = cls._convert_value_to_string(value)

        if not string:
            return ""

        if charset == Charset.LATIN1:
            _pat = cls._RE_UXXXX
            _esc = cls.escape(string, format)
            return _pat.sub(lambda m: f"%26%23{int(m.group(1), 16)}%3B", _esc)

        return cls._encode_string(string, format)

    @staticmethod
    def _convert_value_to_string(value: t.Any) -> str:
        """Coerce a supported scalar to `str`.

        - `bytes` are decoded as UTF‑8.
        - `bool` values are lower‑cased (`"true"` / `"false"`).
        - `str` passes through.
        - All other supported scalars use `str(value)`.
        """
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
        """Percent-encode `string` per RFC3986 or RFC1738, operating on UTF-16 code units.

        We first expand non-BMP code points into surrogate pairs so that indexing and length checks are done in *code units*,
        matching JavaScript semantics. We then walk the string with a manual index, skipping the low surrogate when we emit a
        surrogate pair.
        """
        # Work on UTF-16 code units for JS parity.
        s = cls._to_surrogates(string)
        safe_chars = cls.RFC1738_SAFE_CHARS if format == Format.RFC1738 else cls.SAFE_CHARS
        hex_table = cls.HEX_TABLE
        buffer: t.List[str] = []

        i = 0
        n = len(s)
        while i < n:
            c = ord(s[i])

            if c in safe_chars:
                buffer.append(s[i])
                i += 1
                continue
            # ASCII
            if c < 0x80:
                buffer.append(hex_table[c])
                i += 1
                continue
            # Two-byte UTF-8
            if c < 0x800:
                buffer.extend(
                    [
                        hex_table[0xC0 | (c >> 6)],
                        hex_table[0x80 | (c & 0x3F)],
                    ]
                )
                i += 1
                continue
            # Surrogates → 4-byte UTF-8 (only when a valid high+low pair is present)
            if 0xD800 <= c <= 0xDBFF and (i + 1) < n:
                next_c = ord(s[i + 1])
                if 0xDC00 <= next_c <= 0xDFFF:
                    buffer.extend(cls._encode_surrogate_pair(s, i, c))
                    i += 2
                    continue
            # 3-byte UTF-8 (non-surrogate BMP)
            buffer.extend(
                [
                    hex_table[0xE0 | (c >> 12)],
                    hex_table[0x80 | ((c >> 6) & 0x3F)],
                    hex_table[0x80 | (c & 0x3F)],
                ]
            )
            i += 1

        return "".join(buffer)

    @classmethod
    def _is_safe_char(cls, c: int, format: t.Optional[Format]) -> bool:
        """Return True if code unit `c` is allowed unescaped for the given `format`."""
        return c in cls.RFC1738_SAFE_CHARS if format == Format.RFC1738 else c in cls.SAFE_CHARS

    @classmethod
    def _encode_char(cls, string: str, i: int, c: int) -> t.List[str]:
        """Encode one UTF‑16 code unit (at index `i`) into percent‑encoded UTF‑8 bytes.

        - ASCII (`c &lt; 0x80`) → single `%XX`.
        - Two‑byte, three‑byte UTF‑8 forms as needed.
        - If `c` is a surrogate, defer to `_encode_surrogate_pair`.
        """
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
        """Encode a surrogate pair starting at `i` as a 4‑byte UTF‑8 sequence."""
        buffer: t.List[str] = []
        low = ord(string[i + 1])
        c = 0x10000 + (((c & 0x3FF) << 10) | (low & 0x3FF))
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
        """Expand non‑BMP code points (code point &gt; 0xFFFF) into UTF‑16 surrogate pairs.

        This mirrors how JavaScript strings store characters, allowing compatibility with legacy `%uXXXX` encoding paths
        and consistent behavior with the Node `qs` implementation.
        """
        # Fast path: no non-BMP code points — return original string
        for _ch in string:
            if ord(_ch) > 0xFFFF:
                break
        else:
            return string

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
        """Serialize a `datetime` to ISO‑8601 using `datetime.isoformat()`."""
        return dt.isoformat()
