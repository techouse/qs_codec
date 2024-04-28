"""A query string encoding and decoding library for Python. Ported from qs_codec for JavaScript."""

__version__ = "0.1.5"

from .decode import decode
from .encode import encode
from .enums.charset import Charset
from .enums.duplicates import Duplicates
from .enums.format import Format
from .enums.list_format import ListFormat
from .enums.sentinel import Sentinel
from .models.decode_options import DecodeOptions
from .models.encode_options import EncodeOptions
from .models.undefined import Undefined
