"""Python-side bridge helpers for the native decode backend."""

from __future__ import annotations

import re
import sys
import typing as t
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from math import isinf

from .decode import _first_structured_split_index, _leading_structured_root, _parse_array_value, pure_decode
from .enums.charset import Charset
from .enums.duplicates import Duplicates
from .enums.sentinel import Sentinel
from .models.decode_options import DecodeOptions
from .utils.utils import Utils

_I64_MIN = -(1 << 63)
_I64_MAX = (1 << 63) - 1
_U64_MAX = (1 << 64) - 1


@dataclass
class _OpaqueLeafPool:
    values_by_token: t.Dict[str, t.Any] = field(default_factory=dict)
    token_by_object_id: t.Dict[int, str] = field(default_factory=dict)

    def placeholder(self, value: t.Any) -> str:
        """Return a stable token for a Python object that cannot cross FFI directly."""
        object_id = id(value)
        token = self.token_by_object_id.get(object_id)
        if token is None:
            token = f"__qs_codec_pyobj__:{len(self.values_by_token)}:{object_id:x}"
            self.token_by_object_id[object_id] = token
            self.values_by_token[token] = value
        return token


def _convert_decode_leaf(value: t.Any, pool: _OpaqueLeafPool) -> t.Any:
    """Convert a Python decode leaf into a native-compatible scalar or placeholder."""
    if value is None or isinstance(value, (str, bytes, datetime)):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if _I64_MIN <= value <= _I64_MAX or 0 <= value <= _U64_MAX:
            return value
        return pool.placeholder(value)
    if isinstance(value, float):
        return value
    if isinstance(value, (Decimal, Enum)):
        return pool.placeholder(value)
    return pool.placeholder(value)


def _restore_placeholders(value: t.Any, pool: _OpaqueLeafPool) -> t.Any:
    if isinstance(value, str):
        return pool.values_by_token.get(value, value)
    if isinstance(value, list):
        return [_restore_placeholders(item, pool) for item in value]
    if isinstance(value, dict):
        return {key: _restore_placeholders(item, pool) for key, item in value.items()}
    return value


def _normalize_decode_pairs_config(options: DecodeOptions) -> t.Dict[str, t.Any]:
    depth = int(options.depth)
    if depth < 0:
        depth = 0

    list_limit = int(options.list_limit)
    if list_limit < 0:
        raise RuntimeError("negative list_limit cannot be normalized for native decode_pairs")

    duplicates = {
        Duplicates.COMBINE: "combine",
        Duplicates.FIRST: "first",
        Duplicates.LAST: "last",
    }[options.duplicates]

    return {
        "allow_dots": bool(options.allow_dots),
        "decode_dot_in_keys": bool(options.decode_dot_in_keys),
        "allow_empty_lists": bool(options.allow_empty_lists),
        # qs.py treats the limit as inclusive for explicit numeric indices.
        "list_limit": list_limit + 1,
        "original_list_limit": list_limit,
        "depth": depth,
        "duplicates": duplicates,
        "parse_lists": bool(options.parse_lists),
        "strict_depth": bool(options.strict_depth),
        "strict_null_handling": bool(options.strict_null_handling),
        "raise_on_limit_exceeded": bool(options.raise_on_limit_exceeded),
        "parameter_limit": sys.maxsize,
    }


def _effective_parse_lists_for_string(value: str, options: DecodeOptions) -> bool:
    parse_lists_effective = options.parse_lists
    if not parse_lists_effective:
        return False

    query = value.replace("?", "", 1) if options.ignore_query_prefix else value
    if isinstance(options.delimiter, re.Pattern):
        parts_count = len(re.split(options.delimiter, query)) if query else 0
    else:
        parts_count = (query.count(options.delimiter) + 1) if query else 0

    if 0 < options.list_limit < parts_count:
        return False
    return True


def _split_query_parts(value: str, options: DecodeOptions) -> t.Tuple[t.List[str], Charset]:
    clean_str = value.replace("?", "", 1) if options.ignore_query_prefix else value
    clean_str = clean_str.replace("%5B", "[").replace("%5b", "[").replace("%5D", "]").replace("%5d", "]")

    limit: t.Optional[int] = None if isinf(options.parameter_limit) else int(options.parameter_limit)
    if limit is not None and limit <= 0:
        raise ValueError("Parameter limit must be a positive integer.")

    parts: t.List[str]
    if limit is None:
        if isinstance(options.delimiter, re.Pattern):
            parts = re.split(options.delimiter, clean_str)
        else:
            parts = clean_str.split(options.delimiter)
    else:
        if options.raise_on_limit_exceeded:
            if isinstance(options.delimiter, re.Pattern):
                parts = re.split(options.delimiter, clean_str, maxsplit=limit)
            else:
                parts = clean_str.split(options.delimiter, limit)
            if len(parts) > limit:
                raise ValueError(
                    f"Parameter limit exceeded: Only {limit} parameter{'s' if limit != 1 else ''} allowed."
                )
        else:
            if isinstance(options.delimiter, re.Pattern):
                parts = re.split(options.delimiter, clean_str)
            else:
                parts = clean_str.split(options.delimiter)
            parts = parts[:limit]

    charset = options.charset
    if options.charset_sentinel:
        for index, part in enumerate(parts):
            if part.startswith("utf8="):
                if part == Sentinel.CHARSET.encoded:
                    charset = Charset.UTF8
                elif part == Sentinel.ISO.encoded:
                    charset = Charset.LATIN1
                del parts[index]
                break

    return parts, charset


def _tokenize_string_pairs(value: str, options: DecodeOptions, *, parse_lists: bool) -> t.List[t.Tuple[str, t.Any]]:
    parts, charset = _split_query_parts(value, options)
    if not parts:
        return []

    pairs: t.List[t.Tuple[str, t.Any]] = []
    accumulator: t.Dict[str, t.Any] = {}

    for part in parts:
        if not part:
            continue

        bracket_equals_pos = part.find("]=")
        pos = part.find("=") if bracket_equals_pos == -1 else (bracket_equals_pos + 1)

        if pos == -1:
            key = options.decode_key(part, charset)
            if key is None or key == "":
                continue
            val: t.Any = None if options.strict_null_handling else ""
        else:
            raw_key = part[:pos]
            key = options.decode_key(raw_key, charset)
            if key is None or key == "":
                continue

            current_list_length = (
                len(accumulator[key]) if key in accumulator and isinstance(accumulator[key], (list, tuple)) else 0
            )
            parsed_value = _parse_array_value(part[pos + 1 :], options, current_list_length)
            if isinstance(parsed_value, (list, tuple)):
                val = [options.decode_value(item, charset) for item in parsed_value]
            else:
                val = options.decode_value(parsed_value, charset)

        if val and options.interpret_numeric_entities and charset == Charset.LATIN1:
            val = (
                re.sub(r"&#(\d+);", lambda match: chr(int(match.group(1))), val)
                if isinstance(val, str)
                else (
                    re.sub(r"&#(\d+);", lambda match: chr(int(match.group(1))), ",".join(map(str, val)))
                    if isinstance(val, (list, tuple))
                    else re.sub(r"&#(\d+);", lambda match: chr(int(match.group(1))), str(val))
                )
            )

        if parse_lists and pos != -1 and "[]=" in part and isinstance(val, (list, tuple)):
            raw_key_text = part[:pos]
            if not raw_key_text.endswith("[]"):
                val = [val]

        pairs.append((key, val))

        existing = key in accumulator
        if existing and options.duplicates == Duplicates.COMBINE:
            accumulator[key] = Utils.combine(accumulator[key], val, options)
        elif not existing or options.duplicates == Duplicates.LAST:
            accumulator[key] = val

    return pairs


def _mapping_to_pairs(value: Mapping[str, t.Any], options: DecodeOptions) -> t.List[t.Tuple[str, t.Any]]:
    pairs: t.List[t.Tuple[str, t.Any]] = []
    for key, item in value.items():
        parsed_value = _parse_array_value(item, options, 0)
        pairs.append((str(key), parsed_value))
    return pairs


def _has_mixed_root_collision(pairs: t.Sequence[t.Tuple[str, t.Any]], options: DecodeOptions) -> bool:
    flat_keys: t.Set[str] = set()
    structured_roots: t.Set[str] = set()
    allow_dots = bool(options.allow_dots)

    for key, _ in pairs:
        split_at = _first_structured_split_index(key, allow_dots)
        if split_at < 0:
            flat_keys.add(key)
            continue

        if split_at == 0:
            structured_roots.add(_leading_structured_root(key, options))
        else:
            structured_roots.add(key[:split_at])

    return bool(flat_keys & structured_roots)


def decode_with_rust(
    native_module: t.Any,
    value: t.Optional[t.Union[str, Mapping[str, t.Any]]],
    options: t.Optional[DecodeOptions] = None,
) -> t.Dict[str, t.Any]:
    """Decode via the native structured merge path while keeping Python semantics authoritative."""
    if not value:
        return {}

    if not isinstance(value, (str, Mapping)):
        raise ValueError("value must be a str or a Mapping[str, Any]")

    opts = options if options is not None else DecodeOptions()
    if opts.list_limit <= 0:
        return pure_decode(value, opts)

    if isinstance(value, str):
        parse_lists = _effective_parse_lists_for_string(value, opts)
        if not parse_lists:
            return pure_decode(value, opts)
        if bool(opts.allow_dots) and any(
            pattern in value for pattern in (".[", "%2E[", "%2e[", "%2E%5B", "%2E%5b", "%2e%5B", "%2e%5b")
        ):
            return pure_decode(value, opts)
        pairs_to_decode = _tokenize_string_pairs(value, opts, parse_lists=parse_lists)
        if _has_mixed_root_collision(pairs_to_decode, opts):
            return pure_decode(value, opts)
    else:
        pairs_to_decode = _mapping_to_pairs(value, opts)

    if not pairs_to_decode:
        return {}

    pool = _OpaqueLeafPool()
    pairs = [(key, _convert_decode_leaf(item, pool)) for key, item in pairs_to_decode]
    config = _normalize_decode_pairs_config(opts)
    if isinstance(value, str):
        config["parse_lists"] = True
    decoded = native_module.decode_pairs(pairs, config)
    restored = decoded if not pool.values_by_token else _restore_placeholders(decoded, pool)
    compacted = Utils.compact(restored)
    return t.cast(t.Dict[str, t.Any], compacted)
