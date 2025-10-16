"""Query‑string *encoder* (stringifier).

This module converts Python mappings and sequences into a percent‑encoded query string with feature parity to the
Node.js `qs` package where it makes sense for Python. It supports:

- Stable, deterministic key ordering with an optional custom comparator.
- Multiple list encodings (indices, brackets, repeat key, comma) including the "comma round‑trip" behavior to preserve single‑element lists.
- Custom per‑scalar encoder and `datetime` serializer hooks.
- RFC 3986 vs RFC 1738 formatting and optional charset sentinels.
- Dots vs brackets in key paths (`allow_dots`, `encode_dot_in_keys`).
- Strict/null handling, empty‑list emission, and cycle detection.

Nothing in this module mutates caller objects: inputs are shallow‑normalized and deep‑copied only where safe/necessary to honor options.
"""

import typing as t
from copy import deepcopy
from datetime import datetime
from functools import cmp_to_key
from weakref import WeakKeyDictionary

from .enums.charset import Charset
from .enums.format import Format
from .enums.list_format import ListFormat
from .enums.sentinel import Sentinel
from .models.encode_options import EncodeOptions
from .models.undefined import UNDEFINED, Undefined
from .models.weak_wrapper import WeakWrapper
from .utils.utils import Utils


def encode(value: t.Any, options: EncodeOptions = EncodeOptions()) -> str:
    """
    Stringify a Python value into a query string.

    Args:
        value: The object to encode. Accepted shapes:
            * Mapping -> encoded as-is.
            * Sequence (list/tuple) -> treated as an object with string indices.
            * Other/None -> treated as empty input.
        options: Encoding behavior (parity with the Node.js `qs` API).

    Returns:
        The encoded query string (possibly prefixed with "?" if requested), or an empty string when there is nothing to encode.

    Notes:
        - Caller input is not mutated. When a mapping is provided it is deep-copied; sequences are projected to a temporary mapping.
        - If a callable `filter` is provided, it can transform the root object.
        - If an iterable filter is provided, it selects which *root* keys to emit.
    """
    # Treat `None` as "nothing to encode".
    if value is None:
        return ""

    # Normalize the root into a mapping we can traverse deterministically:
    # - Mapping  -> deepcopy (avoid mutating caller containers)
    # - Sequence -> promote to {"0": v0, "1": v1, ...}
    # - Other    -> empty (encodes to "")
    obj: t.Mapping[str, t.Any]
    if isinstance(value, t.Mapping):
        obj = deepcopy(value)
    elif isinstance(value, (list, tuple)):
        obj = {str(i): item for i, item in enumerate(value)}
    else:
        obj = {}

    # Early exit if there's nothing to emit.
    if not obj:
        return ""

    keys: t.List[str] = []

    # If an iterable filter is provided for the root, restrict emission to those keys.
    obj_keys: t.Optional[t.List[t.Any]] = None
    if options.filter is not None:
        if callable(options.filter):
            # Callable filter may transform the root object.
            obj = options.filter("", obj)
        elif isinstance(options.filter, (list, tuple)):
            obj_keys = list(options.filter)

    # Single-item list round-trip marker when using comma format.
    comma_round_trip: bool = options.list_format == ListFormat.COMMA and options.comma_round_trip is True

    # Default root key set if no iterable filter was provided.
    if obj_keys is None:
        obj_keys = list(obj.keys())

    # Deterministic ordering via user-supplied comparator (if any).
    if options.sort is not None and callable(options.sort):
        obj_keys = sorted(obj_keys, key=cmp_to_key(options.sort))

    # Side channel for cycle detection across recursive calls.
    side_channel: WeakKeyDictionary = WeakKeyDictionary()

    # Encode each selected root key.
    for _key in obj_keys:
        if not isinstance(_key, str):
            # Skip non-string keys; parity with ports that stringify key paths.
            continue
        # Optionally drop explicit nulls at the root.
        if _key in obj and obj.get(_key) is None and options.skip_nulls:
            continue

        _encoded: t.Union[t.List[t.Any], t.Tuple[t.Any, ...], t.Any] = _encode(
            value=obj.get(_key),
            is_undefined=_key not in obj,
            side_channel=side_channel,
            prefix=_key,
            generate_array_prefix=options.list_format.generator,
            comma_round_trip=comma_round_trip,
            comma_compact_nulls=options.list_format == ListFormat.COMMA and options.comma_compact_nulls,
            encoder=options.encoder if options.encode else None,
            serialize_date=options.serialize_date,
            sort=options.sort,
            filter=options.filter,
            formatter=options.format.formatter,
            allow_empty_lists=options.allow_empty_lists,
            strict_null_handling=options.strict_null_handling,
            skip_nulls=options.skip_nulls,
            encode_dot_in_keys=options.encode_dot_in_keys,
            allow_dots=options.allow_dots,
            format=options.format,
            encode_values_only=options.encode_values_only,
            charset=options.charset,
            add_query_prefix=options.add_query_prefix,
        )

        # `_encode` yields either a flat list of `key=value` tokens or a single token.
        if isinstance(_encoded, (list, tuple)):
            keys.extend(_encoded)
        else:
            keys.append(_encoded)

    # Join tokens with the selected pair delimiter.
    joined: str = options.delimiter.join(keys)

    # Optional leading "?" prefix (applied *before* a charset sentinel, if any).
    prefix: str = "?" if options.add_query_prefix else ""

    # Optional charset sentinel token for downstream parsers (e.g., "utf-8" or "iso-8859-1").
    if options.charset_sentinel:
        if options.charset == Charset.LATIN1:
            prefix += f"{Sentinel.ISO.encoded}&"
        elif options.charset == Charset.UTF8:
            prefix += f"{Sentinel.CHARSET.encoded}&"
        else:
            raise ValueError("Invalid charset")

    return prefix + joined if joined else ""


# Alias for the `encode` function.
dumps = encode  # public alias (parity with `json.dumps` / Node `qs.stringify`)

# Unique placeholder used as a key within the side-channel chain to pass context down recursion.
_sentinel: WeakWrapper = WeakWrapper({})


def _encode(
    value: t.Any,
    is_undefined: bool,
    side_channel: WeakKeyDictionary,
    prefix: t.Optional[str],
    comma_round_trip: t.Optional[bool],
    comma_compact_nulls: bool,
    encoder: t.Optional[t.Callable[[t.Any, t.Optional[Charset], t.Optional[Format]], str]],
    serialize_date: t.Callable[[datetime], t.Optional[str]],
    sort: t.Optional[t.Callable[[t.Any, t.Any], int]],
    filter: t.Optional[t.Union[t.Callable, t.List[t.Union[str, int]]]],
    formatter: t.Optional[t.Callable[[str], str]],
    format: Format = Format.RFC3986,
    generate_array_prefix: t.Callable[[str, t.Optional[str]], str] = ListFormat.INDICES.generator,
    allow_empty_lists: bool = False,
    strict_null_handling: bool = False,
    skip_nulls: bool = False,
    encode_dot_in_keys: bool = False,
    allow_dots: bool = False,
    encode_values_only: bool = False,
    charset: t.Optional[Charset] = Charset.UTF8,
    add_query_prefix: bool = False,
) -> t.Union[t.List[t.Any], t.Tuple[t.Any, ...], t.Any]:
    """
    Recursive worker that produces `key=value` tokens for a single subtree.

    This function returns either:
      * a list/tuple of tokens (strings) to be appended to the parent list, or
      * a single token string (when a scalar is reached).

    It threads a *side-channel* (a chained `WeakKeyDictionary`) through recursion to detect cycles by remembering where each visited object last appeared.

    Args:
        value: Current subtree value.
        is_undefined: Whether the current key was absent in the parent mapping.
        side_channel: Cycle-detection chain; child frames point to their parent via `_sentinel`.
        prefix: The key path accumulated so far (unencoded except for dot-encoding when requested).
        comma_round_trip: Whether a single-element list should emit `[]` to ensure round-trip with comma format.
        comma_compact_nulls: When True (and using comma list format), drop `None` entries before joining.
        encoder: Custom per-scalar encoder; if None, falls back to `str(value)` for primitives.
        serialize_date: Optional `datetime` serializer hook.
        sort: Optional comparator for object/array key ordering.
        filter: Callable (transform value) or iterable of keys/indices (select).
        formatter: Percent-escape function chosen by `format` (RFC3986/1738).
        format: Format enum (only used to choose a default `formatter` if none provided).
        generate_array_prefix: Strategy used to build array key segments (indices/brackets/repeat/comma).
        allow_empty_lists: Emit `[]` for empty lists if True.
        strict_null_handling: If True, emit bare keys for nulls (no `=`).
        skip_nulls: If True, drop nulls entirely.
        encode_dot_in_keys: Percent-encode literal '.' in key names.
        allow_dots: Use dot notation for nested objects instead of brackets.
        encode_values_only: If True, do not encode key names (only values).
        charset: The charset hint passed to `encoder`.
        add_query_prefix: Whether the top-level caller requested a leading '?'.

    Returns:
        Either a list/tuple of tokens or a single token string.
    """
    # Establish a starting prefix for the top-most invocation (used when called directly).
    if prefix is None:
        prefix = "?" if add_query_prefix else ""

    # Infer comma round-trip when using the COMMA generator and the flag was not explicitly provided.
    if comma_round_trip is None:
        comma_round_trip = generate_array_prefix is ListFormat.COMMA.generator

    # Choose a formatter if one wasn't provided (based on the selected format).
    if formatter is None:
        formatter = format.formatter

    # Work with the original; we never mutate in place (we build new lists/maps when normalizing).
    obj: t.Any = value

    # --- Cycle detection via chained side-channel -----------------------------------------
    obj_wrapper: WeakWrapper = WeakWrapper(value)
    tmp_sc: t.Optional[WeakKeyDictionary] = side_channel
    step: int = 0
    find_flag: bool = False

    # Walk up the chain looking for `obj_wrapper`. If we see it at the same "step"
    # again we've closed a loop.
    while (tmp_sc := tmp_sc.get(_sentinel)) and not find_flag:  # type: ignore [union-attr]
        # Where `value` last appeared in the ref tree
        pos: t.Optional[int] = tmp_sc.get(obj_wrapper)
        step += 1
        if pos is not None:
            if pos == step:
                raise ValueError("Circular reference detected")
            else:
                find_flag = True  # Break while
        if tmp_sc.get(_sentinel) is None:
            step = 0

    # --- Pre-processing: filter & datetime handling ---------------------------------------
    if callable(filter):
        # Callable filter can transform the object for this prefix.
        obj = filter(prefix, obj)
    else:
        # Normalize datetimes both for scalars and (in COMMA mode) list elements.
        if isinstance(obj, datetime):
            obj = serialize_date(obj) if callable(serialize_date) else obj.isoformat()
        elif generate_array_prefix is ListFormat.COMMA.generator and isinstance(obj, (list, tuple)):
            if callable(serialize_date):
                obj = [serialize_date(x) if isinstance(x, datetime) else x for x in obj]
            else:
                obj = [x.isoformat() if isinstance(x, datetime) else x for x in obj]

    # --- Null handling --------------------------------------------------------------------
    if not is_undefined and obj is None:
        if strict_null_handling:
            # Bare key (no '=value') when strict handling is requested.
            return encoder(prefix, charset, format) if callable(encoder) and not encode_values_only else prefix
        # Otherwise treat `None` as empty string.
        obj = ""

    # --- Fast path for primitives/bytes ---------------------------------------------------
    if Utils.is_non_nullish_primitive(obj, skip_nulls) or isinstance(obj, bytes):
        # When a custom encoder is provided, still coerce Python bools to lowercase JSON style
        if callable(encoder):
            key_value = prefix if encode_values_only else encoder(prefix, charset, format)
            if isinstance(obj, bool):
                value_part = "true" if obj else "false"
            else:
                value_part = encoder(obj, charset, format)
            return [f"{formatter(key_value)}={formatter(value_part)}"]
        # Default fallback (no custom encoder): ensure lowercase boolean literals
        if isinstance(obj, bool):
            value_str = "true" if obj else "false"
        else:
            value_str = str(obj)
        return [f"{formatter(prefix)}={formatter(value_str)}"]

    values: t.List[t.Any] = []

    # If the *key itself* was undefined (not present in the parent), there is nothing to emit.
    if is_undefined:
        return values

    # --- Determine which keys/indices to traverse ----------------------------------------
    comma_effective_length: t.Optional[int] = None
    obj_keys: t.List[t.Any]
    if generate_array_prefix == ListFormat.COMMA.generator and isinstance(obj, (list, tuple)):
        # In COMMA mode we join the elements into a single token at this level.
        comma_items: t.List[t.Any] = list(obj)
        if comma_compact_nulls:
            comma_items = [item for item in comma_items if item is not None]
        comma_effective_length = len(comma_items)

        if encode_values_only and callable(encoder):
            encoded_items = Utils.apply(comma_items, encoder)
            obj_keys_value = ",".join(("" if e is None else str(e)) for e in encoded_items)
        else:
            obj_keys_value = ",".join(Utils.normalize_comma_elem(e) for e in comma_items)

        if comma_items:
            obj_keys = [{"value": obj_keys_value if obj_keys_value else None}]
        else:
            obj_keys = [{"value": UNDEFINED}]
    elif isinstance(filter, (list, tuple)):
        # Iterable filter restricts traversal to a fixed key/index set.
        obj_keys = list(filter)
    else:
        # Default: enumerate keys/indices from mappings or sequences.
        if isinstance(obj, t.Mapping):
            keys = list(obj.keys())
        elif isinstance(obj, (list, tuple)):
            keys = list(range(len(obj)))
        else:
            keys = []
        obj_keys = sorted(keys, key=cmp_to_key(sort)) if sort is not None else keys

    # Percent-encode literal dots in key names when requested.
    encoded_prefix: str = prefix.replace(".", "%2E") if encode_dot_in_keys else prefix

    # In comma round-trip mode, ensure a single-element list appends `[]` to preserve type on decode.
    single_item_for_round_trip: bool = False
    if comma_round_trip and isinstance(obj, (list, tuple)):
        if generate_array_prefix == ListFormat.COMMA.generator and comma_effective_length is not None:
            single_item_for_round_trip = comma_effective_length == 1
        else:
            single_item_for_round_trip = len(obj) == 1
    adjusted_prefix: str = f"{encoded_prefix}[]" if single_item_for_round_trip else encoded_prefix

    # Optionally emit empty lists as `key[]=`.
    if allow_empty_lists and isinstance(obj, (list, tuple)) and not obj:
        return [f"{adjusted_prefix}[]"]

    # --- Recurse for each child -----------------------------------------------------------
    for _key in obj_keys:
        # Resolve the child value and whether it was "undefined" at this level.
        _value: t.Any
        _value_undefined: bool
        if isinstance(_key, t.Mapping) and "value" in _key and not isinstance(_key.get("value"), Undefined):
            _value = _key.get("value")
            _value_undefined = False
        else:
            try:
                if isinstance(obj, t.Mapping):
                    _value = obj.get(_key)
                    _value_undefined = _key not in obj
                elif isinstance(obj, (list, tuple)):
                    _value = obj[_key]
                    _value_undefined = False
                else:
                    _value = obj[_key]
                    _value_undefined = False
            except Exception:  # pylint: disable=W0718
                _value = None
                _value_undefined = True

        # Optionally drop null children.
        if skip_nulls and _value is None:
            continue

        # When using dotted paths and also encoding dots in keys, percent-escape '.' inside key names.
        encoded_key: str = str(_key).replace(".", "%2E") if allow_dots and encode_dot_in_keys else str(_key)

        # Build the child key path depending on whether we're traversing a list or a mapping.
        key_prefix: str = (
            generate_array_prefix(adjusted_prefix, encoded_key)
            if isinstance(obj, (list, tuple))
            else f"{adjusted_prefix}{f'.{encoded_key}' if allow_dots else f'[{encoded_key}]'}"
        )

        # Update side-channel for the child call and thread the parent channel via `_sentinel`.
        side_channel[obj_wrapper] = step
        value_side_channel: WeakKeyDictionary = WeakKeyDictionary()
        value_side_channel[_sentinel] = side_channel

        # Recurse into the child.
        encoded: t.Union[t.List[t.Any], t.Tuple[t.Any, ...], t.Any] = _encode(
            value=_value,
            is_undefined=_value_undefined,
            side_channel=value_side_channel,
            prefix=key_prefix,
            comma_round_trip=comma_round_trip,
            comma_compact_nulls=comma_compact_nulls,
            encoder=(
                None
                if generate_array_prefix is ListFormat.COMMA.generator
                and encode_values_only
                and isinstance(obj, (list, tuple))
                else encoder
            ),
            serialize_date=serialize_date,
            sort=sort,
            filter=filter,
            formatter=formatter,
            format=format,
            generate_array_prefix=generate_array_prefix,
            allow_empty_lists=allow_empty_lists,
            strict_null_handling=strict_null_handling,
            skip_nulls=skip_nulls,
            encode_dot_in_keys=encode_dot_in_keys,
            allow_dots=allow_dots,
            encode_values_only=encode_values_only,
            charset=charset,
        )

        # Flatten nested results into the `values` list.
        if isinstance(encoded, (list, tuple)):
            values.extend(encoded)
        else:
            values.append(encoded)

    return values
