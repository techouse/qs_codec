"""
Utility helpers shared across the `qs_codec` decode/encode internals.

The functions in this module are intentionally small, allocation‑aware, and careful about container mutation to match the
behavior (and performance characteristics) of the original JavaScript `qs` library.

Key responsibilities:
- Merging decoded key/value pairs into nested Python containers (`merge`)
- Removing the library's `Undefined` sentinel values (`compact` and helpers)
- Minimal deep‑equality for cycle detection guards (`_dicts_are_equal`)
- Small helpers for list/value composition (`combine`, `apply`)
- Primitive checks used by the encoder (`is_non_nullish_primitive`)

Notes:
- `Undefined` marks entries that should be *omitted* from output structures. We remove these in place where possible to minimize allocations.
- Many helpers accept both `list` and `tuple`; tuples are converted to lists on mutation because Python tuples are immutable.
- Several routines use an object‑identity `visited` set to avoid infinite recursion when user inputs contain cycles.
"""

import typing as t
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

from ..models.decode_options import DecodeOptions
from ..models.overflow_dict import OverflowDict
from ..models.undefined import Undefined


def _numeric_key_pairs(mapping: t.Mapping[t.Any, t.Any]) -> t.List[t.Tuple[int, t.Any]]:
    """Return (numeric_key, original_key) for keys that coerce to int.

    Note: distinct keys like "01" and "1" both coerce to 1; downstream merges
    may overwrite earlier values when materializing numeric-keyed dicts.
    """
    pairs: t.List[t.Tuple[int, t.Any]] = []
    for key in mapping.keys():
        try:
            numeric_key = int(key)
        except (TypeError, ValueError):
            continue
        pairs.append((numeric_key, key))
    return pairs


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
    list_target: t.Dict[int, t.Any] = field(default_factory=dict)
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
        Merge `source` into `target` in a qs‑compatible way.

        This function mirrors how the original JavaScript `qs` library builds nested structures while parsing query strings.
        It accepts mappings, sequences (``list`` / ``tuple``), and scalars on either side and returns a merged value.

        Rules (high level)
        ------------------
        - If `source` is ``None``: return `target` unchanged.
        - If `source` is **not** a mapping:
          * `target` is a sequence → append/extend, skipping :class:`Undefined`.
          * `target` is a mapping → write items from the sequence under string indices ("0", "1", …).
          * otherwise → return ``[target, source]`` (skipping :class:`Undefined` where applicable).
        - If `source` **is** a mapping:
          * `target` is not a mapping → if `target` is a sequence, coerce it to an index‑keyed dict and merge; otherwise, concatenate as a list ``[target, source]`` while skipping :class:`Undefined`.
          * `target` is a mapping → deep‑merge keys; where keys collide, merge values recursively.

        List handling
        -------------
        When a list that already contains :class:`Undefined` must receive new values and ``options.parse_lists`` is ``False``,
        the list is promoted to a dict with string indices so positions can be addressed deterministically. Otherwise,
        sentinels are simply removed as we go.

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
        opts = options if options is not None else DecodeOptions()
        last_result: t.Any = None

        stack: t.List[_MergeFrame] = [_MergeFrame(target=target, source=source, options=opts)]

        while stack:
            frame = stack[-1]

            if frame.phase == "start":
                current_target = frame.target
                current_source = frame.source

                if current_source is None:
                    stack.pop()
                    last_result = current_target
                    continue

                if not isinstance(current_source, t.Mapping):
                    # Fast-path: merging a non-mapping (list/tuple/scalar) into target.
                    if isinstance(current_target, (list, tuple)):
                        # If the target sequence contains `Undefined`, we may need to promote it
                        # to a dict keyed by indices for stable writes.
                        if any(isinstance(el, Undefined) for el in current_target):
                            target_: t.Dict[int, t.Any] = dict(enumerate(current_target))

                            if isinstance(current_source, (list, tuple)):
                                for i, item in enumerate(current_source):
                                    if not isinstance(item, Undefined):
                                        target_[i] = item
                            else:
                                target_[len(target_)] = current_source

                            # When list parsing is disabled, collapse to a string-keyed dict and drop sentinels.
                            if not frame.options.parse_lists and any(
                                isinstance(value, Undefined) for value in target_.values()
                            ):
                                result: t.Any = {
                                    str(i): target_[i] for i in target_ if not isinstance(target_[i], Undefined)
                                }
                            else:
                                result = [el for el in target_.values() if not isinstance(el, Undefined)]
                            stack.pop()
                            last_result = result
                            continue

                        if isinstance(current_source, (list, tuple)):
                            if all(isinstance(el, (t.Mapping, Undefined)) for el in current_target) and all(
                                isinstance(el, (t.Mapping, Undefined)) for el in current_source
                            ):
                                frame.list_target = dict(enumerate(current_target))
                                frame.list_source = dict(enumerate(current_source))
                                frame.list_max_len = max(len(frame.list_target), len(frame.list_source))
                                frame.list_index = 0
                                frame.list_merged = []
                                frame.phase = "list_iter"
                                continue

                            mutable_target = (
                                list(current_target) if isinstance(current_target, tuple) else current_target
                            )
                            # Mutates in-place by design for list targets to preserve merge performance.
                            mutable_target.extend(el for el in current_source if not isinstance(el, Undefined))
                            stack.pop()
                            last_result = mutable_target
                            continue

                        mutable_target = list(current_target) if isinstance(current_target, tuple) else current_target
                        mutable_target.append(current_source)
                        stack.pop()
                        last_result = mutable_target
                        continue

                    if isinstance(current_target, t.Mapping):
                        if Utils.is_overflow(current_target):
                            stack.pop()
                            last_result = Utils.combine(current_target, current_source, frame.options)
                            continue

                        # Target is a mapping but source is a sequence — coerce indices to string keys.
                        if isinstance(current_source, (list, tuple)):
                            new_target = dict(current_target)
                            for i, item in enumerate(current_source):
                                if not isinstance(item, Undefined):
                                    new_target[str(i)] = item
                            stack.pop()
                            last_result = new_target
                            continue

                        stack.pop()
                        last_result = current_target
                        continue

                    if not isinstance(current_target, (list, tuple)) and isinstance(current_source, (list, tuple)):
                        stack.pop()
                        last_result = [
                            current_target,
                            *(el for el in current_source if not isinstance(el, Undefined)),
                        ]
                        continue

                    stack.pop()
                    last_result = [current_target, current_source]
                    continue

                # Source is a mapping but target is not — coerce target to a mapping or
                # concatenate as a list, then proceed.
                if current_target is None or not isinstance(current_target, t.Mapping):
                    if isinstance(current_target, (list, tuple)):
                        stack.pop()
                        last_result = {
                            **{
                                str(i): item for i, item in enumerate(current_target) if not isinstance(item, Undefined)
                            },
                            **current_source,
                        }
                        continue

                    if Utils.is_overflow(current_source):
                        source_of = t.cast(OverflowDict, current_source)
                        sorted_pairs = sorted(_numeric_key_pairs(source_of), key=lambda item: item[0])
                        numeric_keys = {key for _, key in sorted_pairs}
                        result = OverflowDict()
                        offset = 0
                        if not isinstance(current_target, Undefined):
                            result["0"] = current_target
                            offset = 1
                        for numeric_key, key in sorted_pairs:
                            val = source_of[key]
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
                    for element in (current_target,):
                        if not isinstance(element, Undefined):
                            result_list.append(element)
                    for element in (current_source,):
                        if not isinstance(element, Undefined):
                            result_list.append(element)
                    stack.pop()
                    last_result = result_list
                    continue

                # Prepare a mutable target we can merge into; reuse dict targets for performance.
                frame.merge_target = current_target if isinstance(current_target, dict) else dict(current_target)
                frame.merge_existing_keys = set(frame.merge_target.keys())
                frame.pending_updates = {}
                frame.source_items = list(current_source.items())
                frame.entry_index = 0
                frame.pending_key = None
                frame.phase = "map_iter"
                continue

            if frame.phase == "map_iter":
                merge_target = frame.merge_target
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
                    last_result = frame.list_merged
                    continue

                idx = frame.list_index
                frame.list_index += 1
                has_target = idx in frame.list_target
                has_source = idx in frame.list_source

                if has_target and has_source:
                    target_value = frame.list_target[idx]
                    source_value = frame.list_source[idx]

                    if isinstance(source_value, Undefined):
                        if not isinstance(target_value, Undefined):
                            frame.list_merged.append(target_value)
                        continue

                    frame.phase = "list_wait_child"
                    stack.append(_MergeFrame(target=target_value, source=source_value, options=frame.options))
                    continue

                if has_target:
                    target_value = frame.list_target[idx]
                    if not isinstance(target_value, Undefined):
                        frame.list_merged.append(target_value)
                elif has_source:
                    source_value = frame.list_source[idx]
                    if not isinstance(source_value, Undefined):
                        frame.list_merged.append(source_value)
                continue

            # frame.phase == "list_wait_child"
            frame.list_merged.append(last_result)
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
        # Depth‑first traversal without recursion.
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
                            )  # Mark before descending to avoid re‑pushing the same object through a cycle.
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
                            )  # Mark before descending to avoid re‑pushing the same object through a cycle.
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
            item = value[i]
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

        Any tuple values are converted to lists to allow in‑place pruning. Uses a lightweight cycle guard via
        `_dicts_are_equal` to avoid descending into the same mapping from itself.
        """
        # Snapshot keys so we can delete while iterating.
        keys: t.List[t.Any] = list(obj.keys())
        for key in keys:
            val = obj[key]
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

        This is not a general deep‑equality routine; it exists to prevent infinite recursion when structures point at
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
        else:
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

        If `list_limit` is exceeded, converts the list to an `OverflowDict`
        (a dict with numeric keys) to prevent memory exhaustion.
        When `options` is provided, its ``list_limit`` controls when a list is
        converted into an :class:`OverflowDict` (a dict with numeric keys) to
        prevent unbounded growth. If ``options`` is ``None``, the default
        ``list_limit`` from :class:`DecodeOptions` is used.
        A negative ``list_limit`` is treated as "overflow immediately": any
        non-empty combined result will be converted to :class:`OverflowDict`.
        This helper never raises an exception when the limit is exceeded; even
        if :class:`DecodeOptions` has ``raise_on_limit_exceeded`` set to
        ``True``, ``combine`` will still handle overflow only by converting the
        list to :class:`OverflowDict`.
        """
        if Utils.is_overflow(a):
            # a is already an OverflowDict. Append b to a *copy* at the next numeric index.
            # We assume sequential keys; len(a_copy) gives the next index.
            orig_a = t.cast(OverflowDict, a)
            a_copy = OverflowDict({k: v for k, v in orig_a.items() if not isinstance(v, Undefined)})
            # Use max key + 1 to handle sparse dicts safely, rather than len(a)
            key_pairs = _numeric_key_pairs(a_copy)
            idx = (max(key for key, _ in key_pairs) + 1) if key_pairs else 0

            if isinstance(b, (list, tuple)):
                for item in b:
                    if not isinstance(item, Undefined):
                        a_copy[str(idx)] = item
                        idx += 1
            elif Utils.is_overflow(b):
                b = t.cast(OverflowDict, b)
                # Iterate in numeric key order to preserve list semantics
                for _, k in sorted(_numeric_key_pairs(b), key=lambda item: item[0]):
                    val = b[k]
                    if not isinstance(val, Undefined):
                        a_copy[str(idx)] = val
                        idx += 1
            else:
                if not isinstance(b, Undefined):
                    a_copy[str(idx)] = b
            return a_copy

        # Normal combination: flatten lists/tuples
        # Flatten a
        if isinstance(a, (list, tuple)):
            list_a = [x for x in a if not isinstance(x, Undefined)]
        else:
            list_a = [a] if not isinstance(a, Undefined) else []

        # Flatten b, handling OverflowDict as a list source
        if isinstance(b, (list, tuple)):
            list_b = [x for x in b if not isinstance(x, Undefined)]
        elif Utils.is_overflow(b):
            b_of = t.cast(OverflowDict, b)
            list_b = [
                b_of[k]
                for _, k in sorted(_numeric_key_pairs(b_of), key=lambda item: item[0])
                if not isinstance(b_of[k], Undefined)
            ]
        else:
            list_b = [b] if not isinstance(b, Undefined) else []

        res = [*list_a, *list_b]

        list_limit = options.list_limit if options else DecodeOptions().list_limit
        if list_limit < 0:
            return OverflowDict({str(i): x for i, x in enumerate(res)}) if res else res
        if len(res) > list_limit:
            # Convert to OverflowDict
            return OverflowDict({str(i): x for i, x in enumerate(res)})

        return res

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
        - Any non‑container object is treated as primitive.

        This mirrors the behavior expected by the original `qs` encoder.
        """
        if val is None:
            return False

        if isinstance(val, str):
            return val != "" if skip_nulls else True

        if isinstance(val, (int, float, Decimal, bool, Enum, datetime, timedelta)):
            return True

        if isinstance(val, Undefined):
            return False

        if isinstance(val, object):
            if isinstance(val, (list, tuple, t.Mapping)):
                return False
            return True

        return False

    @staticmethod
    def normalize_comma_elem(e: t.Any) -> str:
        """Normalize a value for inclusion in a comma‑joined list."""
        if e is None:
            return ""
        if isinstance(e, bool):
            return "true" if e else "false"
        return str(e)
