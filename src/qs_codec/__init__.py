"""
Query string encoding/decoding for Python.

This package is a Python port of the popular `qs` library for JavaScript/Node.js.
It strives to match `qs` semantics and edge cases — including list/array formats,
duplicate key handling, RFC 3986 vs RFC 1738 formatting, character set sentinels,
and other interoperability details.

The package root re-exports the most commonly used functions and enums so you can:

    >>> from qs_codec import encode, decode, ListFormat, EncodeOptions
    >>> encode({"a": [1, 2, 3]}, options=EncodeOptions(list_format=ListFormat.brackets))
    'a[]=1&a[]=2&a[]=3'
"""

# Package version (PEP 440). Bump in lockstep with distribution metadata.
__version__ = "1.2.1"

from .decode import decode, load, loads
from .encode import dumps, encode
from .enums.charset import Charset
from .enums.decode_kind import DecodeKind
from .enums.duplicates import Duplicates
from .enums.format import Format
from .enums.list_format import ListFormat
from .enums.sentinel import Sentinel
from .models.decode_options import DecodeOptions
from .models.encode_options import EncodeOptions
from .models.undefined import Undefined


# Public API surface re-exported at the package root.
__all__ = [
    "decode",
    "encode",
    "dumps",
    "loads",
    "load",
    "Charset",
    "DecodeKind",
    "Duplicates",
    "Format",
    "ListFormat",
    "Sentinel",
    "DecodeOptions",
    "EncodeOptions",
    "Undefined",
]
