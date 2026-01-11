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

import copy
import typing as t
from collections import deque
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

from ..models.decode_options import DecodeOptions
from ..models.undefined import Undefined


class OverflowDict(dict):
    """A dictionary subclass used to mark objects that have been converted from lists due to the `list_limit` being exceeded."""

    pass


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
        if source is None:
            # Nothing to merge — keep the original target as‑is.
            return target

        if options is None:
            # Use default decode options when none are provided.
            options = DecodeOptions()

        if not isinstance(source, t.Mapping):
            # Fast‑path: merging a non‑mapping (list/tuple/scalar) into target.
            if isinstance(target, (list, tuple)):
                # If the target sequence contains `Undefined`, we may need to promote it
                # to a dict keyed by string indices for stable writes.
                if any(isinstance(el, Undefined) for el in target):
                    # Create an index → value view so we can overwrite by position.
                    target_: t.Dict[int, t.Any] = dict(enumerate(target))

                    if isinstance(source, (list, tuple)):
                        for i, item in enumerate(source):
                            if not isinstance(item, Undefined):
                                target_[i] = item
                    else:
                        target_[len(target_)] = source

                    # When list parsing is disabled, collapse to a string‑keyed dict and drop sentinels.
                    if not options.parse_lists and any(isinstance(value, Undefined) for value in target_.values()):
                        target = {str(i): target_[i] for i in target_ if not isinstance(target_[i], Undefined)}
                    else:
                        target = [el for el in target_.values() if not isinstance(el, Undefined)]
                else:
                    if isinstance(source, (list, tuple)):
                        if all(isinstance(el, (t.Mapping, Undefined)) for el in target) and all(
                            isinstance(el, (t.Mapping, Undefined)) for el in source
                        ):
                            target_dict: t.Dict[int, t.Any] = dict(enumerate(target))
                            source_dict: t.Dict[int, t.Any] = dict(enumerate(source))
                            max_len = max(len(target_dict), len(source_dict))
                            merged_list: t.List[t.Any] = []
                            for i in range(max_len):
                                has_t = i in target_dict
                                has_s = i in source_dict
                                if has_t and has_s:
                                    merged_list.append(Utils.merge(target_dict[i], source_dict[i], options))
                                elif has_t:
                                    tv = target_dict[i]
                                    if not isinstance(tv, Undefined):
                                        merged_list.append(tv)
                                elif has_s:
                                    sv = source_dict[i]
                                    if not isinstance(sv, Undefined):
                                        merged_list.append(sv)
                            target = merged_list
                        else:
                            # Tuples are immutable; work with a list when mutating.
                            if isinstance(target, tuple):
                                target = list(target)
                            target.extend(el for el in source if not isinstance(el, Undefined))
                    elif source is not None:
                        # Tuples are immutable; work with a list when mutating.
                        if isinstance(target, tuple):
                            target = list(target)
                        target.append(source)
            elif isinstance(target, t.Mapping):
                if Utils.is_overflow(target):
                    return Utils.combine(target, source, options)

                # Target is a mapping but source is a sequence — coerce indices to string keys.
                if isinstance(source, (list, tuple)):
                    _new = dict(target)
                    for i, item in enumerate(source):
                        if not isinstance(item, Undefined):
                            _new[str(i)] = item
                    target = _new
            elif source is not None:
                if not isinstance(target, (list, tuple)) and isinstance(source, (list, tuple)):
                    return [target, *(el for el in source if not isinstance(el, Undefined))]
                return [target, source]

            return target

        # Source is a mapping but target is not — coerce target to a mapping or
        # concatenate as a list, then proceed.
        if target is None or not isinstance(target, t.Mapping):
            if isinstance(target, (list, tuple)):
                return {
                    **{str(i): item for i, item in enumerate(target) if not isinstance(item, Undefined)},
                    **source,
                }

            if Utils.is_overflow(source):
                source_of = t.cast(OverflowDict, source)
                sorted_pairs = sorted(Utils._numeric_key_pairs(source_of), key=lambda item: item[0])
                overflow_values = [source_of[k] for _, k in sorted_pairs]
                numeric_keys = {key for _, key in sorted_pairs}
                non_numeric_items = [(key, val) for key, val in source_of.items() if key not in numeric_keys]
                result = OverflowDict()
                offset = 0
                if not isinstance(target, Undefined):
                    result["0"] = target
                    offset = 1
                for (numeric_key, _), val in zip(sorted_pairs, overflow_values):
                    if not isinstance(val, Undefined):
                        result[str(numeric_key + offset)] = val
                for key, val in non_numeric_items:
                    if not isinstance(val, Undefined):
                        result[key] = val
                return result

            _res: t.List[t.Any] = []
            _iter1 = target if isinstance(target, (list, tuple)) else [target]
            for _el in _iter1:
                if not isinstance(_el, Undefined):
                    _res.append(_el)
            _iter2 = [source]
            for _el in _iter2:
                if not isinstance(_el, Undefined):
                    _res.append(_el)
            return _res

        # Prepare a mutable copy of the target we can merge into.
        is_overflow_target = Utils.is_overflow(target)
        merge_target: t.Dict[str, t.Any] = copy.deepcopy(target if isinstance(target, dict) else dict(target))

        # For overlapping keys, merge recursively; otherwise, take the new value.
        merged = {
            **merge_target,
            **{
                str(key): Utils.merge(merge_target[key], value, options) if key in merge_target else value
                for key, value in source.items()
            },
        }
        return OverflowDict(merged) if is_overflow_target else merged

    @staticmethod
    def compact(root: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
        """
        Remove all `Undefined` sentinels from a nested container in place.

        Traversal is iterative (explicit stack) to avoid deep recursion, and a per‑object `visited` set prevents infinite
        loops on cyclic inputs.

        Args:
            root: Dictionary to clean. It is mutated and also returned.

        Returns:
            The same `root` object for chaining.
        """
        # Depth‑first traversal without recursion.
        stack: deque[t.Union[t.Dict, t.List]] = deque([root])
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
    def _numeric_key_pairs(mapping: t.Mapping[t.Any, t.Any]) -> t.List[t.Tuple[int, t.Any]]:
        """Return (numeric_key, original_key) for keys that coerce to int."""
        pairs: t.List[t.Tuple[int, t.Any]] = []
        for key in mapping.keys():
            try:
                numeric_key = int(key)
            except (TypeError, ValueError):
                continue
            pairs.append((numeric_key, key))
        return pairs

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
        prevent unbounded growth. If ``options`` is ``None``, a default
        ``list_limit`` of ``20`` is used.
        A negative ``list_limit`` is treated as "overflow immediately": any
        non-empty combined result will be converted to :class:`OverflowDict`
        because ``len(res) > list_limit`` is then always true for ``len(res) >= 0``.
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
            key_pairs = Utils._numeric_key_pairs(a_copy)
            idx = (max(key for key, _ in key_pairs) + 1) if key_pairs else 0

            if isinstance(b, (list, tuple)):
                for item in b:
                    if not isinstance(item, Undefined):
                        a_copy[str(idx)] = item
                        idx += 1
            elif Utils.is_overflow(b):
                b = t.cast(OverflowDict, b)
                # Iterate in numeric key order to preserve list semantics
                for _, k in sorted(Utils._numeric_key_pairs(b), key=lambda item: item[0]):
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
                for _, k in sorted(Utils._numeric_key_pairs(b_of), key=lambda item: item[0])
                if not isinstance(b_of[k], Undefined)
            ]
        else:
            list_b = [b] if not isinstance(b, Undefined) else []

        res = [*list_a, *list_b]

        list_limit = options.list_limit if options else 20
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
