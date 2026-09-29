"""
Utility helpers shared across the `qs_codec` decode/encode internals.

The functions in this module are intentionally small, allocation-aware, and careful about container mutation to match the
behavior (and performance characteristics) of the original JavaScript `qs` library.

Key responsibilities:
- Merging decoded key/value pairs into nested Python containers (`merge`)
- Removing the library's `Undefined` sentinel values (`compact` and helpers)
- Minimal deep-equality for cycle detection guards (`_dicts_are_equal`)
- Small helpers for list/value composition (`combine`, `apply`)
- Primitive checks used by the encoder (`is_non_nullish_primitive`)

Notes:
- `Undefined` marks entries that should be *omitted* from output structures. We remove these in place where possible to minimize allocations.
- Many helpers accept both `list` and `tuple`; tuples are converted to lists on mutation because Python tuples are immutable.
- Several routines use an object-identity `visited` set to avoid infinite recursion when user inputs contain cycles.
"""

import copy
import typing as t
from collections import deque
from collections.abc import Mapping as ABCMapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

from ..models.decode_options import DecodeOptions
from ..models.overflow_dict import CommaOverflowDict, OverflowDict
from ..models.undefined import Undefined


def _numeric_key_pairs(mapping: t.Mapping[t.Any, t.Any]) -> t.List[t.Tuple[int, t.Any]]:
    """Return (numeric_key, original_key) for keys that coerce to int.

    Note: distinct keys like "01" and "1" both coerce to 1; downstream merges
    may overwrite earlier values when materializing numeric-keyed dicts.
    """
    pairs: t.List[t.Tuple[int, t.Any]] = []
    for key in mapping:
        try:
            numeric_key = int(key)
        except (TypeError, ValueError):
            continue
        pairs.append((numeric_key, key))
    return pairs


def _copy_overflow_append_value(value: t.Any) -> t.Any:
    """Copy container values before storing them in an overflow append slot."""
    if isinstance(value, (ABCMapping, list, tuple)):
        return copy.copy(value)
    return value


def _enforce_list_limit(values: t.List[t.Any], options: DecodeOptions) -> t.Union[t.List[t.Any], OverflowDict]:
    """Return list values within the configured limit, or raise/degrade on overflow."""
    if not values or len(values) <= options.list_limit:
        return values
    if options.raise_on_limit_exceeded:
        limit = options.list_limit
        raise ValueError(f"List limit exceeded: Only {limit} element{'' if limit == 1 else 's'} allowed in a list.")
    return OverflowDict({str(i): value for i, value in enumerate(values) if not isinstance(value, Undefined)})


@dataclass
class _MergeFrame:
    target: t.Any
    source: t.Any
    options: DecodeOptions
    phase: str = "start"
    merge_target: t.Optional[t.MutableMapping[t.Any, t.Any]] = None
    merge_existing_keys: t.Set[t.Any] = field(default_factory=set)
    pending_updates: t.Dict[t.Any, t.Any] = field(default_factory=dict)
    source_items: t.List[t.Tuple[t.Any, t.Any]] = field(default_factory=list)
    entry_index: int = 0
    pending_key: t.Any = None
    list_source: t.Dict[int, t.Any] = field(default_factory=dict)
    list_max_len: int = 0
    list_index: int = 0
    list_merged: t.List[t.Any] = field(default_factory=list)


class Utils:
    """
    Namespace container for stateless utility routines.

    All methods are `@staticmethod`s to keep call sites simple and to make the functions easy to reuse across modules
    without constructing objects.
    """

    @staticmethod
    def merge(
        target: t.Optional[t.Union[t.Mapping[str, t.Any], t.List[t.Any], t.Tuple[t.Any]]],
        source: t.Optional[t.Union[t.Mapping[str, t.Any], t.List[t.Any], t.Tuple[t.Any], t.Any]],
        options: t.Optional[DecodeOptions] = None,
    ) -> t.Union[t.Dict[str, t.Any], t.List[t.Any], t.Tuple[t.Any], t.Any]:
        """
        Merge `source` into `target` in a qs-compatible way.

        This function mirrors how the original JavaScript `qs` library builds nested structures while parsing query strings.
        It accepts mappings, sequences (``list`` / ``tuple``), and scalars on either side and returns a merged value.

        Rules (high level)
        ------------------
        - If `source` is ``None``: return `target` unchanged.
        - If `source` is **not** a mapping:
          * `target` is a sequence → merge sequence positions or append a scalar, retaining sparse holes as needed.
          * `target` is a mapping → convert sequence positions to string keys ("0", "1", …) and deep-merge them.
          * otherwise → combine the values, retaining sequence holes until final compaction.
        - If `source` **is** a mapping:
          * `target` is not a mapping → if `target` is a sequence, coerce it to an index-keyed dict and merge;
            otherwise, concatenate as a list ``[target, source]`` while skipping :class:`Undefined`.
          * `target` is a mapping → deep-merge keys; where keys collide, merge values recursively.

        List handling
        -------------
        :class:`Undefined` entries model sparse-array holes. They may remain in intermediate lists so indices and
        ``list_limit`` checks match JavaScript array-length semantics. When ``options.parse_lists`` is ``False``, sparse
        lists are promoted to dicts with string indices. Public decoding calls :meth:`compact` before returning, which
        removes any retained placeholders; direct callers of :meth:`merge` may observe them in intermediate list results.

        Parameters
        ----------
        target : mapping | list | tuple | Any | None
            Existing value to merge into.
        source : mapping | list | tuple | Any | None
            Incoming value.
        options : DecodeOptions | None
            Options that affect list promotion/handling.

        Returns
        -------
        mapping | list | tuple | Any
            The merged structure. May be the original `target` object when
            `source` is ``None``.
        """
        opts: DecodeOptions = options if options is not None else DecodeOptions()
        last_result: t.Any = None

        stack: t.List[_MergeFrame] = [_MergeFrame(target=target, source=source, options=opts)]

        while stack:
            frame: _MergeFrame = stack[-1]

            if frame.phase == "start":
                current_target: t.Any = frame.target
                current_source: t.Any = frame.source

                if current_source is None:
                    stack.pop()
                    last_result = current_target
                    continue

                if not isinstance(current_source, ABCMapping):
                    # Fast-path: merging a non-mapping (list/tuple/scalar) into target.
                    if isinstance(current_target, (list, tuple)):
                        # If the target sequence contains `Undefined`, we may need to promote it
                        # to a dict keyed by indices for stable writes.
                        if not frame.options.parse_lists and any(isinstance(el, Undefined) for el in current_target):
                            target_by_index: t.Dict[int, t.Any] = dict(enumerate(current_target))

                            if isinstance(current_source, (list, tuple)):
                                for i, item in enumerate(current_source):
                                    if not isinstance(item, Undefined):
                                        target_by_index[i] = item
                            else:
                                target_by_index[len(target_by_index)] = current_source

                            # When list parsing is disabled, collapse to a string-keyed dict and drop sentinels.
                            if any(isinstance(value, Undefined) for value in target_by_index.values()):
                                result: t.Any = {
                                    str(i): target_by_index[i]
                                    for i in target_by_index
                                    if not isinstance(target_by_index[i], Undefined)
                                }
                            else:
                                result = [el for el in target_by_index.values() if not isinstance(el, Undefined)]
                            stack.pop()
                            last_result = (
                                _enforce_list_limit(result, frame.options) if isinstance(result, list) else result
                            )
                            continue

                        if isinstance(current_source, (list, tuple)):
                            frame.list_source = dict(enumerate(current_source))
                            frame.list_max_len = len(current_source)
                            frame.list_index = 0
                            frame.list_merged = list(current_target)
                            frame.phase = "list_iter"
                            continue

                        candidate = [*current_target, current_source]
                        enforced = _enforce_list_limit(candidate, frame.options)
                        if isinstance(enforced, OverflowDict):
                            stack.pop()
                            last_result = enforced
                            continue

                        mutable_target = list(current_target) if isinstance(current_target, tuple) else current_target
                        mutable_target.append(current_source)
                        stack.pop()
                        last_result = mutable_target
                        continue

                    if isinstance(current_target, ABCMapping):
                        if isinstance(current_source, (list, tuple)):
                            if Utils.is_overflow(current_target):
                                overflow_target = t.cast(OverflowDict, current_target)
                                frame.target = overflow_target.copy()
                            else:
                                frame.target = dict(current_target)
                            frame.source = {
                                str(i): item for i, item in enumerate(current_source) if not isinstance(item, Undefined)
                            }
                            continue

                        if Utils.is_overflow(current_target):
                            stack.pop()
                            last_result = Utils.combine(current_target, current_source, frame.options)
                            continue

                        if isinstance(current_source, Undefined) or current_source == "":
                            stack.pop()
                            last_result = current_target
                            continue

                        if frame.options.strict_merge:
                            stack.pop()
                            last_result = [dict(current_target), current_source]
                            continue

                        if isinstance(current_source, str):
                            new_target = dict(current_target)
                            new_target[current_source] = True
                            stack.pop()
                            last_result = new_target
                            continue

                        stack.pop()
                        last_result = [current_target, current_source]
                        continue

                    if not isinstance(current_target, (list, tuple)) and isinstance(current_source, (list, tuple)):
                        stack.pop()
                        last_result = _enforce_list_limit(
                            [current_target, *current_source],
                            frame.options,
                        )
                        continue

                    stack.pop()
                    last_result = [current_target, current_source]
                    continue

                # Source is a mapping but target is not — coerce target to a mapping or
                # concatenate as a list, then proceed.
                if current_target is None or not isinstance(current_target, ABCMapping):
                    if isinstance(current_target, (list, tuple)):
                        target_values = {
                            str(i): item for i, item in enumerate(current_target) if not isinstance(item, Undefined)
                        }
                        frame.target = (
                            OverflowDict(target_values) if Utils.is_overflow(current_source) else target_values
                        )
                        continue

                    if Utils.is_overflow(current_source):
                        source_of: OverflowDict = t.cast(OverflowDict, current_source)
                        sorted_pairs: t.List[t.Tuple[int, t.Any]] = sorted(
                            _numeric_key_pairs(source_of), key=lambda item: item[0]
                        )
                        numeric_keys: t.Set[str] = {key for _, key in sorted_pairs}
                        result = OverflowDict()
                        offset: int = 0
                        if not isinstance(current_target, Undefined):
                            result["0"] = current_target
                            offset = 1
                        for numeric_key, key in sorted_pairs:
                            val: t.Any = source_of[key]
                            if not isinstance(val, Undefined):
                                # Offset ensures target occupies index "0"; source indices shift up by 1.
                                result[str(numeric_key + offset)] = val
                        for key, val in source_of.items():
                            if key in numeric_keys:
                                continue
                            if not isinstance(val, Undefined):
                                result[key] = val
                        stack.pop()
                        last_result = result
                        continue

                    result_list: t.List[t.Any] = []
                    if not isinstance(current_target, Undefined):
                        result_list.append(current_target)
                    if not isinstance(current_source, Undefined):
                        result_list.append(current_source)
                    stack.pop()
                    last_result = _enforce_list_limit(result_list, frame.options)
                    continue

                # Prepare a mutable target we can merge into; reuse dict targets for performance.
                frame.merge_target = current_target if isinstance(current_target, dict) else dict(current_target)
                frame.merge_existing_keys = set(frame.merge_target)
                frame.pending_updates = {}
                frame.source_items = list(current_source.items())
                frame.entry_index = 0
                frame.pending_key = None
                frame.phase = "map_iter"
                continue

            if frame.phase == "map_iter":
                merge_target: t.Optional[t.MutableMapping[t.Any, t.Any]] = frame.merge_target
                if merge_target is None:  # pragma: no cover - internal invariant
                    raise RuntimeError("merge target is not initialized")  # noqa: TRY003

                if frame.entry_index >= len(frame.source_items):
                    if frame.pending_updates:
                        merge_target.update(frame.pending_updates)
                    stack.pop()
                    last_result = merge_target
                    continue

                key, value = frame.source_items[frame.entry_index]
                frame.entry_index += 1
                normalized_key = str(key)

                if key in frame.merge_existing_keys:
                    frame.pending_key = key
                    frame.phase = "map_wait_child"
                    stack.append(_MergeFrame(target=merge_target[key], source=value, options=frame.options))
                    continue
                if normalized_key in frame.merge_existing_keys:
                    frame.pending_key = normalized_key
                    frame.phase = "map_wait_child"
                    stack.append(_MergeFrame(target=merge_target[normalized_key], source=value, options=frame.options))
                    continue

                frame.pending_updates[key] = value
                continue

            if frame.phase == "map_wait_child":
                merge_target = frame.merge_target
                if merge_target is None:  # pragma: no cover - internal invariant
                    raise RuntimeError("merge target is not initialized")  # noqa: TRY003
                frame.pending_updates[frame.pending_key] = last_result
                frame.pending_key = None
                frame.phase = "map_iter"
                continue

            if frame.phase == "list_iter":
                if frame.list_index >= frame.list_max_len:
                    stack.pop()
                    enforced = _enforce_list_limit(frame.list_merged, frame.options)
                    if isinstance(frame.target, list) and isinstance(enforced, list):
                        frame.target[:] = enforced
                        last_result = frame.target
                    else:
                        last_result = enforced
                    continue

                idx = frame.list_index
                frame.list_index += 1
                source_value = frame.list_source[idx]
                if isinstance(source_value, Undefined):
                    continue

                has_target = idx < len(frame.list_merged) and not isinstance(frame.list_merged[idx], Undefined)
                if has_target:
                    target_value = frame.list_merged[idx]
                    if isinstance(target_value, ABCMapping) and isinstance(source_value, ABCMapping):
                        frame.phase = "list_wait_child"
                        stack.append(_MergeFrame(target=target_value, source=source_value, options=frame.options))
                    else:
                        frame.list_merged.append(source_value)
                    continue

                while len(frame.list_merged) <= idx:
                    frame.list_merged.append(Undefined())
                frame.list_merged[idx] = source_value
                continue

            # frame.phase == "list_wait_child"
            frame.list_merged[frame.list_index - 1] = last_result
            frame.phase = "list_iter"

        return last_result

    @staticmethod
    def compact(root: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
        """
        Remove all `Undefined` sentinels from a nested container in place.

        Traversal is iterative (explicit stack) to avoid deep recursion, and a per-object `visited` set prevents infinite
        loops on cyclic inputs.

        Args:
            root: Dictionary to clean. It is mutated and also returned.

        Returns:
            The same `root` object for chaining.
        """
        # Depth-first traversal without recursion.
        stack: t.Deque[t.Union[t.Dict, t.List]] = deque([root])
        # Track object identities to avoid revisiting in cycles.
        visited: t.Set[int] = {id(root)}

        while stack:
            node: t.Union[t.Dict, t.List] = stack.pop()
            if isinstance(node, dict):
                # Copy keys so we can delete from the dict during iteration.
                for k in list(node.keys()):
                    v: object = node[k]
                    # Library sentinel: drop this key entirely.
                    if isinstance(v, Undefined):
                        del node[k]
                    elif isinstance(v, (dict, list)):
                        if id(v) not in visited:
                            visited.add(
                                id(v)
                            )  # Mark before descending to avoid re-pushing the same object through a cycle.
                            stack.append(v)
            elif isinstance(node, list):
                # Manual index loop since we may delete elements while iterating.
                i: int = 0
                while i < len(node):
                    v = node[i]
                    if isinstance(v, Undefined):
                        del node[i]
                    else:
                        if isinstance(v, (dict, list)) and id(v) not in visited:
                            visited.add(
                                id(v)
                            )  # Mark before descending to avoid re-pushing the same object through a cycle.
                            stack.append(v)
                        i += 1
        return root

    @staticmethod
    def _remove_undefined_from_list(value: t.List[t.Any]) -> None:
        """
        Recursively remove `Undefined` from a list in place.

        Tuples encountered inside the list are converted to lists so they can be pruned or further traversed.
        """
        i: int = len(value) - 1
        while i >= 0:
            item: t.Any = value[i]
            if isinstance(item, Undefined):
                value.pop(i)
            elif isinstance(item, dict):
                Utils._remove_undefined_from_map(item)
            elif isinstance(item, list):
                Utils._remove_undefined_from_list(item)
            elif isinstance(item, tuple):
                value[i] = list(item)
                Utils._remove_undefined_from_list(value[i])
            i -= 1

    @staticmethod
    def _remove_undefined_from_map(obj: t.Dict[t.Any, t.Any]) -> None:
        """
        Recursively remove `Undefined` from a mapping in place.

        Any tuple values are converted to lists to allow in-place pruning. Uses a lightweight cycle guard via
        `_dicts_are_equal` to avoid descending into the same mapping from itself.
        """
        # Snapshot keys so we can delete while iterating.
        keys: t.List[t.Any] = list(obj)
        for key in keys:
            val: t.Any = obj[key]
            if isinstance(val, Undefined):
                obj.pop(key)
            elif isinstance(val, dict) and not Utils._dicts_are_equal(val, obj):
                Utils._remove_undefined_from_map(val)
            elif isinstance(val, list):
                Utils._remove_undefined_from_list(val)
            elif isinstance(val, tuple):
                obj[key] = list(val)
                Utils._remove_undefined_from_list(obj[key])

    @staticmethod
    def _dicts_are_equal(
        d1: t.Mapping[t.Any, t.Any],
        d2: t.Mapping[t.Any, t.Any],
        path: t.Optional[t.Set[t.Any]] = None,
    ) -> bool:
        """
        Minimal deep equality helper with cycle guarding.

        This is not a general deep-equality routine; it exists to prevent infinite recursion when structures point at
        themselves. If both inputs are dicts, we compare keys and recurse into values; otherwise we fall back to `==`.

        Args:
            d1, d2: Structures to compare.
            path: Internal identity set used to detect cycles.

        Returns:
            True if considered equal, or if a cycle is detected on either side.
        """
        # Lazily create the identity set used for cycle detection.
        if path is None:
            path = set()

        # If we've seen either mapping at this level, treat as equal to break cycles.
        if id(d1) in path or id(d2) in path:
            return True

        path.add(id(d1))
        path.add(id(d2))

        if isinstance(d1, dict) and isinstance(d2, dict):
            if len(d1) != len(d2):
                return False
            for k, v in d1.items():
                if k not in d2:
                    return False
                if not Utils._dicts_are_equal(v, d2[k], path):
                    return False
            return True
        return d1 == d2

    @staticmethod
    def is_overflow(obj: t.Any) -> bool:
        """Check if an object is an OverflowDict."""
        return isinstance(obj, OverflowDict)

    @staticmethod
    def combine(
        a: t.Union[t.List[t.Any], t.Tuple[t.Any], t.Any],
        b: t.Union[t.List[t.Any], t.Tuple[t.Any], t.Any],
        options: t.Optional[DecodeOptions] = None,
    ) -> t.Union[t.List[t.Any], t.Dict[str, t.Any]]:
        """
        Concatenate two values, treating non-sequences as singletons.

        Normal list/tuple inputs are flattened into the combined result. When
        ``a`` is already an :class:`OverflowDict`, top-level list/tuple elements
        from ``b`` are appended at successive numeric keys; a nested list remains
        one group, and an incoming overflow mapping remains one copied value.

        If `list_limit` is exceeded, converts the list to an `OverflowDict`
        (a dict with numeric keys) to prevent memory exhaustion.
        When `options` is provided, its ``list_limit`` controls when a list is
        converted into an :class:`OverflowDict` (a dict with numeric keys) to
        prevent unbounded growth. If ``options`` is ``None``, the default
        ``list_limit`` from :class:`DecodeOptions` is used.
        A negative ``list_limit`` is treated as "overflow immediately": any
        non-empty combined result will be converted to :class:`OverflowDict`.
        When :attr:`DecodeOptions.raise_on_limit_exceeded` is ``True``, an
        over-limit result raises ``ValueError`` instead of being converted.
        """
        if Utils.is_overflow(a):
            if options is not None and options.raise_on_limit_exceeded:
                limit = options.list_limit
                raise ValueError(
                    f"List limit exceeded: Only {limit} element{'' if limit == 1 else 's'} allowed in a list."
                )
            # Copy on write; append top-level values after the highest numeric index.
            orig_a: OverflowDict = t.cast(OverflowDict, a)
            a_copy: OverflowDict = orig_a.__class__({k: v for k, v in orig_a.items() if not isinstance(v, Undefined)})
            # Use max key + 1 to handle sparse dicts safely, rather than len(a)
            key_pairs: t.List[t.Tuple[int, str]] = _numeric_key_pairs(a_copy)
            idx: int = (max(key for key, _ in key_pairs) + 1) if key_pairs else 0

            for value in b if isinstance(b, (list, tuple)) else (b,):
                if not isinstance(value, Undefined):
                    a_copy[str(idx)] = _copy_overflow_append_value(value)
                    idx += 1
            return a_copy

        # Normal combination: flatten lists/tuples
        # Flatten a
        if isinstance(a, (list, tuple)):
            list_a: t.List[t.Any] = [x for x in a if not isinstance(x, Undefined)]
        else:
            list_a = [a] if not isinstance(a, Undefined) else []

        # Flatten b, handling OverflowDict as a list source
        if isinstance(b, (list, tuple)):
            list_b: t.List[t.Any] = [x for x in b if not isinstance(x, Undefined)]
        elif isinstance(b, CommaOverflowDict):
            list_b = [b]
        elif Utils.is_overflow(b):
            b_of: OverflowDict = t.cast(OverflowDict, b)
            list_b = [
                b_of[k]
                for _, k in sorted(_numeric_key_pairs(b_of), key=lambda item: item[0])
                if not isinstance(b_of[k], Undefined)
            ]
        else:
            list_b = [b] if not isinstance(b, Undefined) else []

        res: t.List[t.Any] = [*list_a, *list_b]

        return _enforce_list_limit(res, options if options is not None else DecodeOptions())

    @staticmethod
    def apply(
        val: t.Union[t.List[t.Any], t.Tuple[t.Any], t.Any],
        fn: t.Callable,
    ) -> t.Union[t.List[t.Any], t.Any]:
        """
        Map a callable over a value or sequence.

        If `val` is a list/tuple, returns a list of mapped results; otherwise returns
        the single mapped value.
        """
        return [fn(item) for item in val] if isinstance(val, (list, tuple)) else fn(val)

    @staticmethod
    def is_non_nullish_primitive(val: t.Any, skip_nulls: bool = False) -> bool:
        """
        Return True if `val` is considered a primitive for encoding purposes.

        Rules:
        - `None` and `Undefined` are not primitives.
        - Strings are primitives; if `skip_nulls` is True, the empty string is not.
        - Numbers, booleans, `Enum`, `datetime`, and `timedelta` are primitives.
        - Any non-container object is treated as primitive.

        This mirrors the behavior expected by the original `qs` encoder.
        """
        if val is None:
            return False

        if isinstance(val, Undefined):
            return False

        if isinstance(val, str):
            return val != "" if skip_nulls else True

        if isinstance(val, (int, float, Decimal, bool, Enum, datetime, timedelta)):
            return True

        if isinstance(val, (list, tuple, dict)):
            return False

        if isinstance(val, ABCMapping):
            return False

        # Opaque custom types are treated as primitives; keep the explicit fallback
        # check for compatibility with tests that monkeypatch `isinstance`.
        return isinstance(val, object)

    @staticmethod
    def normalize_comma_elem(e: t.Any) -> str:
        """Normalize a value for inclusion in a comma-joined list."""
        if e is None:
            return ""
        if isinstance(e, bool):
            return "true" if e else "false"
        return str(e)
