"""This module contains the `EncodeOptions` class that configures the output of QS.encode."""

import typing as t
from dataclasses import asdict, dataclass, field
from datetime import datetime

from ..enums.charset import Charset
from ..enums.format import Format
from ..enums.list_format import ListFormat
from ..utils.encode_utils import EncodeUtils


@dataclass
class EncodeOptions:
    """Options that configure the output of QS.encode."""

    # Set to `True` to use dot `Dict` notation in the encoded output.
    allow_dots: bool = field(default=None)  # type: ignore [assignment]

    # Set to `True` to add a question mark `?` prefix to the encoded output.
    add_query_prefix: bool = False

    # Set to `True` to allow empty `List`s in the encoded output.
    allow_empty_lists: bool = False

    # Deprecated: Use `list_format` instead.
    indices: t.Optional[bool] = None

    # The `List` encoding format to use.
    list_format: ListFormat = ListFormat.INDICES

    # The character encoding to use.
    charset: Charset = Charset.UTF8

    # Set to `True` to announce the character by including an `utf8=✓` parameter
    # with the proper encoding of the checkmark, similar to what Ruby on Rails
    # and others do when submitting forms.
    charset_sentinel: bool = False

    # The delimiter to use when joining key-value pairs in the encoded output."""
    delimiter: str = "&"

    # Set to `False` to disable encoding."""
    encode: bool = True

    # Encode `Dict` keys using dot notation by setting `encode_dot_in_keys` to `True`
    # Caveat: When `encode_values_only` is `True` as well as `encode_dot_in_keys`,
    # only dots in keys and nothing else will be encoded.
    encode_dot_in_keys: bool = field(default=None)  # type: ignore [assignment]

    # Encoding can be disabled for keys by setting the `encode_values_only` to `True`"""
    encode_values_only: bool = False

    # The encoding format to use.
    # The default `format` is `Format.RFC3986` which encodes `' '` to `%20` which is backward compatible.
    # You can also set `format` to `Format.RFC1738` which encodes `' '` to `+`.
    format: Format = Format.RFC3986

    # Use the `filter` option to restrict which keys will be included in the encoded output.
    # If you pass a `Callable`, it will be called for each key to obtain the replacement value.
    # If you pass a `List`, it will be used to select properties and `List` indices to be encoded.
    filter: t.Optional[t.Union[t.Callable, t.List[t.Union[str, int]]]] = field(default=None)

    # Set to `True` to completely skip encoding keys with `null` values"""
    skip_nulls: bool = False

    # If you only want to override the serialization of `datetime` objects,
    # you can provide a `Callable`.
    serialize_date: t.Callable[[datetime], str] = EncodeUtils.serialize_date

    # Set an `Encoder` to affect the encoding of values.
    # Note: the `encoder` option does not apply if `encode` is `False`
    encoder: t.Callable[[t.Any, t.Optional[Charset], t.Optional[Format]], str] = field(  # type: ignore [assignment]
        default_factory=EncodeUtils.encode  # type: ignore [arg-type]
    )
    _encoder: t.Callable[[t.Any, t.Optional[Charset], t.Optional[Format]], str] = field(init=False, repr=False)

    @property  # type: ignore [no-redef]
    def encoder(self) -> t.Callable[[t.Any, t.Optional[Charset], t.Optional[Format]], str]:  # noqa: F811
        """Get the encoder function."""
        return lambda v, c=self.charset, f=self.format: self._encoder(v, c, f)  # type: ignore [misc]

    @encoder.setter
    def encoder(self, value: t.Optional[t.Callable[[t.Any, t.Optional[Charset], t.Optional[Format]], str]]) -> None:
        self._encoder = value if callable(value) else EncodeUtils.encode  # type: ignore [assignment]

    # Set to `True` to distinguish between `null` values and empty `str`ings.
    # This way the encoded string `null` values will have no `=` sign.
    strict_null_handling: bool = False

    # When `list_format` is set to `ListFormat.COMMA`, you can also set
    # `comma_round_trip` option to `True` or `False`, to append `[]` on
    # single-item `List`s, so that they can round trip through a parse.
    comma_round_trip: t.Optional[bool] = None

    # Set a `Sorter` to affect the order of parameter keys.
    sort: t.Optional[t.Callable[[t.Any, t.Any], int]] = field(default=None)

    def __post_init__(self):
        """Post-initialization."""
        if self.allow_dots is None:
            self.allow_dots = self.encode_dot_in_keys is True or False
        if self.encode_dot_in_keys is None:
            self.encode_dot_in_keys = False
        if self.indices is not None:
            self.list_format = ListFormat.INDICES if self.indices else ListFormat.REPEAT

    def __eq__(self, other: object) -> bool:
        """Compare two `EncodeOptions` objects."""
        if not isinstance(other, EncodeOptions):
            return False

        self_dict = asdict(self)
        other_dict = asdict(other)

        self_dict["encoder"] = self._encoder
        other_dict["encoder"] = other._encoder

        return self_dict == other_dict
