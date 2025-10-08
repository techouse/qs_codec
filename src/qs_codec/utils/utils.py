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

            _res: t.List[t.Any] = []
            _iter1 = target if isinstance(target, (list, tuple)) else [target]
            for _el in _iter1:
                if not isinstance(_el, Undefined):
                    _res.append(_el)
            _iter2 = source if isinstance(source, (list, tuple)) else [source]
            for _el in _iter2:
                if not isinstance(_el, Undefined):
                    _res.append(_el)
            return _res

        # Prepare a mutable copy of the target we can merge into.
        merge_target: t.Dict[str, t.Any] = copy.deepcopy(target if isinstance(target, dict) else dict(target))

        # For overlapping keys, merge recursively; otherwise, take the new value.
        return {
            **merge_target,
            **{
                str(key): Utils.merge(merge_target[key], value, options) if key in merge_target else value
                for key, value in source.items()
            },
        }

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
    def combine(
        a: t.Union[t.List[t.Any], t.Tuple[t.Any], t.Any],
        b: t.Union[t.List[t.Any], t.Tuple[t.Any], t.Any],
    ) -> t.List[t.Any]:
        """
        Concatenate two values, treating non‑sequences as singletons.

        Returns a new `list`; tuples are expanded but not preserved as tuples.
        """
        return [*(a if isinstance(a, (list, tuple)) else [a]), *(b if isinstance(b, (list, tuple)) else [b])]

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
