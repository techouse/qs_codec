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

from __future__ import annotations

import re
import typing as t
from collections.abc import Mapping
from math import isinf

from .enums.charset import Charset
from .enums.decode_kind import DecodeKind
from .enums.duplicates import Duplicates
from .enums.sentinel import Sentinel
from .models.decode_options import DecodeOptions
from .models.overflow_dict import OverflowDict
from .models.structured_key_scan import StructuredKeyScan
from .models.undefined import UNDEFINED
from .utils.decode_utils import DecodeUtils
from .utils.utils import Utils


def pure_decode(
    value: t.Optional[t.Union[str, Mapping[str, t.Any]]],
    options: t.Optional[DecodeOptions] = None,
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

    if not isinstance(value, (str, Mapping)):
        raise ValueError("value must be a str or a Mapping[str, Any]")

    opts = options if options is not None else DecodeOptions()
    decode_from_string = isinstance(value, str)
    str_value: str = t.cast(str, value) if decode_from_string else ""
    mapping_value: t.Mapping[str, t.Any] = t.cast(t.Mapping[str, t.Any], value) if not decode_from_string else {}

    parse_lists_effective = opts.parse_lists
    if decode_from_string and parse_lists_effective:
        # Keep caller options immutable: compute a local parse_lists switch only for this invocation.
        query = str_value.replace("?", "", 1) if opts.ignore_query_prefix else str_value
        if isinstance(opts.delimiter, re.Pattern):
            parts_count = len(re.split(opts.delimiter, query)) if query else 0
        else:
            parts_count = (query.count(opts.delimiter) + 1) if query else 0
        if 0 < opts.list_limit < parts_count:
            parse_lists_effective = False

    if decode_from_string:
        temp_obj: t.Optional[t.Dict[str, t.Any]] = _parse_query_string_values(
            str_value, opts, parse_lists=parse_lists_effective
        )
    else:
        temp_obj = dict(mapping_value)
    if not temp_obj:
        return obj

    structured_scan = _scan_structured_keys(temp_obj, opts) if decode_from_string else StructuredKeyScan.empty()
    if decode_from_string and not structured_scan.has_any_structured_syntax:
        return Utils.compact(temp_obj)

    # Iterate over the keys and setup the new object
    for key, val in temp_obj.items():
        if (
            decode_from_string
            and key not in structured_scan.structured_keys
            and key not in structured_scan.structured_roots
        ):
            # Fast path for flat keys: direct assignment when safe.
            # If a structured key already materialized the same key, preserve
            # historical merge semantics instead of overwriting.
            if key in obj:
                obj = Utils.merge(obj, {key: val}, opts)  # type: ignore [assignment]
            else:
                obj[key] = val
            continue

        new_obj: t.Any = _parse_keys(key, val, opts, decode_from_string, parse_lists=parse_lists_effective)

        if not obj and isinstance(new_obj, dict):
            obj = new_obj
            continue

        obj = Utils.merge(obj, new_obj, opts)  # type: ignore [assignment]

    return Utils.compact(obj)


# Alias for the pure implementation.
pure_load = pure_decode


def decode(
    value: t.Optional[t.Union[str, Mapping[str, t.Any]]],
    options: t.Optional[DecodeOptions] = None,
) -> t.Dict[str, t.Any]:
    """Dispatch to the configured backend while preserving the public API."""
    from ._backend import resolve_backend  # pylint: disable=import-outside-toplevel

    selection = resolve_backend()
    if selection.name == "pure":
        return pure_decode(value, options)

    from ._decode_rust import decode_with_rust  # pylint: disable=import-outside-toplevel

    return decode_with_rust(selection.native_module, value, options)


# Alias for decode function
load = decode


def loads(value: t.Optional[str], options: t.Optional[DecodeOptions] = None) -> t.Dict[str, t.Any]:
    """
    Alias for ``decode``. Decodes a query string into a ``Dict[str, Any]``.

    Use ``decode`` if you want to pass a ``Dict[str, Any]``.
    """
    return decode(value, options)


def _first_structured_split_index(key: str, allow_dots: bool) -> int:
    """Return the earliest index that indicates structured syntax in ``key``."""
    split_at = key.find("[")
    if not allow_dots:
        return split_at

    dot_index = key.find(".")
    if dot_index >= 0 and (split_at < 0 or dot_index < split_at):
        split_at = dot_index

    encoded_dot_index = -1
    if "%" in key:
        upper = key.find("%2E")
        lower = key.find("%2e")
        if upper >= 0 and lower >= 0:
            encoded_dot_index = upper if upper < lower else lower
        else:
            encoded_dot_index = upper if upper >= 0 else lower

    if encoded_dot_index >= 0 and (split_at < 0 or encoded_dot_index < split_at):
        split_at = encoded_dot_index

    return split_at


def _leading_structured_root(key: str, options: DecodeOptions) -> str:
    """Extract root key for leading-bracket structured keys (``[]`` normalizes to ``"0"``)."""
    segments = DecodeUtils.split_key_into_segments(
        original_key=key,
        allow_dots=t.cast(bool, options.allow_dots),
        max_depth=options.depth,
        strict_depth=options.strict_depth,
    )
    if not segments:
        return key

    first = segments[0]
    if not first.startswith("["):
        return first

    last = first.rfind("]")
    clean_root = first[1:last] if last > 0 else first[1:]
    return clean_root or "0"


def _scan_structured_keys(temp_obj: Mapping[str, t.Any], options: DecodeOptions) -> StructuredKeyScan:
    """Pre-scan keys to enable flat-query and mixed-query decode bypasses."""
    if not temp_obj:
        return StructuredKeyScan.empty()

    allow_dots = t.cast(bool, options.allow_dots)
    structured_roots: t.Set[str] = set()
    structured_keys: t.Set[str] = set()

    for key in temp_obj.keys():
        split_at = _first_structured_split_index(key, allow_dots)
        if split_at < 0:
            continue
        structured_keys.add(key)
        if split_at == 0:
            structured_roots.add(_leading_structured_root(key, options))
        else:
            structured_roots.add(key[:split_at])

    if not structured_keys:
        return StructuredKeyScan.empty()

    return StructuredKeyScan(
        has_any_structured_syntax=True,
        structured_roots=frozenset(structured_roots),
        structured_keys=frozenset(structured_keys),
    )


def _interpret_numeric_entities(value: str) -> str:
    """Convert HTML numeric entities (e.g., ``&#169;``) to their character equivalents.

    Only used when ``options.interpret_numeric_entities`` is True and the effective charset
    is Latin-1; see the Node `qs` compatibility behavior.
    """
    return re.sub(r"&#(\d+);", lambda match: chr(int(match.group(1))), value)


def _parse_array_value(value: t.Any, options: DecodeOptions, current_list_length: int) -> t.Any:
    """Post-process a raw scalar for list semantics and enforce ``list_limit``.

    Behavior
    --------
    - If ``comma=True`` and ``value`` is a string that contains commas, split into a list.
    - Otherwise, enforce the per-list length limit by comparing ``current_list_length`` to ``options.list_limit``.
      When ``raise_on_limit_exceeded=True``, violations raise ``ValueError``.
    - When ``list_limit`` is negative:
        * if ``raise_on_limit_exceeded=True``, **any** list-growth operation here (e.g., comma-splitting)
          raises immediately;
        * if ``raise_on_limit_exceeded=False`` (default), comma-splitting still returns a list; numeric
          bracket indices are handled later by ``_parse_object`` (where negative ``list_limit`` disables
          numeric-index parsing only).

    Returns
    -------
    Any
        Either the original value or a list of values, without decoding (that happens later).
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


def _parse_query_string_values(
    value: str, options: DecodeOptions, *, parse_lists: t.Optional[bool] = None
) -> t.Dict[str, t.Any]:
    """Tokenize a raw query string into a flat ``Dict[str, Any]``.

    Responsibilities
    ----------------
    - Strip a leading '?' if ``ignore_query_prefix`` is True.
    - Normalize percent-encoded square brackets (``%5B/%5D``) (case-insensitive) so the key splitter can operate.
    - Split into parts using either a string delimiter or a regex delimiter.
    - Enforce ``parameter_limit`` (optionally raising).
    - Detect the UTF-8/Latin-1 charset via the ``utf8=…`` sentinel when enabled.
    - For each ``key=value`` pair:
        * Decode key/value via ``options.decoder`` (default: percent-decoding using the selected ``charset``).
          Keys are passed with ``kind=DecodeKind.KEY`` and values with ``kind=DecodeKind.VALUE``; a custom decoder
          may return the raw token or ``None``.
        * Apply comma-split list logic to values (handled here). Index-based list growth from bracket segments is applied later in ``_parse_object``. When ``list_limit < 0`` and ``raise_on_limit_exceeded=True``, any comma-split that would increase the list length raises immediately; otherwise the split proceeds.
        * Interpret numeric entities for Latin-1 when requested.
        * Handle empty brackets ``[]`` as list markers (wrapping exactly once).
        * Merge duplicate keys according to ``duplicates`` policy.

    The output is a *flat* dict (keys are full key-path strings). Higher-level structure is constructed later by
    ``_parse_keys`` / ``_parse_object``.
    """
    obj: t.Dict[str, t.Any] = {}
    parse_lists_enabled = options.parse_lists if parse_lists is None else parse_lists

    clean_str: str = value.replace("?", "", 1) if options.ignore_query_prefix else value
    # Normalize %5B/%5D to literal brackets before splitting (case-insensitive).
    # Note: this operates on the entire query string (keys *and* values). That’s
    # intentional: it keeps the splitter simple, and value tokens are subsequently
    # passed through the scalar decoder, so this replacement is safe.
    clean_str = clean_str.replace("%5B", "[").replace("%5b", "[").replace("%5D", "]").replace("%5d", "]")

    # Compute an effective parameter limit (None means "no limit").
    limit: t.Optional[int] = None if isinf(options.parameter_limit) else options.parameter_limit  # type: ignore [assignment]

    # Guard against non-positive limits early for clearer errors.
    if limit is not None and limit <= 0:
        raise ValueError("Parameter limit must be a positive integer.")

    parts: t.List[str]
    if limit is None:
        # Unlimited parameters: split fully
        if isinstance(options.delimiter, re.Pattern):
            parts = re.split(options.delimiter, clean_str)
        else:
            parts = clean_str.split(options.delimiter)
    else:
        if options.raise_on_limit_exceeded:
            # Split to at most limit+1 parts so we can detect overflow
            if isinstance(options.delimiter, re.Pattern):
                parts = re.split(options.delimiter, clean_str, maxsplit=limit)
            else:
                parts = clean_str.split(options.delimiter, limit)
            if len(parts) > limit:
                raise ValueError(
                    f"Parameter limit exceeded: Only {limit} parameter{'s' if limit != 1 else ''} allowed."
                )
        else:
            # Silent degrade: split fully, then take the first `limit` parts
            if isinstance(options.delimiter, re.Pattern):
                parts = re.split(options.delimiter, clean_str)
            else:
                parts = clean_str.split(options.delimiter)
            parts = parts[:limit]

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

    # Local, non-optional decoder reference for type-checkers
    decoder_fn: t.Callable[..., t.Optional[str]] = options.decoder or DecodeUtils.decode
    duplicates = options.duplicates

    # Iterate over parts and decode each key/value pair.
    for i, _ in enumerate(parts):
        if i == skip_index:
            continue

        part: str = parts[i]
        if not part:
            continue
        bracket_equals_pos: int = part.find("]=")
        pos: int = part.find("=") if bracket_equals_pos == -1 else (bracket_equals_pos + 1)

        # Decode key and value with a key-aware decoder; skip pairs whose key decodes to None
        raw_key = ""
        if pos == -1:
            key_decoded = decoder_fn(part, charset, kind=DecodeKind.KEY)
            if key_decoded is None:
                continue
            key: str = key_decoded
            if not key:
                continue
            val: t.Any = None if options.strict_null_handling else ""
        else:
            raw_key = part[:pos]
            key_decoded = decoder_fn(raw_key, charset, kind=DecodeKind.KEY)
            if key_decoded is None:
                continue
            key = key_decoded
            if not key:
                continue
            parsed_value = _parse_array_value(
                part[pos + 1 :],
                options,
                len(obj[key]) if key in obj and isinstance(obj[key], (list, tuple)) else 0,
            )
            if isinstance(parsed_value, (list, tuple)):
                val = [decoder_fn(v, charset, kind=DecodeKind.VALUE) for v in parsed_value]
            else:
                val = decoder_fn(parsed_value, charset, kind=DecodeKind.VALUE)

        if val and options.interpret_numeric_entities and charset == Charset.LATIN1:
            val = _interpret_numeric_entities(
                val if isinstance(val, str) else ",".join(val) if isinstance(val, (list, tuple)) else str(val)
            )

        # Upstream parity: if token contains "[]=", only wrap values that are already arrays
        # (typically produced by comma splitting), preserving list-of-lists semantics.
        if parse_lists_enabled and pos != -1 and "[]=" in part and isinstance(val, (list, tuple)):
            val = [val]

        existing: bool = key in obj

        # Combine/overwrite according to the configured duplicates policy.
        if existing and duplicates == Duplicates.COMBINE:
            obj[key] = Utils.combine(obj[key], val, options)
        elif not existing or duplicates == Duplicates.LAST:
            obj[key] = val

    return obj


def _parse_object(
    chain: t.Union[t.List[str], t.Tuple[str, ...]],
    val: t.Any,
    options: DecodeOptions,
    values_parsed: bool,
    *,
    parse_lists: t.Optional[bool] = None,
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
    - Converts bracketed **numeric** segments into list indices when allowed and within ``list_limit``.
    - When ``list_limit`` is negative, **numeric-indexed bracket segments** are treated as map keys
      (i.e., index-based list growth is disabled). Empty brackets (``[]``) still create lists unless
      ``raise_on_limit_exceeded`` is True; with ``raise_on_limit_exceeded=True``, any list-growth operation
      (empty brackets, comma-split, nested pushes) raises immediately.
    - Inside bracket segments, a custom key decoder may leave percent-encoded dots (``%2E/%2e``). When
      ``decode_dot_in_keys`` is True, these are normalized to ``.`` here. Top-level dot splitting is already
      handled by the splitter.
    - When list parsing is disabled and an empty segment is encountered, coerces to ``{"0": leaf}`` to preserve round-trippability with other ports.
    """
    parse_lists_enabled = options.parse_lists if parse_lists is None else parse_lists
    current_list_length: int = 0

    # If the chain ends with an empty list marker, compute current list length for limit checks.
    # Best-effort note:
    #   This is a conservative heuristic intended to help when we see patterns like `a[0][]=`,
    #   so `_parse_array_value` can enforce the list limit for the final `[]` push. The segments
    #   we receive in `chain` include bracket markers (e.g., `["a", "[0]", "[]"]`), so
    #   `"".join(chain[:-1])` is rarely a pure integer (e.g., `"a[0]"` raises `ValueError`),
    #   and we typically fall back to `0`. That’s fine: it remains safe and conservative.
    #   We still:
    #     • enforce per-list length for already-allocated containers during tokenization in
    #       `_parse_query_string_values` (where we know the current length), and
    #     • enforce index-based growth limits inside this function when converting bracketed
    #       numeric segments into list indices.
    #   Keeping this lightweight probe matches the other ports and avoids costly look-ahead into
    #   parent structures while maintaining correct limit behavior.
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

        if root == "[]" and parse_lists_enabled:
            if Utils.is_overflow(leaf):
                obj = leaf
            elif options.allow_empty_lists and (leaf == "" or (options.strict_null_handling and leaf is None)):
                obj = []
            else:
                obj = list(leaf) if isinstance(leaf, (list, tuple)) else [leaf]
                if options.list_limit is not None and len(obj) > options.list_limit:
                    obj = OverflowDict({str(i): x for i, x in enumerate(obj)})
        else:
            obj = dict()

            # Map `%2E`/`%2e` to a literal dot *inside bracket segments* when
            # `decode_dot_in_keys` is enabled. Even though `_parse_query_string_values`
            # typically percent-decodes the key (default decoder), a custom
            # `DecodeOptions.decoder` may return the raw token. In that case, `%2E` can
            # still appear here and must be normalized for parity with the Kotlin/C#/Swift/Dart ports.
            # (Top-level dot splitting is performed earlier by the key splitter.)
            clean_root: str = root[1:-1] if root.startswith("[") and root.endswith("]") else root

            if options.decode_dot_in_keys and "%2" in clean_root:
                decoded_root: str = clean_root.replace("%2E", ".").replace("%2e", ".")
            else:
                decoded_root = clean_root

            # Parse numeric segment to decide between dict key vs. list index.
            index: t.Optional[int]
            try:
                index = int(decoded_root, 10)
            except (ValueError, TypeError):
                index = None

            if not parse_lists_enabled and decoded_root == "":
                if Utils.is_overflow(leaf):
                    obj = leaf
                else:
                    obj = {"0": leaf}
            elif (
                index is not None
                and index >= 0
                and root != decoded_root
                and str(index) == decoded_root
                and parse_lists_enabled
                and index <= options.list_limit
            ):
                obj = [UNDEFINED for _ in range(index + 1)]
                obj[index] = leaf
            else:
                # Preserve the literal decoded key for non-array roots (e.g. "[01]" -> "01"),
                # matching Node `qs` behavior for leading-zero numeric-like segments.
                obj[decoded_root] = leaf

        leaf = obj

    return leaf


def _parse_keys(
    given_key: t.Optional[str],
    val: t.Any,
    options: DecodeOptions,
    values_parsed: bool,
    *,
    parse_lists: t.Optional[bool] = None,
) -> t.Any:
    """Split a full key string into segments and dispatch to ``_parse_object``.

    Returns ``None`` for empty keys (mirrors upstream behavior).
    """
    if not given_key:
        return None

    keys: t.List[str] = DecodeUtils.split_key_into_segments(
        original_key=given_key,
        allow_dots=t.cast(bool, options.allow_dots),
        max_depth=options.depth,
        strict_depth=options.strict_depth,
    )

    return _parse_object(keys, val, options, values_parsed, parse_lists=parse_lists)
