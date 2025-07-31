"""A query string encoding and decoding library for Python. Ported from qs_codec for JavaScript."""

__version__ = "1.1.7"

from .decode import decode, load, loads
from .encode import dumps, encode
from .enums.charset import Charset
from .enums.duplicates import Duplicates
from .enums.format import Format
from .enums.list_format import ListFormat
from .enums.sentinel import Sentinel
from .models.decode_options import DecodeOptions
from .models.encode_options import EncodeOptions
from .models.undefined import Undefined


__all__ = [
    "decode",
    "encode",
    "dumps",
    "loads",
    "load",
    "Charset",
    "Duplicates",
    "Format",
    "ListFormat",
    "Sentinel",
    "DecodeOptions",
    "EncodeOptions",
    "Undefined",
]
