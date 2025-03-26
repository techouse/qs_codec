"""A query string encoder (stringifier)."""

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
from .models.undefined import Undefined
from .models.weak_wrapper import WeakWrapper
from .utils.utils import Utils


def encode(value: t.Any, options: EncodeOptions = EncodeOptions()) -> str:
    """
    Encodes an object into a query string.

    Providing custom ``EncodeOptions`` will override the default behavior.
    """
    if value is None:
        return ""

    obj: t.Mapping[str, t.Any]
    if isinstance(value, t.Mapping):
        obj = deepcopy(value)
    elif isinstance(value, (list, tuple)):
        obj = {str(key): value for key, value in enumerate(value)}
    else:
        obj = {}

    keys: t.List[t.Any] = []

    if not obj:
        return ""

    obj_keys: t.Optional[t.List[t.Any]] = None

    if options.filter is not None:
        if callable(options.filter):
            obj = options.filter("", obj)
        elif isinstance(options.filter, (list, tuple)):
            obj_keys = list(options.filter)

    comma_round_trip: bool = options.list_format == ListFormat.COMMA and options.comma_round_trip is True

    if obj_keys is None:
        obj_keys = list(obj.keys())

    if options.sort is not None and callable(options.sort):
        obj_keys = sorted(obj_keys, key=cmp_to_key(options.sort))

    side_channel: WeakKeyDictionary = WeakKeyDictionary()

    for _key in obj_keys:
        if not isinstance(_key, str):
            continue
        if _key in obj and obj.get(_key) is None and options.skip_nulls:
            continue

        _encoded: t.Union[t.List[t.Any], t.Tuple[t.Any, ...], t.Any] = _encode(
            value=obj.get(_key),
            is_undefined=_key not in obj,
            side_channel=side_channel,
            prefix=_key,
            generate_array_prefix=options.list_format.generator,
            comma_round_trip=comma_round_trip,
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

        if isinstance(_encoded, (list, tuple)):
            keys.extend(_encoded)
        else:
            keys.append(_encoded)

    joined: str = options.delimiter.join(keys)
    prefix: str = "?" if options.add_query_prefix else ""

    if options.charset_sentinel:
        if options.charset == Charset.LATIN1:
            prefix += f"{Sentinel.ISO.encoded}&"
        elif options.charset == Charset.UTF8:
            prefix += f"{Sentinel.CHARSET.encoded}&"
        else:
            raise ValueError("Invalid charset")

    return prefix + joined if joined else ""


_sentinel: WeakWrapper = WeakWrapper({})


def _encode(
    value: t.Any,
    is_undefined: bool,
    side_channel: WeakKeyDictionary,
    prefix: t.Optional[str],
    comma_round_trip: t.Optional[bool],
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
    if prefix is None:
        prefix = "?" if add_query_prefix else ""

    if comma_round_trip is None:
        comma_round_trip = generate_array_prefix == ListFormat.COMMA.generator

    if formatter is None:
        formatter = format.formatter

    obj: t.Any = deepcopy(value)

    tmp_sc: t.Optional[WeakKeyDictionary] = side_channel
    step: int = 0
    find_flag: bool = False

    while (tmp_sc := tmp_sc.get(_sentinel)) and not find_flag:  # type: ignore [union-attr]
        # Where value last appeared in the ref tree
        pos: t.Optional[int] = tmp_sc.get(WeakWrapper(value))
        step += 1
        if pos is not None:
            if pos == step:
                raise ValueError("Circular reference detected")
            else:
                find_flag = True  # Break while
        if tmp_sc.get(_sentinel) is None:
            step = 0

    if callable(filter):
        obj = filter(prefix, obj)
    elif isinstance(obj, datetime):
        obj = serialize_date(obj) if callable(serialize_date) else obj.isoformat()
    elif generate_array_prefix == ListFormat.COMMA.generator and isinstance(obj, (list, tuple)):
        obj = Utils.apply(
            obj,
            lambda val: (
                (serialize_date(val) if callable(serialize_date) else val.isoformat())
                if isinstance(val, datetime)
                else val
            ),
        )

    if not is_undefined and obj is None:
        if strict_null_handling:
            return encoder(prefix, charset, format) if callable(encoder) and not encode_values_only else prefix

        obj = ""

    if Utils.is_non_nullish_primitive(obj, skip_nulls) or isinstance(obj, bytes):
        if callable(encoder):
            key_value = prefix if encode_values_only else encoder(prefix, charset, format)
            return [f"{formatter(key_value)}={formatter(encoder(obj, charset, format))}"]

        return [f"{formatter(prefix)}={formatter(str(obj))}"]

    values: t.List[t.Any] = []

    if is_undefined:
        return values

    obj_keys: t.List[t.Any]
    if generate_array_prefix == ListFormat.COMMA.generator and isinstance(obj, (list, tuple)):
        # we need to join elements in
        if encode_values_only and callable(encoder):
            obj = Utils.apply(obj, encoder)

        if obj:
            obj_keys_value = ",".join([str(e) if e is not None else "" for e in obj])
            obj_keys = [{"value": obj_keys_value if obj_keys_value else None}]
        else:
            obj_keys = [{"value": Undefined()}]
    elif isinstance(filter, (list, tuple)):
        obj_keys = list(filter)
    else:
        keys: t.List[t.Any]
        if isinstance(obj, t.Mapping):
            keys = list(obj.keys())
        elif isinstance(obj, (list, tuple)):
            keys = [index for index in range(len(obj))]
        else:
            keys = []

        obj_keys = sorted(keys, key=cmp_to_key(sort)) if sort is not None else list(keys)

    encoded_prefix: str = prefix.replace(".", "%2E") if encode_dot_in_keys else prefix

    adjusted_prefix: str = (
        f"{encoded_prefix}[]"
        if comma_round_trip and isinstance(obj, (list, tuple)) and len(obj) == 1
        else encoded_prefix
    )

    if allow_empty_lists and isinstance(obj, (list, tuple)) and not obj:
        return [f"{adjusted_prefix}[]"]

    for _key in obj_keys:
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

        if skip_nulls and _value is None:
            continue

        encoded_key: str = str(_key).replace(".", "%2E") if allow_dots and encode_dot_in_keys else str(_key)

        key_prefix: str = (
            generate_array_prefix(adjusted_prefix, encoded_key)
            if isinstance(obj, (list, tuple))
            else f"{adjusted_prefix}{f'.{encoded_key}' if allow_dots else f'[{encoded_key}]'}"
        )

        side_channel[WeakWrapper(value)] = step
        value_side_channel: WeakKeyDictionary = WeakKeyDictionary()
        value_side_channel[_sentinel] = side_channel

        encoded: t.Union[t.List[t.Any], t.Tuple[t.Any, ...], t.Any] = _encode(
            value=_value,
            is_undefined=_value_undefined,
            side_channel=value_side_channel,
            prefix=key_prefix,
            comma_round_trip=comma_round_trip,
            encoder=(
                None
                if generate_array_prefix == ListFormat.COMMA.generator
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

        if isinstance(encoded, (list, tuple)):
            values.extend(encoded)
        else:
            values.append(encoded)

    return values
