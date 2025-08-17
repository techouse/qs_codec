"""Configuration object for `encode`.

`EncodeOptions` mirrors the behavior and defaults of the reference `qs` implementation. It controls how Python values
(dicts/lists/scalars) are turned into a URL-encoded query string. The options here are intentionally close to the Node.js
library so behavior is predictable across languages.

Key interactions to be aware of:
- `allow_dots` vs `encode_dot_in_keys`: when unspecified, `allow_dots` mirrors the value of `encode_dot_in_keys` (see `__post_init__`).
- `indices` is deprecated and mapped to `list_format` for parity with newer ports.
- `encoder` and `serialize_date` let you customize scalar/date serialization, while `encode=False` short-circuits the encoder entirely.
- `sort` may return -1/0/+1 (like `strcmp`/`NSComparisonResult.rawValue`) to deterministically order keys.
"""

import typing as t
from dataclasses import dataclass, field, fields
from datetime import datetime

from ..enums.charset import Charset
from ..enums.format import Format
from ..enums.list_format import ListFormat
from ..utils.encode_utils import EncodeUtils


@dataclass
class EncodeOptions:
    """Options that configure the output of `encode`.

    Each field corresponds to a knob in the query-string encoder. Defaults aim to be
    unsurprising and compatible with other Techouse qs ports. See per-field docs
    below for details and caveats.
    """

    allow_dots: bool = field(default=None)  # type: ignore [assignment]
    """When `True`, interpret dotted keys as object paths during encoding (e.g. `a.b=1`). If `None`, mirrors `encode_dot_in_keys` (see `__post_init__`)."""

    add_query_prefix: bool = False
    """When `True`, prefix the output with a `?` (useful when appending to a base URL)."""

    allow_empty_lists: bool = False
    """When `True`, include empty lists in the output (e.g. `a[]=` instead of omitting)."""

    indices: t.Optional[bool] = None
    """Deprecated: prefer `list_format`. If set, maps to `ListFormat.INDICES` when `True` or `ListFormat.REPEAT` when `False`."""

    list_format: ListFormat = ListFormat.INDICES
    """Controls how lists are encoded (indices/brackets/repeat/comma). See `ListFormat`."""

    charset: Charset = Charset.UTF8
    """Character encoding used by the encoder (defaults to UTF‑8)."""

    charset_sentinel: bool = False
    """When `True`, include a sentinel parameter announcing the charset (e.g. `utf8=✓`)."""

    delimiter: str = "&"
    """Pair delimiter between tokens (typically `&`; `;` and others are allowed)."""

    encode: bool = True
    """Master switch. When `False`, values/keys are not percent‑encoded (joined as-is)."""

    encode_dot_in_keys: bool = field(default=None)  # type: ignore [assignment]
    """When `True`, encode dots in keys literally. With `encode_values_only=True`, only key dots are encoded while values remain untouched."""

    encode_values_only: bool = False
    """When `True`, the encoder is applied to values only; keys are left unencoded."""

    format: Format = Format.RFC3986
    """Space handling and percent‑encoding style. `RFC3986` encodes spaces as `%20`, while
    `RFC1738` uses `+`."""

    filter: t.Optional[t.Union[t.Callable, t.List[t.Union[str, int]]]] = field(default=None)
    """Restrict which keys get included.
    - If a callable is provided, it is invoked for each key and should return the
    replacement value (or `None` to drop when `skip_nulls` applies).
    - If a list is provided, only those keys/indices are retained.
    """

    skip_nulls: bool = False
    """When `True`, omit keys whose value is `None` entirely (no trailing `=`)."""

    serialize_date: t.Callable[[datetime], t.Optional[str]] = EncodeUtils.serialize_date
    """Hook to stringify `datetime` values before encoding; returning `None` is treated as a null value
    (subject to null-handling options), not as a fallback to ISO-8601."""

    encoder: t.Callable[[t.Any, t.Optional[Charset], t.Optional[Format]], str] = field(  # type: ignore [assignment]
        default=EncodeUtils.encode, init=False, repr=False
    )
    """Custom scalar encoder. Signature: `(value, charset|None, format|None) -> str`.
    Note: when `encode=False`, this is bypassed and values are joined without
    percent‑encoding."""

    _encoder: t.Callable[[t.Any, t.Optional[Charset], t.Optional[Format]], str] = field(init=False, repr=False)

    @property  # type: ignore [no-redef]
    def encoder(self) -> t.Callable[[t.Any, t.Optional[Charset], t.Optional[Format]], str]:  # noqa: F811
        """Return a view of the encoder bound to the current `charset` and `format`.

        The returned callable has signature `(value) -> str` and internally calls the
        underlying `_encoder(value, self.charset, self.format)`.
        """
        return lambda v, c=self.charset, f=self.format: self._encoder(v, c, f)  # type: ignore [misc]

    @encoder.setter
    def encoder(self, value: t.Optional[t.Callable[[t.Any, t.Optional[Charset], t.Optional[Format]], str]]) -> None:
        """Set the underlying encoder, falling back to `EncodeUtils.encode` when `None` or non‑callable."""
        self._encoder = value if callable(value) else EncodeUtils.encode

    strict_null_handling: bool = False
    """When `True`, distinguish empty strings from `None`: `None` → `a` (no `=`), empty string → `a=`."""

    comma_round_trip: t.Optional[bool] = None
    """Only used with `ListFormat.COMMA`. When `True`, single‑item lists append `[]` so they round‑trip back to a list on decode."""

    sort: t.Optional[t.Callable[[t.Any, t.Any], int]] = field(default=None)
    """Optional comparator for deterministic key ordering. Must return -1, 0, or +1."""

    def __post_init__(self) -> None:
        """Normalize interdependent options.

        - If `allow_dots` is `None`, mirror `encode_dot_in_keys` (treating non‑`True` as `False`).
        - Default `encode_dot_in_keys` to `False` when unset.
        - Map deprecated `indices` to `list_format` for backward compatibility.
        """
        if not hasattr(self, "_encoder") or self._encoder is None:
            self._encoder = EncodeUtils.encode
        # Default `encode_dot_in_keys` first, then mirror into `allow_dots` when unspecified.
        if self.encode_dot_in_keys is None:
            self.encode_dot_in_keys = False
        if self.allow_dots is None:
            self.allow_dots = bool(self.encode_dot_in_keys)
        # Map deprecated `indices` to `list_format` for backward compatibility.
        if self.indices is not None:
            self.list_format = ListFormat.INDICES if self.indices else ListFormat.REPEAT

    def __eq__(self, other: object) -> bool:
        """Structural equality that treats the bound encoder consistently.

        `dataclasses.asdict` would serialize the `encoder` property (a lambda bound to
        charset/format) differently on each instance. To compare meaningfully, we swap in
        `_encoder` (the raw callable) on both sides before comparing dictionaries.
        """
        if not isinstance(other, EncodeOptions):
            return False

        for f in fields(EncodeOptions):
            name = f.name
            if name == "encoder":
                v1 = self._encoder
                v2 = other._encoder
            else:
                v1 = getattr(self, name)
                v2 = getattr(other, name)
            if v1 != v2:
                return False
        return True
