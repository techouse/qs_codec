"""This module contains the ``DecodeOptions`` class that configures the output of ``decode``."""

import inspect
import typing as t
from dataclasses import dataclass
from enum import Enum
from functools import wraps

from ..enums.charset import Charset
from ..enums.decode_kind import DecodeKind
from ..enums.duplicates import Duplicates
from ..utils.decode_utils import DecodeUtils


@dataclass
class DecodeOptions:
    """Options that configure the output of ``decode``."""

    allow_dots: t.Optional[bool] = None
    """Set to ``True`` to decode dot ``dict`` notation in the encoded input.
    When ``None`` (default), it inherits the value of ``decode_dot_in_keys``."""

    decode_dot_in_keys: t.Optional[bool] = None
    """Set to ``True`` to decode percent‑encoded dots in keys (e.g., ``%2E`` → ``.``).
    Note: it implies ``allow_dots``, so ``decode`` will error if you set ``decode_dot_in_keys`` to ``True``, and
    ``allow_dots`` to ``False``.
    When ``None`` (default), it defaults to ``False``."""

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

    When ``True``, the decoder raises:
    - a ``DecodeError`` for parameter and list limit violations; and
    - an ``IndexError`` when nesting deeper than ``depth`` **and** ``strict_depth=True``.

    When ``False`` (default), the decoder degrades gracefully: it slices the parameter list
    at ``parameter_limit``, stops adding items beyond ``list_limit``, and—if
    ``strict_depth=True``—stops descending once ``depth`` is reached without raising.
    """

    decoder: t.Optional[t.Callable[..., t.Optional[str]]] = DecodeUtils.decode
    """Custom scalar decoder invoked for each raw token prior to interpretation.

    The built-in decoder supports ``kind`` and is invoked as
    ``decoder(string, charset, kind=DecodeKind.KEY|VALUE)``. Custom decoders that omit
    ``kind`` (or ``charset``) are automatically adapted for compatibility. Returning ``None``
    from the decoder uses ``None`` as the scalar value.
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

            # Precompute dispatch to avoid per-call introspection.
            try:
                sig = inspect.signature(user_dec)
                params = sig.parameters
                param_list = list(params.values())

                has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in param_list)
                has_var_pos = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in param_list)

                accepts_charset_pos = False
                accepts_charset_kw = False
                if "charset" in params:
                    p = params["charset"]
                    if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                        accepts_charset_pos = True
                    if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY):
                        accepts_charset_kw = True
                if has_var_pos:
                    accepts_charset_pos = True

                has_kind_param = "kind" in params
                accepts_kind_kw = False
                accepts_kind_pos = False
                if has_kind_param:
                    k = params["kind"]
                    accepts_kind_kw = k.kind in (
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        inspect.Parameter.KEYWORD_ONLY,
                    )
                    accepts_kind_pos = k.kind in (
                        inspect.Parameter.POSITIONAL_ONLY,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    )
                elif has_var_kw:
                    accepts_kind_kw = True  # can pass via **kwargs
                    accepts_kind_pos = False

                # Decide how to represent `kind`: prefer string for maximum compatibility
                pass_kind_as_str = True
                if has_kind_param:
                    ann = params["kind"].annotation
                    if ann is inspect.Signature.empty:
                        pass_kind_as_str = True
                    else:
                        # If annotation is an Enum subclass (eg, DecodeKind), pass the enum.
                        if isinstance(ann, type):
                            pass_kind_as_str = not issubclass(ann, Enum)
                        else:
                            pass_kind_as_str = True
                elif has_var_kw:
                    # With **kwargs but no explicit parameter, safest is to pass string
                    pass_kind_as_str = True

                def dispatch(
                    s: t.Optional[str],
                    charset: t.Optional[Charset],
                    kind: DecodeKind,
                ) -> t.Optional[str]:
                    # Choose enum or string representation for `kind`
                    kind_arg: t.Union[DecodeKind, str] = kind.value if pass_kind_as_str else kind
                    args: t.List[t.Any] = [s]
                    kwargs: t.Dict[str, t.Any] = {}
                    if accepts_charset_pos:
                        args.append(charset)
                    elif accepts_charset_kw or has_var_kw:
                        kwargs["charset"] = charset
                    if accepts_kind_kw:
                        kwargs["kind"] = kind_arg
                    elif accepts_kind_pos:
                        args.append(kind_arg)
                    return user_dec(*args, **kwargs)

            except (TypeError, ValueError):
                # Builtins/callables without retrievable signature: try the most compatible forms.
                def dispatch(
                    s: t.Optional[str],
                    charset: t.Optional[Charset],
                    kind: DecodeKind,
                ) -> t.Optional[str]:
                    # Mark `kind` as used to satisfy linters; legacy decoders ignore it.
                    _ = kind
                    try:
                        return user_dec(s)  # type: ignore[misc]
                    except TypeError as e1:
                        try:
                            return user_dec(s, charset)  # type: ignore[misc]
                        except TypeError as exc:
                            raise e1 from exc

            @wraps(user_dec)
            def _adapter(
                s: t.Optional[str],
                charset: t.Optional[Charset] = Charset.UTF8,
                *,
                kind: DecodeKind = DecodeKind.VALUE,
            ) -> t.Optional[str]:
                """Adapter that dispatches based on the user decoder's signature."""
                return dispatch(s, charset, kind)

            self.decoder = _adapter
