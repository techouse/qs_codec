"""This module contains the ``DecodeOptions`` class that configures the output of ``decode``."""

import inspect
import typing as t
from dataclasses import dataclass
from functools import wraps

from ..enums.charset import Charset
from ..enums.decode_kind import DecodeKind
from ..enums.duplicates import Duplicates
from ..utils.decode_utils import DecodeUtils


@dataclass
class DecodeOptions:
    """Options that configure the output of ``decode``."""

    allow_dots: t.Optional[bool] = None
    """Set to ``True`` to decode dot ``dict`` notation in the encoded input."""

    decode_dot_in_keys: t.Optional[bool] = None
    """Set to ``True`` to decode dots in keys.
    Note: it implies ``allow_dots``, so ``decode`` will error if you set ``decode_dot_in_keys`` to ``True``, and
    ``allow_dots`` to ``False``."""

    allow_empty_lists: bool = False
    """Set to ``True`` to allow empty ``list`` values inside ``dict``\\s in the encoded input."""

    list_limit: int = 20
    """Maximum number of **indexed** items allowed in a single list (default: ``20``).

    During decoding, keys like ``a[0]``, ``a[1]``, … are treated as list indices. If an
    index exceeds this limit, the container is treated as a ``dict`` instead, with the
    numeric index kept as a string key (e.g., ``{"999": "x"}``) to prevent creation of
    massive sparse lists (e.g., ``a[999999999]``).

    This limit also applies to comma–split lists when ``comma=True``. Set a larger value if
    you explicitly need more items, or set a smaller one to harden against abuse.
    """

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
    """Strategy for handling duplicate keys in the input.

    - ``COMBINE`` (default): merge values into a list (e.g., ``a=1&a=2`` → ``{"a": [1, 2]}``).
    - ``FIRST``: keep the first value and ignore subsequent ones (``{"a": 1}``).
    - ``LAST``: keep only the last value seen (``{"a": 2}``).
    """

    ignore_query_prefix: bool = False
    """Set to ``True`` to ignore the leading question mark query prefix in the encoded input."""

    interpret_numeric_entities: bool = False
    """Set to ``True`` to interpret HTML numeric entities (``&#...;``) in the encoded input."""

    parse_lists: bool = True
    """To disable ``list`` parsing entirely, set ``parse_lists`` to ``False``."""

    strict_depth: bool = False
    """Enforce the ``depth`` limit when decoding nested structures.

    When ``True``, the decoder will not descend beyond ``depth`` levels. Combined with
    ``raise_on_limit_exceeded``:

    - if ``raise_on_limit_exceeded=True``, exceeding the depth raises an ``IndexError``;
    - if ``False``, the decoder stops descending and treats deeper content as a terminal value, preserving the last valid container without raising.
    """

    strict_null_handling: bool = False
    """Set to ``True`` to decode values without ``=`` to ``None``."""

    raise_on_limit_exceeded: bool = False
    """Raise instead of degrading gracefully when limits are exceeded.

    When ``True``, the decoder raises a ``DecodeError`` in any of the following cases:

    - more than ``parameter_limit`` top‑level parameters,
    - more than ``list_limit`` items in a single list (including comma–split lists),
    - nesting deeper than ``depth`` **when** ``strict_depth=True``.

    When ``False`` (default), the decoder degrades gracefully: it slices the parameter list
    at ``parameter_limit``, stops adding items beyond ``list_limit``, and—if
    ``strict_depth=True``—stops descending once ``depth`` is reached without raising.
    """

    decoder: t.Optional[t.Callable[..., t.Optional[str]]] = DecodeUtils.decode
    """Custom scalar decoder invoked for each raw token prior to interpretation.

    Signature: ``Callable[[Optional[str], Optional[Charset]], Optional[str]]`` by default, but the
    parser will prefer ``decoder(string, charset, kind=DecodeKind.KEY|VALUE)`` when available.
    If a custom decoder does not accept ``kind``, it will be automatically adapted so existing
    decoders continue to work. Returning ``None`` from the decoder uses ``None`` as the scalar value.
    """

    def __post_init__(self) -> None:
        """Post-initialization."""
        # Default `decode_dot_in_keys` first, then mirror into `allow_dots` when unspecified.
        if self.decode_dot_in_keys is None:
            self.decode_dot_in_keys = False
        if self.allow_dots is None:
            self.allow_dots = bool(self.decode_dot_in_keys)

        # Enforce consistency with the docs: `decode_dot_in_keys=True` implies `allow_dots=True`.
        if self.decode_dot_in_keys and not self.allow_dots:
            raise ValueError("decode_dot_in_keys=True implies allow_dots=True")

        # decoder setup + compatibility wrapper
        if self.decoder is None:
            self.decoder = DecodeUtils.decode
        else:
            user_dec = self.decoder

            @wraps(user_dec)
            def _adapter(
                s: t.Optional[str],
                charset: t.Optional[Charset] = Charset.UTF8,
                *,
                kind: DecodeKind = DecodeKind.VALUE,
            ) -> t.Optional[str]:
                """Adapter that dispatches based on the user decoder's signature.

                Supported forms:
                - dec(s)
                - dec(s, charset)
                - dec(s, charset, kind)
                - dec(s, charset, *, kind=...)
                If **kwargs is present, we may pass `kind` as a keyword even without an explicit parameter.
                """
                try:
                    sig = inspect.signature(user_dec)
                except (TypeError, ValueError):
                    # Builtins/callables without a retrievable signature: conservative call
                    return user_dec(s, charset)

                params = sig.parameters
                param_list = list(params.values())

                # Does it accept **kwargs?
                has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in param_list)
                # Does it accept *args?
                has_var_pos = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in param_list)

                # Charset handling
                accepts_charset_pos = False
                accepts_charset_kw = False
                if "charset" in params:
                    p = params["charset"]
                    if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                        accepts_charset_pos = True
                    if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY):
                        accepts_charset_kw = True
                # If *args is present, we can safely pass charset positionally.
                if has_var_pos:
                    accepts_charset_pos = True

                # Kind handling
                has_kind_param = "kind" in params
                accepts_kind_kw = False
                if has_kind_param:
                    k = params["kind"]
                    accepts_kind_kw = k.kind in (
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        inspect.Parameter.KEYWORD_ONLY,
                    )
                elif has_var_kw:
                    accepts_kind_kw = True  # can pass via **kwargs

                # Choose representation for `kind`; default to string for broader compatibility when uncertain.
                kind_arg: t.Union[DecodeKind, str] = kind.value
                if has_kind_param:
                    ann = params["kind"].annotation
                    # Prefer enum when explicitly annotated as DecodeKind
                    if ann is DecodeKind or getattr(ann, "__name__", None) == "DecodeKind":
                        kind_arg = kind

                # Build call
                args: t.List[t.Any] = [s]
                kwargs: t.Dict[str, t.Any] = {}

                if accepts_charset_pos:
                    args.append(charset)
                elif accepts_charset_kw or has_var_kw:
                    kwargs["charset"] = charset

                if accepts_kind_kw:
                    kwargs["kind"] = kind_arg

                return user_dec(*args, **kwargs)

            self.decoder = _adapter
