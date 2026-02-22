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

import sys
import typing as t
from collections.abc import Sequence as ABCSequence
from copy import deepcopy
from dataclasses import dataclass, field
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
        - Caller input is not mutated. When a mapping is provided it is shallow-copied (deep-copied only when a callable
          filter is used); sequences are projected to a temporary mapping.
        - If a callable `filter` is provided, it can transform the root object.
        - If an iterable filter is provided, it selects which *root* keys to emit.
    """
    # Treat `None` as "nothing to encode".
    if value is None:
        return ""

    filter_opt = options.filter

    # Normalize the root into a mapping we can traverse deterministically:
    # - Mapping  -> shallow copy (deep-copy only when a callable filter may mutate)
    # - Sequence -> promote to {"0": v0, "1": v1, ...}
    # - Other    -> empty (encodes to "")
    obj: t.Mapping[str, t.Any]
    if isinstance(value, t.Mapping):
        obj = deepcopy(value) if callable(filter_opt) else dict(value)
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
    if filter_opt is not None:
        if callable(filter_opt):
            # Callable filter may transform the root object.
            obj = filter_opt("", obj)
        elif isinstance(filter_opt, ABCSequence) and not isinstance(filter_opt, (str, bytes, bytearray)):
            obj_keys = list(filter_opt)

    # Single-item list round-trip marker when using comma format.
    comma_round_trip: bool = options.list_format == ListFormat.COMMA and options.comma_round_trip is True

    # Default root key set if no iterable filter was provided.
    if obj_keys is None:
        obj_keys = list(obj.keys())

    # Deterministic ordering via user-supplied comparator (if any).
    if options.sort is not None and callable(options.sort):
        obj_keys = sorted(obj_keys, key=cmp_to_key(options.sort))

    # Side channel seed for legacy `_encode` compatibility (and cycle-state bootstrap when provided).
    side_channel: WeakKeyDictionary = WeakKeyDictionary()
    max_depth = _get_max_encode_depth(options.max_depth)

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
            filter_=options.filter,
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
            _max_depth=max_depth,
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
MAX_ENCODING_DEPTH_EXCEEDED = "Maximum encoding depth exceeded"


def _get_max_encode_depth(max_depth: t.Optional[int]) -> int:
    if max_depth is None:
        return sys.maxsize
    return max_depth


@dataclass
class _EncodeFrame:
    value: t.Any
    is_undefined: bool
    side_channel: WeakKeyDictionary
    prefix: t.Optional[str]
    comma_round_trip: t.Optional[bool]
    comma_compact_nulls: bool
    encoder: t.Optional[t.Callable[[t.Any, t.Optional[Charset], t.Optional[Format]], str]]
    serialize_date: t.Union[t.Callable[[datetime], t.Optional[str]], str]
    sort: t.Optional[t.Callable[[t.Any, t.Any], int]]
    filter_: t.Optional[t.Union[t.Callable, t.Sequence[t.Union[str, int]]]]
    formatter: t.Optional[t.Callable[[str], str]]
    format: Format
    generate_array_prefix: t.Callable[[str, t.Optional[str]], str]
    allow_empty_lists: bool
    strict_null_handling: bool
    skip_nulls: bool
    encode_dot_in_keys: bool
    allow_dots: bool
    encode_values_only: bool
    charset: t.Optional[Charset]
    add_query_prefix: bool
    depth: int
    max_depth: t.Optional[int]
    phase: str = "start"
    obj: t.Any = None
    obj_wrapper: t.Optional[WeakWrapper] = None
    step: int = 0
    obj_keys: t.List[t.Any] = field(default_factory=list)
    values: t.List[t.Any] = field(default_factory=list)
    index: int = 0
    adjusted_prefix: str = ""
    cycle_state: t.Optional["_CycleState"] = None
    cycle_level: t.Optional[int] = None
    cycle_pushed: bool = False


@dataclass
class _CycleEntry:
    level: int
    pos: t.Any
    is_top: bool


@dataclass
class _CycleState:
    entries: t.Dict[WeakWrapper, t.List[_CycleEntry]] = field(default_factory=dict)


def _bootstrap_cycle_state_from_side_channel(side_channel: WeakKeyDictionary) -> t.Tuple[_CycleState, int]:
    """
    Build O(1) ancestry lookup state from an existing side-channel chain.

    Returns:
        Tuple of (state, current_level), where current_level is the chain length
        from the current frame to the top-most side-channel mapping.
    """
    chain: t.List[WeakKeyDictionary] = []
    tmp_sc: t.Optional[WeakKeyDictionary] = side_channel.get(_sentinel)  # type: ignore[assignment]
    while tmp_sc is not None:
        chain.append(tmp_sc)
        tmp_sc = tmp_sc.get(_sentinel)  # type: ignore[assignment]

    state = _CycleState()
    for level, ancestor in enumerate(reversed(chain)):
        is_top = ancestor.get(_sentinel) is None
        for key, pos in ancestor.items():
            if key is _sentinel or not isinstance(key, WeakWrapper):
                continue
            state.entries.setdefault(key, []).append(_CycleEntry(level=level, pos=pos, is_top=is_top))

    return state, len(chain)


def _compute_step_and_check_cycle(state: _CycleState, wrapper: WeakWrapper, current_level: int) -> int:
    """
    Compute the current cycle-detection "step" and raise on circular reference.

    Semantics intentionally match the legacy side-channel chain scan:
      * nearest ancestor match wins
      * raise when ancestor_pos == distance
      * return 0 when no match or when nearest match is the top-most side-channel
    """
    entries = state.entries.get(wrapper)
    if not entries:
        return 0

    nearest = entries[-1]
    distance = current_level - nearest.level
    if nearest.pos == distance:
        raise ValueError("Circular reference detected")  # noqa: TRY003

    return 0 if nearest.is_top else distance


def _push_current_node(state: _CycleState, wrapper: WeakWrapper, current_level: int, pos: int, is_top: bool) -> None:
    state.entries.setdefault(wrapper, []).append(_CycleEntry(level=current_level, pos=pos, is_top=is_top))


def _pop_current_node(state: _CycleState, wrapper: WeakWrapper) -> None:
    entries = state.entries.get(wrapper)
    if not entries:
        return

    entries.pop()
    if not entries:
        del state.entries[wrapper]


def _encode(
    value: t.Any,
    is_undefined: bool,
    side_channel: WeakKeyDictionary,
    prefix: t.Optional[str],
    comma_round_trip: t.Optional[bool],
    comma_compact_nulls: bool,
    encoder: t.Optional[t.Callable[[t.Any, t.Optional[Charset], t.Optional[Format]], str]],
    serialize_date: t.Union[t.Callable[[datetime], t.Optional[str]], str],
    sort: t.Optional[t.Callable[[t.Any, t.Any], int]],
    filter_: t.Optional[t.Union[t.Callable, t.Sequence[t.Union[str, int]]]],
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
    _depth: int = 0,
    _max_depth: t.Optional[int] = None,
) -> t.Union[t.List[t.Any], t.Tuple[t.Any, ...], t.Any]:
    """
    Iterative worker that produces `key=value` tokens for a single subtree.

    This function returns either:
      * a list/tuple of tokens (strings) to be appended to the parent list, or
      * a single token string (when a scalar is reached).

    It uses an internal O(1) cycle-state map to detect cycles while preserving compatibility with legacy direct `_encode`
    callers that provide a chained side-channel via `_sentinel`.

    Args:
        value: Current subtree value.
        is_undefined: Whether the current key was absent in the parent mapping.
        side_channel: Legacy side-channel seed. If pre-seeded via `_sentinel`, it is bootstrapped once into cycle state.
        prefix: The key path accumulated so far (unencoded except for dot-encoding when requested).
        comma_round_trip: Whether a single-element list should emit `[]` to ensure round-trip with comma format.
        comma_compact_nulls: When True (and using comma list format), drop `None` entries before joining.
        encoder: Custom per-scalar encoder; if None, falls back to `str(value)` for primitives.
        serialize_date: Optional `datetime` serializer hook.
        sort: Optional comparator for object/array key ordering.
        filter_: Callable (transform value) or iterable of keys/indices (select).
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
    last_result: t.Union[t.List[t.Any], t.Tuple[t.Any, ...], t.Any, None] = None

    stack: t.List[_EncodeFrame] = [
        _EncodeFrame(
            value=value,
            is_undefined=is_undefined,
            side_channel=side_channel,
            prefix=prefix,
            comma_round_trip=comma_round_trip,
            comma_compact_nulls=comma_compact_nulls,
            encoder=encoder,
            serialize_date=serialize_date,
            sort=sort,
            filter_=filter_,
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
            add_query_prefix=add_query_prefix,
            depth=_depth,
            max_depth=_max_depth,
        )
    ]

    while stack:
        frame = stack[-1]

        if frame.phase == "start":
            if frame.max_depth is None:
                frame.max_depth = _get_max_encode_depth(None)
            if frame.depth > frame.max_depth:
                raise ValueError(MAX_ENCODING_DEPTH_EXCEEDED)

            if frame.prefix is None:
                frame.prefix = "?" if frame.add_query_prefix else ""
            if frame.comma_round_trip is None:
                frame.comma_round_trip = frame.generate_array_prefix is ListFormat.COMMA.generator
            if frame.formatter is None:
                frame.formatter = frame.format.formatter

            # Work with the original; we never mutate in place (we build new lists/maps when normalizing).
            obj: t.Any = frame.value

            # --- Pre-processing: filter & datetime handling -------------------------------
            filter_opt = frame.filter_
            if callable(filter_opt):
                # Callable filter can transform the object for this prefix.
                obj = filter_opt(frame.prefix, obj)
            else:
                # Normalize datetimes both for scalars and (in COMMA mode) list elements.
                if isinstance(obj, datetime):
                    obj = frame.serialize_date(obj) if callable(frame.serialize_date) else obj.isoformat()
                elif frame.generate_array_prefix is ListFormat.COMMA.generator and isinstance(obj, (list, tuple)):
                    if callable(frame.serialize_date):
                        obj = [frame.serialize_date(x) if isinstance(x, datetime) else x for x in obj]
                    else:
                        obj = [x.isoformat() if isinstance(x, datetime) else x for x in obj]

            # --- Null handling ------------------------------------------------------------
            if not frame.is_undefined and obj is None:
                if frame.strict_null_handling:
                    # Bare key (no '=value') when strict handling is requested.
                    result_token = (
                        frame.encoder(frame.prefix, frame.charset, frame.format)
                        if callable(frame.encoder) and not frame.encode_values_only
                        else frame.prefix
                    )
                    stack.pop()
                    last_result = result_token
                    continue
                # Otherwise treat `None` as empty string.
                obj = ""

            # --- Fast path for primitives/bytes -----------------------------------------
            if Utils.is_non_nullish_primitive(obj, frame.skip_nulls) or isinstance(obj, bytes):
                # When a custom encoder is provided, still coerce Python bools to lowercase JSON style.
                if callable(frame.encoder):
                    key_value = (
                        frame.prefix
                        if frame.encode_values_only
                        else frame.encoder(frame.prefix, frame.charset, frame.format)
                    )
                    if isinstance(obj, bool):
                        value_part = "true" if obj else "false"
                    else:
                        value_part = frame.encoder(obj, frame.charset, frame.format)
                    result_tokens = [f"{frame.formatter(key_value)}={frame.formatter(value_part)}"]
                else:
                    # Default fallback (no custom encoder): ensure lowercase boolean literals.
                    if isinstance(obj, bool):
                        value_str = "true" if obj else "false"
                    else:
                        value_str = str(obj)
                    result_tokens = [f"{frame.formatter(frame.prefix)}={frame.formatter(value_str)}"]

                stack.pop()
                last_result = result_tokens
                continue

            frame.obj = obj
            frame.values = []

            # If the *key itself* was undefined (not present in the parent), there is nothing to emit.
            if frame.is_undefined:
                stack.pop()
                last_result = frame.values
                continue

            # --- Cycle detection via ancestry lookup state --------------------------------
            # Only needed for traversable containers; primitive/bytes values return via fast path above.
            obj_wrapper: WeakWrapper = WeakWrapper(obj)
            if frame.cycle_state is None or frame.cycle_level is None:
                frame.cycle_state, frame.cycle_level = _bootstrap_cycle_state_from_side_channel(frame.side_channel)
            step = _compute_step_and_check_cycle(frame.cycle_state, obj_wrapper, frame.cycle_level)

            frame.obj_wrapper = obj_wrapper
            frame.step = step

            # --- Determine which keys/indices to traverse -------------------------------
            comma_effective_length: t.Optional[int] = None
            if frame.generate_array_prefix is ListFormat.COMMA.generator and isinstance(obj, (list, tuple)):
                # In COMMA mode we join the elements into a single token at this level.
                comma_items: t.List[t.Any] = list(obj)
                if frame.comma_compact_nulls:
                    comma_items = [item for item in comma_items if item is not None]
                comma_effective_length = len(comma_items)

                if frame.encode_values_only and callable(frame.encoder):
                    encoded_items = Utils.apply(comma_items, frame.encoder)
                    obj_keys_value = ",".join(("" if e is None else str(e)) for e in encoded_items)
                else:
                    obj_keys_value = ",".join(Utils.normalize_comma_elem(e) for e in comma_items)

                if comma_items:
                    frame.obj_keys = [{"value": obj_keys_value if obj_keys_value else None}]
                else:
                    frame.obj_keys = [{"value": UNDEFINED}]
            elif (
                filter_opt is not None
                and isinstance(filter_opt, ABCSequence)
                and not isinstance(filter_opt, (str, bytes, bytearray))
            ):
                # Iterable filter restricts traversal to a fixed key/index set.
                frame.obj_keys = list(filter_opt)
            else:
                # Default: enumerate keys/indices from mappings or sequences.
                if isinstance(obj, t.Mapping):
                    keys = list(obj.keys())
                elif isinstance(obj, (list, tuple)):
                    keys = list(range(len(obj)))
                else:
                    keys = []
                frame.obj_keys = sorted(keys, key=cmp_to_key(frame.sort)) if frame.sort is not None else keys

            # Percent-encode literal dots in key names when requested.
            encoded_prefix: str = frame.prefix.replace(".", "%2E") if frame.encode_dot_in_keys else frame.prefix

            # In comma round-trip mode, ensure a single-element list appends `[]` to preserve type on decode.
            single_item_for_round_trip: bool = False
            if frame.comma_round_trip and isinstance(obj, (list, tuple)):
                if frame.generate_array_prefix is ListFormat.COMMA.generator and comma_effective_length is not None:
                    single_item_for_round_trip = comma_effective_length == 1
                else:
                    single_item_for_round_trip = len(obj) == 1

            frame.adjusted_prefix = f"{encoded_prefix}[]" if single_item_for_round_trip else encoded_prefix

            # Optionally emit empty lists as `key[]=`.
            if frame.allow_empty_lists and isinstance(obj, (list, tuple)) and not obj:
                stack.pop()
                last_result = [f"{frame.adjusted_prefix}[]"]
                continue

            frame.index = 0
            frame.phase = "iterate"
            continue

        if frame.phase == "iterate":
            if frame.index >= len(frame.obj_keys):
                if frame.cycle_pushed and frame.obj_wrapper is not None and frame.cycle_state is not None:
                    _pop_current_node(frame.cycle_state, frame.obj_wrapper)
                    frame.cycle_pushed = False
                stack.pop()
                last_result = frame.values
                continue

            if not frame.cycle_pushed and frame.obj_wrapper is not None and frame.cycle_state is not None:
                _push_current_node(
                    frame.cycle_state,
                    frame.obj_wrapper,
                    frame.cycle_level if frame.cycle_level is not None else 0,
                    frame.step,
                    (frame.cycle_level == 0),
                )
                frame.side_channel[frame.obj_wrapper] = frame.step
                frame.cycle_pushed = True

            _key = frame.obj_keys[frame.index]
            frame.index += 1

            # Resolve the child value and whether it was "undefined" at this level.
            _value: t.Any
            _value_undefined: bool
            if isinstance(_key, t.Mapping) and "value" in _key and not isinstance(_key.get("value"), Undefined):
                _value = _key.get("value")
                _value_undefined = False
            else:
                try:
                    if isinstance(frame.obj, t.Mapping):
                        _value = frame.obj.get(_key)
                        _value_undefined = _key not in frame.obj
                    elif isinstance(frame.obj, (list, tuple)):
                        if isinstance(_key, int):
                            _value = frame.obj[_key]
                            _value_undefined = False
                        else:
                            _value = None
                            _value_undefined = True
                    else:
                        _value = frame.obj[_key]
                        _value_undefined = False
                except Exception:  # noqa: BLE001  # pylint: disable=W0718
                    # User-provided __getitem__/mapping accessors may raise arbitrary exceptions.
                    _value = None
                    _value_undefined = True

            # Optionally drop null children.
            if frame.skip_nulls and _value is None:
                continue

            # When using dotted paths and also encoding dots in keys, percent-escape '.' inside key names.
            encoded_key: str = (
                str(_key).replace(".", "%2E") if frame.allow_dots and frame.encode_dot_in_keys else str(_key)
            )

            # Build the child key path depending on whether we're traversing a list or a mapping.
            key_prefix: str = (
                frame.generate_array_prefix(frame.adjusted_prefix, encoded_key)
                if isinstance(frame.obj, (list, tuple))
                else f"{frame.adjusted_prefix}{f'.{encoded_key}' if frame.allow_dots else f'[{encoded_key}]'}"
            )

            frame.phase = "await_child"
            stack.append(
                _EncodeFrame(
                    value=_value,
                    is_undefined=_value_undefined,
                    side_channel=frame.side_channel,
                    prefix=key_prefix,
                    comma_round_trip=frame.comma_round_trip,
                    comma_compact_nulls=frame.comma_compact_nulls,
                    encoder=(
                        None
                        if frame.generate_array_prefix is ListFormat.COMMA.generator
                        and frame.encode_values_only
                        and isinstance(frame.obj, (list, tuple))
                        else frame.encoder
                    ),
                    serialize_date=frame.serialize_date,
                    sort=frame.sort,
                    filter_=frame.filter_,
                    formatter=frame.formatter,
                    format=frame.format,
                    generate_array_prefix=frame.generate_array_prefix,
                    allow_empty_lists=frame.allow_empty_lists,
                    strict_null_handling=frame.strict_null_handling,
                    skip_nulls=frame.skip_nulls,
                    encode_dot_in_keys=frame.encode_dot_in_keys,
                    allow_dots=frame.allow_dots,
                    encode_values_only=frame.encode_values_only,
                    charset=frame.charset,
                    add_query_prefix=False,
                    depth=frame.depth + 1,
                    max_depth=frame.max_depth,
                    cycle_state=frame.cycle_state,
                    cycle_level=(frame.cycle_level + 1) if frame.cycle_level is not None else None,
                )
            )
            continue

        # frame.phase == "await_child"
        if isinstance(last_result, (list, tuple)):
            frame.values.extend(last_result)
        else:
            frame.values.append(last_result)
        frame.phase = "iterate"

    return [] if last_result is None else last_result
