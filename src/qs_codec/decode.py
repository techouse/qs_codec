"""A query string decoder (parser)."""

import re
import typing as t
from math import isinf

from regex import regex

from .enums.charset import Charset
from .enums.duplicates import Duplicates
from .enums.sentinel import Sentinel
from .models.decode_options import DecodeOptions
from .models.undefined import Undefined
from .utils.utils import Utils


def decode(
    value: t.Optional[t.Union[str, t.Mapping[str, t.Any]]],
    options: DecodeOptions = DecodeOptions(),
) -> t.Dict[str, t.Any]:
    """
    Decodes a query string into a ``Dict[str, Any]``.

    Providing custom ``DecodeOptions`` will override the default behavior.
    """
    obj: t.Dict[str, t.Any] = {}

    if not value:
        return obj

    if not isinstance(value, (str, dict)):
        raise ValueError("The input must be a String or a Dict")

    temp_obj: t.Optional[t.Dict[str, t.Any]] = (
        _parse_query_string_values(value, options) if isinstance(value, str) else value
    )

    if temp_obj is not None and options.parse_lists and 0 < options.list_limit < len(temp_obj):
        options.parse_lists = False

    # Iterate over the keys and setup the new object
    if temp_obj:
        for key, val in temp_obj.items():
            new_obj: t.Any = _parse_keys(key, val, options, isinstance(value, str))
            obj = Utils.merge(obj, new_obj, options)  # type: ignore [assignment]

    return Utils.compact(obj)


def _interpret_numeric_entities(value: str) -> str:
    return re.sub(r"&#(\d+);", lambda match: chr(int(match.group(1))), value)


def _parse_array_value(value: t.Any, options: DecodeOptions, current_list_length: int) -> t.Any:
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
    obj: t.Dict[str, t.Any] = {}

    clean_str: str = value.replace("?", "", 1) if options.ignore_query_prefix else value
    clean_str = clean_str.replace("%5B", "[").replace("%5b", "[").replace("%5D", "]").replace("%5d", "]")
    limit: t.Optional[int] = None if isinf(options.parameter_limit) else options.parameter_limit  # type: ignore [assignment]

    if limit is not None and limit <= 0:
        raise ValueError("Parameter limit must be a positive integer.")

    parts: t.List[str]
    if isinstance(options.delimiter, re.Pattern):
        parts = (
            re.split(options.delimiter, clean_str)
            if (limit is None) or not limit
            else re.split(options.delimiter, clean_str)[: (limit + 1 if options.raise_on_limit_exceeded else limit)]
        )
    else:
        parts = (
            clean_str.split(options.delimiter)
            if (limit is None) or not limit
            else clean_str.split(options.delimiter)[: (limit + 1 if options.raise_on_limit_exceeded else limit)]
        )

    if options.raise_on_limit_exceeded and (limit is not None) and len(parts) > limit:
        raise ValueError(f"Parameter limit exceeded: Only {limit} parameter{'' if limit == 1 else 's'} allowed.")

    skip_index: int = -1  # Keep track of where the utf8 sentinel was found
    i: int

    charset: Charset = options.charset

    if options.charset_sentinel:
        for i, _part in enumerate(parts):
            if _part.startswith("utf8="):
                if _part == Sentinel.CHARSET.encoded:
                    charset = Charset.UTF8
                elif _part == Sentinel.ISO.encoded:
                    charset = Charset.LATIN1
                skip_index = i
                break

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

        if "[]=" in part:
            val = [val] if isinstance(val, (list, tuple)) else val

        existing: bool = key in obj

        if existing and options.duplicates == Duplicates.COMBINE:
            obj[key] = Utils.combine(obj[key], val)
        elif not existing or options.duplicates == Duplicates.LAST:
            obj[key] = val

    return obj


def _parse_object(
    chain: t.Union[t.List[str], t.Tuple[str, ...]], val: t.Any, options: DecodeOptions, values_parsed: bool
) -> t.Any:
    current_list_length: int = 0

    if bool(chain) and chain[-1] == "[]":
        parent_key: t.Optional[int]

        try:
            parent_key = int("".join(chain[0:-1]))
        except ValueError:
            parent_key = None

        if parent_key is not None and isinstance(val, (list, tuple)) and parent_key in dict(enumerate(val)):
            current_list_length = len(val[parent_key])

    leaf: t.Any = val if values_parsed else _parse_array_value(val, options, current_list_length)

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

            clean_root: str = root[1:-1] if root.startswith("[") and root.endswith("]") else root

            decoded_root: str = clean_root.replace(r"%2E", ".") if options.decode_dot_in_keys else clean_root

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
    if not given_key:
        return

    # Transform dot notation to bracket notation
    key: str = re.sub(r"\.([^.[]+)", r"[\1]", given_key) if options.allow_dots else given_key

    # The regex chunks
    brackets: regex.Pattern[str] = regex.compile(r"\[(?:[^\[\]]|(?R))*\]")

    # Get the parent
    segment: t.Optional[regex.Match] = brackets.search(key) if options.depth > 0 else None
    parent: str = key[0 : segment.start()] if segment is not None else key

    # Stash the parent if it exists
    keys: t.List[str] = [parent] if parent else []

    # Loop through children appending to the array until we hit depth
    i: int = 0
    while options.depth > 0 and (segment := brackets.search(key)) is not None and i < options.depth:
        i += 1
        if segment is not None:
            keys.append(segment.group())
            # Update the key to start searching from the next position
            key = key[segment.end() :]

    # If there's a remainder, just add whatever is left
    if segment is not None:
        if options.strict_depth:
            raise IndexError(f"Input depth exceeded depth option of {options.depth} and strict_depth is True")
        keys.append(f"[{key[segment.start():]}]")

    return _parse_object(keys, val, options, values_parsed)
