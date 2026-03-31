"""Python-side bridge helpers for the native encode backend."""

from __future__ import annotations

import typing as t
from collections.abc import Mapping
from collections.abc import Sequence as ABCSequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from urllib.parse import unquote, unquote_plus

from .constants.encode_constants import MAX_ENCODING_DEPTH_EXCEEDED
from .encode import (
    _compute_step_and_check_cycle,
    _get_max_encode_depth,
    _pop_current_node,
    _push_current_node,
    pure_encode,
)
from .enums.charset import Charset
from .enums.format import Format
from .enums.list_format import ListFormat
from .models.cycle_state import CycleState
from .models.encode_options import EncodeOptions
from .models.undefined import Undefined
from .utils.encode_utils import EncodeUtils

_I64_MIN = -(1 << 63)
_I64_MAX = (1 << 63) - 1
_U64_MAX = (1 << 64) - 1
_OMIT = object()


class _FallbackToPureEncode(RuntimeError):
    """Signal that the request should remain on the pure-Python path."""


def _is_filter_sequence(value: t.Any) -> bool:
    return value is not None and isinstance(value, ABCSequence) and not isinstance(value, (str, bytes, bytearray))


def _normalize_root_object(value: t.Any, *, deep_copy: bool) -> t.Any:
    if isinstance(value, dict):
        return deepcopy(value) if deep_copy else dict(value)
    if isinstance(value, Mapping):
        return deepcopy(value) if deep_copy else dict(value)
    if isinstance(value, (list, tuple)):
        sequence = deepcopy(value) if deep_copy else value
        return {str(index): item for index, item in enumerate(sequence)}
    return {}


def _normalize_encode_scalar(value: t.Any) -> t.Any:
    if value is None or isinstance(value, (str, bytes, datetime)):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if _I64_MIN <= value <= _I64_MAX or 0 <= value <= _U64_MAX:
            return value
        return str(value)
    if isinstance(value, float):
        return value
    if isinstance(value, (Decimal, Enum)):
        return str(value)
    return _OMIT


def _normalize_encode_tree(
    value: t.Any,
    *,
    depth: int,
    max_depth: int,
    cycle_state: CycleState,
    root_level: int,
) -> t.Any:
    scalar = _normalize_encode_scalar(value)
    if scalar is not _OMIT:
        return scalar

    if depth > max_depth:
        raise ValueError(MAX_ENCODING_DEPTH_EXCEEDED)

    if isinstance(value, Undefined):
        return _OMIT

    if isinstance(value, dict):
        object_id = id(value)
        step = _compute_step_and_check_cycle(cycle_state, object_id, depth)
        _push_current_node(cycle_state, object_id, depth, step, depth == root_level)
        try:
            normalized: t.Dict[str, t.Any] = {}
            for key, child in value.items():
                child_value = _normalize_encode_tree(
                    child,
                    depth=depth + 1,
                    max_depth=max_depth,
                    cycle_state=cycle_state,
                    root_level=root_level,
                )
                if child_value is _OMIT:
                    continue
                normalized[str(key)] = child_value
            return normalized
        finally:
            _pop_current_node(cycle_state, object_id)

    if isinstance(value, Mapping):
        raise _FallbackToPureEncode("native encode keeps generic Mapping behavior on the pure path")

    if isinstance(value, (list, tuple)):
        if any(isinstance(item, Undefined) for item in value):
            raise _FallbackToPureEncode("native encode does not model Undefined holes inside sequences")

        object_id = id(value)
        step = _compute_step_and_check_cycle(cycle_state, object_id, depth)
        _push_current_node(cycle_state, object_id, depth, step, depth == root_level)
        try:
            normalized_items: t.List[t.Any] = []
            for child in value:
                child_value = _normalize_encode_tree(
                    child,
                    depth=depth + 1,
                    max_depth=max_depth,
                    cycle_state=cycle_state,
                    root_level=root_level,
                )
                if child_value is _OMIT:
                    raise _FallbackToPureEncode("native encode does not model omitted sequence elements")
                normalized_items.append(child_value)
            return normalized_items
        finally:
            _pop_current_node(cycle_state, object_id)

    raise _FallbackToPureEncode(f"unsupported encode leaf type for native backend: {type(value)!r}")


def _uses_default_encoder(options: EncodeOptions) -> bool:
    return getattr(options, "_encoder", None) is EncodeUtils.encode


def _should_fallback_to_pure(value: t.Any, options: EncodeOptions) -> bool:
    if options.delimiter == "":
        return True
    if not isinstance(options.charset, Charset) or not isinstance(options.format, Format):
        return True
    if isinstance(value, (list, tuple)) and _is_filter_sequence(options.filter):
        return True
    if _is_filter_sequence(options.filter) and len(t.cast(ABCSequence[t.Any], options.filter)) == 0:
        return True
    if options.encode_dot_in_keys:
        return True
    if options.allow_empty_lists:
        return True
    if options.list_format == ListFormat.COMMA and (options.strict_null_handling or options.skip_nulls):
        return True
    if options.encode and not _uses_default_encoder(options):
        return True
    return False


def _prepare_native_root(value: t.Any, options: EncodeOptions) -> t.Dict[str, t.Any]:
    root_filter = options.filter if callable(options.filter) else None
    root_object = _normalize_root_object(value, deep_copy=root_filter is not None)

    if root_filter is not None:
        root_object = root_filter("", root_object)
        root_object = _normalize_root_object(root_object, deep_copy=False)

    if not isinstance(root_object, Mapping):
        return {}

    max_depth = _get_max_encode_depth(options.max_depth)
    normalized: t.Dict[str, t.Any] = {}
    for key, child in root_object.items():
        if not isinstance(key, str):
            continue
        normalized_child = _normalize_encode_tree(
            child,
            depth=0,
            max_depth=max_depth,
            cycle_state=CycleState(),
            root_level=0,
        )
        if normalized_child is _OMIT:
            continue
        normalized[key] = normalized_child
    return normalized


@dataclass
class _EncodeCallbackBridge:
    options: EncodeOptions
    skip_root_filter: bool

    def _normalize_replacement(self, value: t.Any) -> t.Any:
        """Normalize callback replacement values using pure-Python validation rules."""
        return _normalize_encode_tree(
            value,
            depth=0,
            max_depth=_get_max_encode_depth(self.options.max_depth),
            cycle_state=CycleState(),
            root_level=0,
        )

    def apply_filter(self, prefix: str, value: t.Any) -> t.Tuple[str, t.Any]:
        """Adapt the Python filter callback to the native keep/omit/replace contract."""
        filter_option = self.options.filter
        if not callable(filter_option):
            return ("keep", None)
        if self.skip_root_filter and prefix == "":
            return ("keep", None)

        normalized_prefix = unquote_plus(prefix) if self.options.format.format_name == "RFC1738" else unquote(prefix)
        filter_fn = t.cast(t.Callable[[str, t.Any], t.Any], filter_option)
        result = filter_fn(normalized_prefix, value)
        if isinstance(result, Undefined):
            return ("omit", None)
        return ("replace", self._normalize_replacement(result))

    def encode_token(self, token: t.Any) -> str:
        """Run the user-visible scalar encoder callback for a native token."""
        encoder = self.options.encoder
        return encoder(token, self.options.charset, self.options.format)

    def compare(self, left: str, right: str) -> int:
        """Bridge the Python sort callback to the integer comparator expected by Rust."""
        sorter = t.cast(t.Callable[[t.Any, t.Any], int], self.options.sort)
        return int(sorter(left, right))

    def serialize_temporal(self, value: datetime) -> t.Optional[str]:
        """Keep Python's date serialization callback authoritative for native encode."""
        serializer = self.options.serialize_date
        if callable(serializer):
            return serializer(value)
        return value.isoformat()


def _normalize_encode_config(options: EncodeOptions) -> t.Dict[str, t.Any]:
    whitelist_keys: t.List[str] = []
    whitelist_indices: t.List[int] = []
    if _is_filter_sequence(options.filter):
        for entry in t.cast(t.Sequence[t.Union[str, int]], options.filter):
            if isinstance(entry, str):
                whitelist_keys.append(entry)
            elif isinstance(entry, int) and not isinstance(entry, bool):
                whitelist_indices.append(entry)

    return {
        "encode": False,
        "delimiter": options.delimiter,
        "list_format": options.list_format.list_format_name,
        "charset": options.charset.encoding,
        "format": options.format.format_name,
        "charset_sentinel": bool(options.charset_sentinel),
        "allow_empty_lists": bool(options.allow_empty_lists),
        "strict_null_handling": bool(options.strict_null_handling),
        "skip_nulls": bool(options.skip_nulls),
        "comma_round_trip": bool(options.comma_round_trip),
        "comma_compact_nulls": bool(options.comma_compact_nulls),
        "encode_values_only": bool(options.encode_values_only),
        "add_query_prefix": bool(options.add_query_prefix),
        "allow_dots": bool(options.allow_dots),
        "encode_dot_in_keys": bool(options.encode_dot_in_keys),
        "whitelist_keys": whitelist_keys,
        "whitelist_indices": whitelist_indices,
        "has_function_filter": callable(options.filter),
        "has_encoder": bool(options.encode),
        "has_sorter": callable(options.sort),
        "max_depth": options.max_depth,
    }


def encode_with_rust(native_module: t.Any, value: t.Any, options: t.Optional[EncodeOptions] = None) -> str:
    """Encode through the native backend while keeping Python behavior authoritative."""
    if value is None:
        return ""

    opts = options if options is not None else EncodeOptions()
    if _should_fallback_to_pure(value, opts):
        return pure_encode(value, opts)

    try:
        prepared_root = _prepare_native_root(value, opts)
    except (_FallbackToPureEncode, RecursionError):
        return pure_encode(value, opts)

    if not prepared_root:
        return ""

    callback_bridge = _EncodeCallbackBridge(options=opts, skip_root_filter=callable(opts.filter))
    encoded = native_module.encode(prepared_root, _normalize_encode_config(opts), callback_bridge)
    return opts.format.formatter(encoded)
