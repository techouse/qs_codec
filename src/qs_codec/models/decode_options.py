"""Options that configure the output of QS.decode."""

import typing as t
from dataclasses import dataclass, field

from ..enums.charset import Charset
from ..enums.duplicates import Duplicates
from ..utils.decode_utils import DecodeUtils


@dataclass
class DecodeOptions:
    """Options that configure the output of QS.decode."""

    # Set to `True` to decode dot `Dict` notation in the encoded input.
    allow_dots: bool = field(default=None)  # type: ignore [assignment]

    # Set to `True` to decode dots in keys.
    # Note: it implies `allow_dots`, so `QS.decode` will error if you set decode_dot_in_keys` to `True`, and
    # `allow_dots` to `False.
    decode_dot_in_keys: bool = field(default=None)  # type: ignore [assignment]

    # Set to `True` to allow empty `List` values inside `Dict`s in the encoded input
    allow_empty_lists: bool = False

    # `QS` will limit specifying indices in a `List` to a maximum index of `20`.
    # Any `List` members with an index of greater than `20` will instead be converted to a `Dict` with the index as the
    # key. This is needed to handle cases when someone sent, for example, `a[999999999]` and it will take significant
    # time to iterate over this huge `List`.
    # This limit can be overridden by passing a `list_limit` option.
    list_limit: int = 20

    # The character encoding to use when decoding the input.
    charset: Charset = Charset.UTF8

    # Some services add an initial `utf8=✓` value to forms so that old InternetExplorer versions are more likely to
    # submit the form as `utf-8`. Additionally, the server can check the value against wrong encodings of the checkmark
    # character and detect that a query string or `application/x-www-form-urlencoded` body was *not* sent as `utf-8`,
    # e.g. if the form had an `accept-charset` parameter or the containing page had a different character set.
    #
    # `QS` supports this mechanism via the `charset_sentinel` option.
    # If specified, the `utf-8` parameter will be omitted from the returned `Dict`.
    # It will be used to switch to `latin-1`/`utf-8` mode depending on how the checkmark is encoded.
    #
    # Important: When you specify both the `charset` option and the `charset_sentinel` option,
    # the `charset` will be overridden when the request contains a `utf-8` parameter from which the actual charset
    # can be deduced. In that sense the `charset` will behave as the default charset rather than the authoritative
    # charset.
    charset_sentinel: bool = False

    # Set to `True` to parse the input as a comma-separated value.
    # Note: nested `Dict`s, such as `'a={b:1},{c:d}'` are not supported.
    comma: bool = False

    # The delimiter to use when splitting key-value pairs in the encoded input.
    # Can be a `str` or a `Pattern`.
    delimiter: t.Union[str, t.Pattern[str]] = "&"

    # By default, when nesting `Dict`s `QS` will only decode up to 5 children deep.
    # This depth can be overridden by setting the `depth`.
    # The depth limit helps mitigate abuse when `QS` is used to parse user input,
    # and it is recommended to keep it a reasonably small number.
    depth: int = 5

    # For similar reasons, by default `QS` will only parse up to 1000
    # parameters. This can be overridden by passing a `parameter_limit`
    # option.
    parameter_limit: t.Union[int, float] = 1000

    # Change the duplicate key handling strategy
    duplicates: Duplicates = Duplicates.COMBINE

    # Set to `True` to ignore the leading question mark query prefix in the encoded input.
    ignore_query_prefix: bool = False

    # Set to `True` to interpret HTML numeric entities (`&#...;`) in the encoded input.
    interpret_numeric_entities: bool = False

    # To disable `List` parsing entirely, set `parse_lists` to `False`.
    parse_lists: bool = True

    # Set to true to decode values without `=` to `null`.
    strict_null_handling: bool = False

    # Set a decoder to affect the decoding of the input.
    decoder: t.Callable[[t.Optional[str], t.Optional[Charset]], t.Any] = DecodeUtils.decode

    def __post_init__(self):
        """Post-initialization."""
        if self.allow_dots is None:
            self.allow_dots = self.decode_dot_in_keys is True or False
        if self.decode_dot_in_keys is None:
            self.decode_dot_in_keys = False
