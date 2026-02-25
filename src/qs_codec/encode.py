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
from collections.abc import Mapping as ABCMapping
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
from .models.key_path_node import KeyPathNode
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
          filter is used). Root sequences are projected to a temporary mapping and deep-copied first when a callable
          filter is used.
        - If a callable `filter` is provided, it can transform the root object.
        - If an iterable filter is provided, it selects which *root* keys to emit.
    """
    # Treat `None` as "nothing to encode".
    if value is None:
        return ""

    filter_opt = options.filter

    # Normalize the root into a mapping we can traverse deterministically:
    # - Mapping  -> shallow copy (deep-copy only when a callable filter may mutate)
    # - Sequence -> optionally deep-copy for callable filters, then promote to {"0": v0, "1": v1, ...}
    # - Other    -> empty (encodes to "")
    obj: t.Mapping[str, t.Any]
    if isinstance(value, ABCMapping):
        obj = deepcopy(value) if callable(filter_opt) else dict(value)
    elif isinstance(value, (list, tuple)):
        sequence = deepcopy(value) if callable(filter_opt) else value
        obj = {str(i): item for i, item in enumerate(sequence)}
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
    missing = _MISSING
    for _key in obj_keys:
        if not isinstance(_key, str):
            # Skip non-string keys; parity with ports that stringify key paths.
            continue

        obj_value = obj.get(_key, missing)
        key_is_undefined = obj_value is missing

        # Optionally drop explicit nulls at the root.
        if options.skip_nulls and obj_value is None:
            continue

        _encoded: t.Union[t.List[t.Any], t.Tuple[t.Any, ...], t.Any] = _encode(
            value=None if key_is_undefined else obj_value,
            is_undefined=key_is_undefined,
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

_MISSING = object()

# Unique placeholder used as a key within the side-channel chain to pass context down traversal frames.
_sentinel: WeakWrapper = WeakWrapper({})
MAX_ENCODING_DEPTH_EXCEEDED = "Maximum encoding depth exceeded"
_PHASE_START = 0
_PHASE_ITERATE = 1
_PHASE_AWAIT_CHILD = 2


def _get_max_encode_depth(max_depth: t.Optional[int]) -> int:
    if max_depth is None:
        return sys.maxsize
    return max_depth


class _EncodeFrame:
    """Mutable traversal frame for iterative encoding."""

    __slots__ = (
        "add_query_prefix",
        "adjusted_path",
        "allow_dots",
        "allow_empty_lists",
        "charset",
        "comma_compact_nulls",
        "comma_round_trip",
        "cycle_level",
        "cycle_pushed",
        "cycle_state",
        "depth",
        "encode_dot_in_keys",
        "encode_values_only",
        "encoder",
        "filter_",
        "format",
        "formatter",
        "generate_array_prefix",
        "index",
        "is_mapping",
        "is_sequence",
        "is_undefined",
        "max_depth",
        "obj",
        "obj_id",
        "obj_keys",
        "path",
        "phase",
        "prefix",
        "serialize_date",
        "side_channel",
        "skip_nulls",
        "sort",
        "step",
        "strict_null_handling",
        "value",
        "values",
    )
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
    path: t.Optional[KeyPathNode]
    phase: int
    obj: t.Any
    obj_id: t.Optional[int]
    is_mapping: bool
    is_sequence: bool
    step: int
    obj_keys: t.List[t.Any]
    values: t.List[t.Any]
    index: int
    adjusted_path: t.Optional[KeyPathNode]
    cycle_state: t.Optional["_CycleState"]
    cycle_level: t.Optional[int]
    cycle_pushed: bool

    def __init__(
        self,
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
        format: Format,
        generate_array_prefix: t.Callable[[str, t.Optional[str]], str],
        allow_empty_lists: bool,
        strict_null_handling: bool,
        skip_nulls: bool,
        encode_dot_in_keys: bool,
        allow_dots: bool,
        encode_values_only: bool,
        charset: t.Optional[Charset],
        add_query_prefix: bool,
        depth: int,
        max_depth: t.Optional[int],
        path: t.Optional[KeyPathNode] = None,
        cycle_state: t.Optional["_CycleState"] = None,
        cycle_level: t.Optional[int] = None,
    ) -> None:
        self.value = value
        self.is_undefined = is_undefined
        self.side_channel = side_channel
        self.prefix = prefix
        self.comma_round_trip = comma_round_trip
        self.comma_compact_nulls = comma_compact_nulls
        self.encoder = encoder
        self.serialize_date = serialize_date
        self.sort = sort
        self.filter_ = filter_
        self.formatter = formatter
        self.format = format
        self.generate_array_prefix = generate_array_prefix
        self.allow_empty_lists = allow_empty_lists
        self.strict_null_handling = strict_null_handling
        self.skip_nulls = skip_nulls
        self.encode_dot_in_keys = encode_dot_in_keys
        self.allow_dots = allow_dots
        self.encode_values_only = encode_values_only
        self.charset = charset
        self.add_query_prefix = add_query_prefix
        self.depth = depth
        self.max_depth = max_depth
        self.path = path
        self.phase = _PHASE_START
        self.obj = None
        self.obj_id = None
        self.is_mapping = False
        self.is_sequence = False
        self.step = 0
        self.obj_keys = []
        self.values = []
        self.index = 0
        self.adjusted_path = None
        self.cycle_state = cycle_state
        self.cycle_level = cycle_level
        self.cycle_pushed = False


@dataclass
class _CycleState:
    entries: t.Dict[int, t.List[t.Tuple[int, t.Any, bool]]] = field(default_factory=dict)


def _identity_key(value: t.Any) -> int:
    """Return an identity-stable integer key for cycle bookkeeping.

    This helper accepts raw ``id(obj)`` integers and returns them unchanged.
    For ``WeakWrapper`` values it returns ``id(value.value)``; if the wrapped
    object is unavailable (``ReferenceError``), it falls back to ``id(value)``.

    Callers should pass object references or ``id(obj)`` values only; arbitrary
    non-id integers are treated as precomputed identity keys.
    """
    if isinstance(value, int):
        return value
    if isinstance(value, WeakWrapper):
        try:
            return id(value.value)
        except ReferenceError:
            return id(value)
    return id(value)


def _bootstrap_cycle_state_from_side_channel(side_channel: WeakKeyDictionary) -> t.Tuple[_CycleState, int]:
    """
    Build O(1) ancestry lookup state from an existing side-channel chain.

    Returns:
        Tuple of (state, current_level), where current_level is the chain length
        from the current frame to the top-most side-channel mapping.
    """
    chain: t.List[WeakKeyDictionary] = []
    tmp_sc = side_channel.get(_sentinel)
    while isinstance(tmp_sc, WeakKeyDictionary):
        chain.append(tmp_sc)
        tmp_sc = tmp_sc.get(_sentinel)  # type: ignore[assignment]

    state = _CycleState()
    for level, ancestor in enumerate(reversed(chain)):
        is_top = ancestor.get(_sentinel) is None
        for key, pos in ancestor.items():
            if key is _sentinel:
                continue
            state.entries.setdefault(_identity_key(key), []).append((level, pos, is_top))

    return state, len(chain)


def _compute_step_and_check_cycle(state: _CycleState, node_key: t.Any, current_level: int) -> int:
    """
    Compute the current cycle-detection "step" and raise on circular reference.

    Semantics intentionally match the legacy side-channel chain scan:
      * nearest ancestor match wins
      * raise when ancestor_pos == distance
      * return 0 when no match or when nearest match is the top-most side-channel
    """
    key_id = node_key if isinstance(node_key, int) else _identity_key(node_key)
    entries = state.entries.get(key_id)
    if not entries:
        return 0

    ancestor_level, ancestor_pos, is_top = entries[-1]
    distance = current_level - ancestor_level
    if ancestor_pos == distance:
        raise ValueError("Circular reference detected")  # noqa: TRY003

    return 0 if is_top else distance


def _push_current_node(state: _CycleState, node_key: t.Any, current_level: int, pos: int, is_top: bool) -> None:
    key_id = node_key if isinstance(node_key, int) else _identity_key(node_key)
    state.entries.setdefault(key_id, []).append((current_level, pos, is_top))


def _pop_current_node(state: _CycleState, node_key: t.Any) -> None:
    key_id = node_key if isinstance(node_key, int) else _identity_key(node_key)
    entries = state.entries.get(key_id)
    if not entries:
        return

    entries.pop()
    if not entries:
        del state.entries[key_id]


_INDICES_GENERATOR = ListFormat.INDICES.generator
_BRACKETS_GENERATOR = ListFormat.BRACKETS.generator
_REPEAT_GENERATOR = ListFormat.REPEAT.generator
_COMMA_GENERATOR = ListFormat.COMMA.generator


def _next_path_for_sequence(
    path: KeyPathNode,
    generator: t.Callable[[str, t.Optional[str]], str],
    encoded_key: str,
) -> KeyPathNode:
    if generator is _INDICES_GENERATOR:
        return path.append(f"[{encoded_key}]")
    if generator is _BRACKETS_GENERATOR:
        return path.append("[]")
    if generator is _REPEAT_GENERATOR or generator is _COMMA_GENERATOR:
        return path

    parent = path.materialize()
    child = generator(parent, encoded_key)
    if child.startswith(parent):
        return path.append(child[len(parent) :])

    # Deliberate fallback for custom generators: a non-prefixed child string is
    # treated as a fully materialized root path, so ancestor linkage is dropped.
    # Downstream materialize()/as_dot_encoded() calls then operate on this new
    # root only. Custom generators should prefix with `parent` to preserve ancestry.
    return KeyPathNode.from_materialized(child)


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

        if frame.phase == _PHASE_START:
            if frame.max_depth is None:
                frame.max_depth = _get_max_encode_depth(None)
            if frame.depth > frame.max_depth:
                raise ValueError(MAX_ENCODING_DEPTH_EXCEEDED)

            if frame.path is None:
                if frame.prefix is None:
                    frame.prefix = "?" if frame.add_query_prefix else ""
                frame.path = KeyPathNode.from_materialized(frame.prefix)
            # Internal invariant: `frame.path` is initialized above when absent.
            current_path = t.cast(KeyPathNode, frame.path)
            if frame.comma_round_trip is None:
                frame.comma_round_trip = frame.generate_array_prefix is _COMMA_GENERATOR
            if frame.formatter is None:
                frame.formatter = frame.format.formatter

            obj: t.Any = frame.value
            filter_opt = frame.filter_

            if callable(filter_opt):
                obj = filter_opt(current_path.materialize(), obj)
            else:
                if isinstance(obj, datetime):
                    obj = frame.serialize_date(obj) if callable(frame.serialize_date) else obj.isoformat()
                elif frame.generate_array_prefix is _COMMA_GENERATOR and isinstance(obj, (list, tuple)):
                    if callable(frame.serialize_date):
                        obj = [frame.serialize_date(x) if isinstance(x, datetime) else x for x in obj]
                    else:
                        obj = [x.isoformat() if isinstance(x, datetime) else x for x in obj]

            if not frame.is_undefined and obj is None:
                if frame.strict_null_handling:
                    key_text = current_path.materialize()
                    key_value = (
                        frame.encoder(key_text, frame.charset, frame.format)
                        if callable(frame.encoder) and not frame.encode_values_only
                        else key_text
                    )
                    result_token = frame.formatter(key_value) if frame.formatter is not None else key_value
                    stack.pop()
                    last_result = result_token
                    continue
                obj = ""

            if Utils.is_non_nullish_primitive(obj, frame.skip_nulls) or isinstance(obj, bytes):
                key_text = current_path.materialize()
                if callable(frame.encoder):
                    key_value = (
                        key_text if frame.encode_values_only else frame.encoder(key_text, frame.charset, frame.format)
                    )
                    if isinstance(obj, bool):
                        value_part = "true" if obj else "false"
                    else:
                        value_part = frame.encoder(obj, frame.charset, frame.format)
                    result_tokens = [f"{frame.formatter(key_value)}={frame.formatter(value_part)}"]
                else:
                    if isinstance(obj, bool):
                        value_str = "true" if obj else "false"
                    else:
                        value_str = str(obj)
                    result_tokens = [f"{frame.formatter(key_text)}={frame.formatter(value_str)}"]

                stack.pop()
                last_result = result_tokens
                continue

            frame.obj = obj
            frame.values = []
            frame.is_mapping = isinstance(obj, ABCMapping)
            frame.is_sequence = isinstance(obj, (list, tuple))

            if frame.is_undefined:
                stack.pop()
                last_result = frame.values
                continue

            obj_id = id(obj)
            if frame.cycle_state is None or frame.cycle_level is None:
                frame.cycle_state, frame.cycle_level = _bootstrap_cycle_state_from_side_channel(frame.side_channel)
            frame.step = _compute_step_and_check_cycle(frame.cycle_state, obj_id, frame.cycle_level)
            frame.obj_id = obj_id

            comma_effective_length: t.Optional[int] = None
            if frame.generate_array_prefix is _COMMA_GENERATOR and frame.is_sequence:
                comma_items: t.List[t.Any] = list(obj)
                if frame.comma_compact_nulls:
                    comma_items = [item for item in comma_items if item is not None]
                comma_effective_length = len(comma_items)

                if frame.encode_values_only and callable(frame.encoder):
                    encoded_items = [frame.encoder(item, frame.charset, frame.format) for item in comma_items]
                    obj_keys_value = ",".join("" if e is None else str(e) for e in encoded_items)
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
                frame.obj_keys = list(filter_opt)
            else:
                if frame.is_mapping:
                    keys = list(obj.keys())
                elif frame.is_sequence:
                    keys = list(range(len(obj)))
                else:
                    keys = []
                frame.obj_keys = sorted(keys, key=cmp_to_key(frame.sort)) if frame.sort is not None else keys

            path_for_children = current_path.as_dot_encoded() if frame.encode_dot_in_keys else current_path

            single_item_for_round_trip = False
            if frame.comma_round_trip and frame.is_sequence:
                if frame.generate_array_prefix is _COMMA_GENERATOR and comma_effective_length is not None:
                    single_item_for_round_trip = comma_effective_length == 1
                else:
                    single_item_for_round_trip = len(obj) == 1

            frame.adjusted_path = path_for_children.append("[]") if single_item_for_round_trip else path_for_children

            if frame.allow_empty_lists and frame.is_sequence and not obj:
                stack.pop()
                last_result = [frame.adjusted_path.append("[]").materialize()]
                continue

            frame.index = 0
            frame.phase = _PHASE_ITERATE
            continue

        elif frame.phase == _PHASE_ITERATE:
            if frame.index >= len(frame.obj_keys):
                if frame.cycle_pushed and frame.obj_id is not None and frame.cycle_state is not None:
                    _pop_current_node(frame.cycle_state, frame.obj_id)
                    frame.cycle_pushed = False
                stack.pop()
                last_result = frame.values
                continue

            if not frame.cycle_pushed and frame.obj_id is not None and frame.cycle_state is not None:
                _push_current_node(
                    frame.cycle_state,
                    frame.obj_id,
                    frame.cycle_level if frame.cycle_level is not None else 0,
                    frame.step,
                    frame.cycle_level == 0,
                )
                frame.cycle_pushed = True

            _key = frame.obj_keys[frame.index]
            frame.index += 1

            _value: t.Any
            _value_undefined: bool
            if isinstance(_key, ABCMapping) and "value" in _key and not isinstance(_key.get("value"), Undefined):
                _value = _key.get("value")
                _value_undefined = False
            else:
                try:
                    if frame.is_mapping:
                        candidate = frame.obj.get(_key, _MISSING)
                        if candidate is _MISSING:
                            _value = None
                            _value_undefined = True
                        else:
                            _value = candidate
                            _value_undefined = False
                    elif frame.is_sequence:
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
                    _value = None
                    _value_undefined = True

            if frame.skip_nulls and _value is None:
                continue

            encoded_key = str(_key).replace(".", "%2E") if frame.allow_dots and frame.encode_dot_in_keys else str(_key)
            if frame.path is None:  # pragma: no cover - internal invariant
                raise RuntimeError("path is not initialized")  # noqa: TRY003
            adjusted_path = frame.adjusted_path if frame.adjusted_path is not None else frame.path

            if frame.is_sequence:
                child_path = _next_path_for_sequence(adjusted_path, frame.generate_array_prefix, encoded_key)
            else:
                child_path = adjusted_path.append(f".{encoded_key}" if frame.allow_dots else f"[{encoded_key}]")

            frame.phase = _PHASE_AWAIT_CHILD
            stack.append(
                _EncodeFrame(
                    value=_value,
                    is_undefined=_value_undefined,
                    side_channel=frame.side_channel,
                    prefix=None,
                    path=child_path,
                    comma_round_trip=frame.comma_round_trip,
                    comma_compact_nulls=frame.comma_compact_nulls,
                    encoder=(
                        None
                        if frame.generate_array_prefix is _COMMA_GENERATOR
                        and frame.encode_values_only
                        and frame.is_sequence
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

        else:
            if frame.phase != _PHASE_AWAIT_CHILD:  # pragma: no cover - internal invariant
                raise RuntimeError("Unexpected _encode frame phase")  # noqa: TRY003

            if isinstance(last_result, (list, tuple)):
                frame.values.extend(last_result)
            else:
                frame.values.append(last_result)
            frame.phase = _PHASE_ITERATE

    return [] if last_result is None else last_result
