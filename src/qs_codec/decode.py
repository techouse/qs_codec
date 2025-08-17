"""Query string **decoder** (a.k.a. parser) with feature parity to the Node.js `qs` package.

Highlights
----------
- Accepts either a raw query string or a pre-tokenized mapping (mirrors `qs.parse`).
- Supports RFC 3986 / 1738 percent-decoding via `DecodeOptions.decoder`.
- Handles bracket notation, indices, dotted keys (opt-in), and duplicate keys strategies.
- Respects list parsing limits, depth limits, and charset sentinels (`utf8=%E2%9C%93` / `utf8=%26%2310003%3B`).
- Returns plain `dict` / `list` containers and never mutates the caller’s input.

This module intentionally keeps the control flow close to the original reference implementation
so that behavior across ports stays predictable and easy to verify with shared test vectors.
"""

import re
import typing as t
from math import isinf

from .enums.charset import Charset
from .enums.duplicates import Duplicates
from .enums.sentinel import Sentinel
from .models.decode_options import DecodeOptions
from .models.undefined import Undefined
from .utils.decode_utils import DecodeUtils
from .utils.utils import Utils


def decode(
    value: t.Optional[t.Union[str, t.Mapping[str, t.Any]]],
    options: DecodeOptions = DecodeOptions(),
) -> t.Dict[str, t.Any]:
    """
    Decode a query string (or a pre-tokenized mapping) into a nested ``Dict[str, Any]``.

    Parameters
    ----------
    value:
        Either a raw query string (``str``) or an already-parsed mapping (``Mapping[str, Any]``).
        Passing a mapping is useful in tests or when a custom tokenizer is used upstream.
    options:
        ``DecodeOptions`` controlling delimiter, duplicates policy, list & depth limits, dot-notation, decoding charset, and more.

    Returns
    -------
    Dict[str, Any]
        A freshly-allocated mapping containing nested dicts/lists/values.

    Raises
    ------
    ValueError
        If ``value`` is neither ``str`` nor ``Mapping``, or when limits are violated under ``raise_on_limit_exceeded=True``.

    Notes
    -----
    - Empty/falsey ``value`` returns an empty dict.
    - When the *number of top-level tokens* exceeds ``list_limit`` and ``parse_lists`` is enabled, the parser temporarily **disables list parsing** for this invocation to avoid quadratic work. This mirrors the behavior of other ports and keeps large flat query strings efficient.
    """
    obj: t.Dict[str, t.Any] = {}

    if not value:
        return obj

    if not isinstance(value, (str, dict)):
        raise ValueError("The input must be a String or a Dict")

    temp_obj: t.Optional[t.Dict[str, t.Any]] = (
        _parse_query_string_values(value, options) if isinstance(value, str) else value
    )

    # If a raw query string produced *more parts than list_limit*, turn list parsing off.
    # This prevents O(n^2) behavior when the input is a very large flat list of tokens.
    # We only toggle for this call (mutating the local `options` instance by design,
    # consistent with the other ports).
    if temp_obj is not None and options.parse_lists and 0 < options.list_limit < len(temp_obj):
        options.parse_lists = False

    # Iterate over the keys and setup the new object
    if temp_obj:
        for key, val in temp_obj.items():
            new_obj: t.Any = _parse_keys(key, val, options, isinstance(value, str))

            if not obj and isinstance(new_obj, dict):
                obj = new_obj
                continue

            obj = Utils.merge(obj, new_obj, options)  # type: ignore [assignment]

    return Utils.compact(obj)


# Alias for decode function
load = decode


def loads(value: t.Optional[str], options: DecodeOptions = DecodeOptions()) -> t.Dict[str, t.Any]:
    """
    Alias for ``decode``. Decodes a query string into a ``Dict[str, Any]``.

    Use ``decode`` if you want to pass a ``Dict[str, Any]``.
    """
    return decode(value, options)


def _interpret_numeric_entities(value: str) -> str:
    """Convert HTML numeric entities (e.g., ``&#169;``) to their character equivalents.

    Only used when ``options.interpret_numeric_entities`` is True and the effective charset
    is Latin-1; see the Node `qs` compatibility behavior.
    """
    return re.sub(r"&#(\d+);", lambda match: chr(int(match.group(1))), value)


def _parse_array_value(value: t.Any, options: DecodeOptions, current_list_length: int) -> t.Any:
    """Post-process a raw scalar for list semantics and enforce `list_limit`.

    Behavior
    --------
    - If `comma=True` and `value` is a string that contains commas, split into a list.
    - Otherwise, enforce the per-list length limit by comparing `current_list_length` to `options.list_limit`. When `raise_on_limit_exceeded=True`, violations raise `ValueError`.

    Returns either the original value or a list of values, without decoding (that happens later).
    """
    if isinstance(value, str) and value and options.comma and "," in value:
        split_val: t.List[str] = value.split(",")
        if options.raise_on_limit_exceeded and len(split_val) > options.list_limit:
            raise ValueError(
                f"List limit exceeded: Only {options.list_limit} element{'' if options.list_limit == 1 else 's'} allowed in a list."
            )
        return split_val

    if options.raise_on_limit_exceeded and current_list_length >= options.list_limit:
        raise ValueError(
            f"List limit exceeded: Only {options.list_limit} element{'' if options.list_limit == 1 else 's'} allowed in a list."
        )

    return value


def _parse_query_string_values(value: str, options: DecodeOptions) -> t.Dict[str, t.Any]:
    """Tokenize a raw query string into a flat ``Dict[str, Any]``.

    Responsibilities
    ----------------
    - Strip a leading '?' if ``ignore_query_prefix`` is True.
    - Normalize percent-encoded square brackets (``%5B/%5D``) so the key splitter can operate.
    - Split into parts using either a string delimiter or a regex delimiter.
    - Enforce ``parameter_limit`` (optionally raising).
    - Detect the UTF-8/Latin-1 charset via the `utf8=…` sentinel when enabled.
    - For each ``key=value`` pair:
        * Percent-decode key/value using the selected charset.
        * Apply list/comma logic to values.
        * Interpret numeric entities for Latin-1 when requested.
        * Handle empty brackets ``[]`` as list markers.
        * Merge duplicate keys according to ``duplicates`` policy.

    The output is a *flat* dict (keys are full key-path strings). Higher-level structure is constructed later by ``_parse_keys`` / ``_parse_object``.
    """
    obj: t.Dict[str, t.Any] = {}

    clean_str: str = value.replace("?", "", 1) if options.ignore_query_prefix else value
    clean_str = clean_str.replace("%5B", "[").replace("%5b", "[").replace("%5D", "]").replace("%5d", "]")

    # Compute an effective parameter limit (None means "no limit").
    limit: t.Optional[int] = None if isinf(options.parameter_limit) else options.parameter_limit  # type: ignore [assignment]

    # Guard against non-positive limits early for clearer errors.
    if limit is not None and limit <= 0:
        raise ValueError("Parameter limit must be a positive integer.")

    parts: t.List[str]
    # Split using either a compiled regex or a literal string delimiter (do it once, then slice if needed).
    if isinstance(options.delimiter, re.Pattern):
        _all_parts = re.split(options.delimiter, clean_str)
    else:
        _all_parts = clean_str.split(options.delimiter)

    if (limit is not None) and limit:
        _take = limit + 1 if options.raise_on_limit_exceeded else limit
        parts = _all_parts[:_take]
    else:
        parts = _all_parts

    # Enforce parameter count when strict mode is enabled.
    if options.raise_on_limit_exceeded and (limit is not None) and len(parts) > limit:
        raise ValueError(f"Parameter limit exceeded: Only {limit} parameter{'' if limit == 1 else 's'} allowed.")

    skip_index: int = -1  # Keep track of where the utf8 sentinel was found
    i: int

    charset: Charset = options.charset

    # Probe for `utf8=` charset sentinel and adjust decoding charset accordingly.
    if options.charset_sentinel:
        for i, _part in enumerate(parts):
            if _part.startswith("utf8="):
                if _part == Sentinel.CHARSET.encoded:
                    charset = Charset.UTF8
                elif _part == Sentinel.ISO.encoded:
                    charset = Charset.LATIN1
                skip_index = i
                break

    # Iterate over parts and decode each key/value pair.
    for i, _ in enumerate(parts):
        if i == skip_index:
            continue

        part: str = parts[i]
        bracket_equals_pos: int = part.find("]=")
        pos: int = part.find("=") if bracket_equals_pos == -1 else (bracket_equals_pos + 1)

        key: str
        val: t.Union[t.List[t.Any], t.Tuple[t.Any], str, t.Any]
        if pos == -1:
            key = options.decoder(part, charset)
            val = None if options.strict_null_handling else ""
        else:
            key = options.decoder(part[:pos], charset)
            val = Utils.apply(
                _parse_array_value(
                    part[pos + 1 :],
                    options,
                    len(obj[key]) if key in obj and isinstance(obj[key], (list, tuple)) else 0,
                ),
                lambda v: options.decoder(v, charset),
            )

        if val and options.interpret_numeric_entities and charset == Charset.LATIN1:
            val = _interpret_numeric_entities(
                val if isinstance(val, str) else ",".join(val) if isinstance(val, (list, tuple)) else str(val)
            )

        # If the pair used empty brackets syntax and list parsing is enabled, force an array container.
        # Always wrap exactly once to preserve list-of-lists semantics when comma splitting applies.
        if options.parse_lists and "[]=" in part:
            val = [val]

        existing: bool = key in obj

        # Combine/overwrite according to the configured duplicates policy.
        if existing and options.duplicates == Duplicates.COMBINE:
            obj[key] = Utils.combine(obj[key], val)
        elif not existing or options.duplicates == Duplicates.LAST:
            obj[key] = val

    return obj


def _parse_object(
    chain: t.Union[t.List[str], t.Tuple[str, ...]], val: t.Any, options: DecodeOptions, values_parsed: bool
) -> t.Any:
    """Fold a flat key-path chain into nested containers.

    Parameters
    ----------
    chain:
        Key segments like ``["user", "[tags]", "[]"]`` produced by the key splitter.
        Bracketed indices and empty brackets are preserved here.
    val:
        The (possibly preprocessed) leaf value.
    options:
        Decoding options governing list handling, depth, and index interpretation.
    values_parsed:
        Whether `val` has already been decoded and split; influences list handling.

    Notes
    -----
    - Builds lists when encountering ``[]`` (respecting ``allow_empty_lists`` and null handling).
    - Converts bracketed numeric segments into list indices when allowed and within ``list_limit``.
    - When list parsing is disabled and an empty segment is encountered, coerces to ``{"0": leaf}`` to preserve round-trippability with other ports.
    """
    current_list_length: int = 0

    # If the chain ends with an empty list marker, compute current list length for limit checks.
    if bool(chain) and chain[-1] == "[]":
        parent_key: t.Optional[int]

        try:
            parent_key = int("".join(chain[0:-1]))
        except ValueError:
            parent_key = None

        if parent_key is not None and isinstance(val, (list, tuple)) and parent_key in dict(enumerate(val)):
            current_list_length = len(val[parent_key])

    leaf: t.Any = val if values_parsed else _parse_array_value(val, options, current_list_length)

    # Walk the chain from the leaf to the root, building nested containers on the way out.
    i: int
    for i in reversed(range(len(chain))):
        obj: t.Optional[t.Union[t.Dict[str, t.Any], t.List[t.Any]]]
        root: str = chain[i]

        if root == "[]" and options.parse_lists:
            if options.allow_empty_lists and (leaf == "" or (options.strict_null_handling and leaf is None)):
                obj = []
            else:
                obj = list(leaf) if isinstance(leaf, (list, tuple)) else [leaf]
        else:
            obj = dict()

            # Optionally treat `%2E` as a literal dot (when `decode_dot_in_keys` is enabled).
            clean_root: str = root[1:-1] if root.startswith("[") and root.endswith("]") else root

            if options.decode_dot_in_keys:
                decoded_root: str = clean_root.replace("%2E", ".").replace("%2e", ".")
            else:
                decoded_root = clean_root

            # Parse numeric segment to decide between dict key vs. list index.
            index: t.Optional[int]
            try:
                index = int(decoded_root, 10)
            except (ValueError, TypeError):
                index = None

            if not options.parse_lists and decoded_root == "":
                obj = {"0": leaf}
            elif (
                index is not None
                and index >= 0
                and root != decoded_root
                and str(index) == decoded_root
                and options.parse_lists
                and index <= options.list_limit
            ):
                obj = [Undefined() for _ in range(index + 1)]
                obj[index] = leaf
            else:
                obj[str(index) if index is not None else decoded_root] = leaf

        leaf = obj

    return leaf


def _parse_keys(given_key: t.Optional[str], val: t.Any, options: DecodeOptions, values_parsed: bool) -> t.Any:
    """Split a full key string into segments and dispatch to ``_parse_object``.

    Returns ``None`` for empty keys (mirrors upstream behavior).
    """
    if not given_key:
        return None

    keys: t.List[str] = DecodeUtils.split_key_into_segments(
        original_key=given_key,
        allow_dots=options.allow_dots,
        max_depth=options.depth,
        strict_depth=options.strict_depth,
    )

    return _parse_object(keys, val, options, values_parsed)
