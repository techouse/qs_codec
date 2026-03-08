"""Mutable traversal frame for iterative encoding."""

import typing as t
from datetime import datetime
from weakref import WeakKeyDictionary

from ..constants.encode_constants import PHASE_START
from ..enums.charset import Charset
from ..enums.format import Format
from ..models.key_path_node import KeyPathNode
from .cycle_state import CycleState


class EncodeFrame:
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
    values: t.Optional[t.List[t.Any]]
    index: int
    adjusted_path: t.Optional[KeyPathNode]
    cycle_state: t.Optional[CycleState]
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
        cycle_state: t.Optional[CycleState] = None,
        cycle_level: t.Optional[int] = None,
    ) -> None:
        """Initialize an EncodeFrame with the given parameters."""
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
        self.phase = PHASE_START
        self.obj = None
        self.obj_id = None
        self.is_mapping = False
        self.is_sequence = False
        self.step = 0
        self.obj_keys = []
        self.values = None
        self.index = 0
        self.adjusted_path = None
        self.cycle_state = cycle_state
        self.cycle_level = cycle_level
        self.cycle_pushed = False
