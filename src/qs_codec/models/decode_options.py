"""This module contains the ``DecodeOptions`` class that configures the output of ``decode``."""

import typing as t
from dataclasses import dataclass, field

from ..enums.charset import Charset
from ..enums.duplicates import Duplicates
from ..utils.decode_utils import DecodeUtils


@dataclass
class DecodeOptions:
    """Options that configure the output of ``decode``."""

    allow_dots: bool = field(default=None)  # type: ignore [assignment]
    """Set to ``True`` to decode dot ``dict`` notation in the encoded input."""

    decode_dot_in_keys: bool = field(default=None)  # type: ignore [assignment]
    """Set to ``True`` to decode dots in keys.
    Note: it implies ``allow_dots``, so ``decode`` will error if you set ``decode_dot_in_keys`` to ``True``, and
    ``allow_dots`` to ``False``."""

    allow_empty_lists: bool = False
    """Set to ``True`` to allow empty ``list`` values inside ``dict``\\s in the encoded input."""

    list_limit: int = 20
    """``qs_codec`` will limit specifying indices in a ``list`` to a maximum index of ``20``.
    Any ``list`` members with an index of greater than ``20`` will instead be converted to a ``dict`` with the index as
    the key. This is needed to handle cases when someone sent, for example, ``a[999999999]`` and it will take
    significant time to iterate over this huge ``list``.
    This limit can be overridden by passing a ``list_limit`` option."""

    charset: Charset = Charset.UTF8
    """The character encoding to use when decoding the input."""

    charset_sentinel: bool = False
    """Some services add an initial ``utf8=✓`` value to forms so that old InternetExplorer versions are more likely to
    submit the form as ``utf-8``. Additionally, the server can check the value against wrong encodings of the checkmark
    character and detect that a query string or ``application/x-www-form-urlencoded`` body was *not* sent as ``utf-8``,
    e.g. if the form had an ``accept-charset`` parameter or the containing page had a different character set.

    ``qs_codec`` supports this mechanism via the ``charset_sentinel`` option.
    If specified, the ``utf-8`` parameter will be omitted from the returned ``dict``.
    It will be used to switch to ``LATIN1`` or ``UTF8`` mode depending on how the checkmark is encoded.

    Important: When you specify both the ``charset`` option and the ``charset_sentinel`` option,
    the ``charset`` will be overridden when the request contains a ``utf-8`` parameter from which the actual charset
    can be deduced. In that sense the ``charset`` will behave as the default charset rather than the authoritative
    charset."""

    comma: bool = False
    """Set to ``True`` to parse the input as a comma-separated value.
    Note: nested ``dict`` s, such as ``'a={b:1},{c:d}'`` are not supported."""

    delimiter: t.Union[str, t.Pattern[str]] = "&"
    """The delimiter to use when splitting key-value pairs in the encoded input. Can be a ``str`` or a ``Pattern``."""

    depth: int = 5
    """By default, when nesting ``dict``\\s ``qs_codec`` will only decode up to 5 children deep.
    This depth can be overridden by setting the ``depth``.
    The depth limit helps mitigate abuse when ``qs_codec`` is used to parse user input,
    and it is recommended to keep it a reasonably small number."""

    parameter_limit: t.Union[int, float] = 1000
    """For similar reasons, by default ``qs_codec`` will only parse up to 1000 parameters. This can be overridden by
    passing a ``parameter_limit`` option."""

    duplicates: Duplicates = Duplicates.COMBINE
    """Change the duplicate key handling strategy."""

    ignore_query_prefix: bool = False
    """Set to ``True`` to ignore the leading question mark query prefix in the encoded input."""

    interpret_numeric_entities: bool = False
    """Set to ``True`` to interpret HTML numeric entities (``&#...;``) in the encoded input."""

    parse_lists: bool = True
    """To disable ``list`` parsing entirely, set ``parse_lists`` to ``False``."""

    strict_depth: bool = False
    """Set to ``True`` to raise an error when the input exceeds the ``depth`` limit."""

    strict_null_handling: bool = False
    """Set to ``True`` to decode values without ``=`` to ``None``."""

    raise_on_limit_exceeded: bool = False
    """Set to ``True`` to raise an error when the input contains more parameters than the ``list_limit``."""

    decoder: t.Callable[[t.Optional[str], t.Optional[Charset]], t.Any] = DecodeUtils.decode
    """Set a ``Callable`` to affect the decoding of the input."""

    def __post_init__(self) -> None:
        """Post-initialization."""
        if self.allow_dots is None:
            self.allow_dots = self.decode_dot_in_keys is True or False
        if self.decode_dot_in_keys is None:
            self.decode_dot_in_keys = False
