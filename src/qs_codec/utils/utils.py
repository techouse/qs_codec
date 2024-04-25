"""A collection of utility methods used by the library."""

import copy
import typing as t
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

from ..models.decode_options import DecodeOptions
from ..models.undefined import Undefined


class Utils:
    """A collection of utility methods used by the library."""

    @staticmethod
    def merge(
        target: t.Optional[t.Union[t.Mapping, t.List, t.Tuple]],
        source: t.Optional[t.Union[t.Mapping, t.List, t.Tuple, t.Any]],
        options: DecodeOptions = DecodeOptions(),
    ) -> t.Union[t.Dict, t.List, t.Tuple, t.Any]:
        """Merge two objects together."""
        if source is None:
            return target

        if not isinstance(source, t.Mapping):
            if isinstance(target, (list, tuple)):
                if any(isinstance(el, Undefined) for el in target):
                    target_: t.Dict[int, t.Any] = dict(enumerate(target))

                    if isinstance(source, (list, tuple)):
                        for i, item in enumerate(source):
                            if not isinstance(item, Undefined):
                                target_[i] = item
                    else:
                        target_[len(target_)] = source

                    target = list(filter(lambda el: not isinstance(el, Undefined), target_.values()))
                else:
                    if isinstance(source, (list, tuple)):
                        if all((isinstance(el, t.Mapping) or isinstance(el, Undefined)) for el in target) and all(
                            (isinstance(el, t.Mapping) or isinstance(el, Undefined)) for el in source
                        ):
                            target__: t.Dict[int, t.Any] = dict(enumerate(target))
                            target = list(
                                {
                                    i: Utils.merge(target__[i], item, options) if i in target__ else item
                                    for i, item in enumerate(source)
                                }.values()
                            )
                        else:
                            if isinstance(target, tuple):
                                target = list(target)
                            target.extend(filter(lambda el: not isinstance(el, Undefined), source))
                    elif source is not None:
                        if isinstance(target, tuple):
                            target = list(target)
                        target.append(source)
            elif isinstance(target, t.Mapping):
                if isinstance(source, (list, tuple)):
                    target = {
                        **target,
                        **{i: item for i, item in enumerate(source) if not isinstance(item, Undefined)},
                    }
            elif source is not None:
                if not isinstance(target, (list, tuple)) and isinstance(source, (list, tuple)):
                    return [target, *filter(lambda el: not isinstance(el, Undefined), source)]
                return [target, source]

            return target

        if target is None or not isinstance(target, t.Mapping):
            if isinstance(target, (list, tuple)):
                return {
                    **{i: item for i, item in enumerate(target) if not isinstance(item, Undefined)},
                    **source,
                }

            return [
                el
                for el in (target if isinstance(target, (list, tuple)) else [target])
                if not isinstance(el, Undefined)
            ] + [
                el
                for el in (source if isinstance(source, (list, tuple)) else [source])
                if not isinstance(el, Undefined)
            ]

        merge_target: t.Dict = (
            dict(enumerate(el for el in source if not isinstance(el, Undefined)))
            if isinstance(target, (list, tuple)) and not isinstance(source, (list, tuple))
            else copy.deepcopy(dict(target) if not isinstance(target, dict) else target)
        )

        return {
            **merge_target,
            **{
                key: Utils.merge(merge_target[key], value, options) if key in merge_target else value
                for key, value in source.items()
            },
        }

    @staticmethod
    def compact(value: t.Dict) -> t.Dict:
        """Remove all `Undefined` values from a dictionary."""
        queue: t.List[t.Dict] = [{"obj": {"o": value}, "prop": "o"}]
        refs: t.List = []

        for i in range(len(queue)):  # pylint: disable=C0200
            item: t.Mapping = queue[i]
            obj: t.Mapping = item["obj"][item["prop"]]

            keys: t.List = list(obj.keys())
            for _, key in enumerate(keys):
                val = obj[key]

                if (
                    val is not None
                    and not isinstance(val, Undefined)
                    and isinstance(val, t.Mapping)
                    and val not in refs
                ):
                    queue.append({"obj": obj, "prop": key})
                    refs.append(val)

        Utils._compact_queue(queue)
        Utils._remove_undefined_from_map(value)

        return value

    @staticmethod
    def _compact_queue(queue: t.List[t.Dict]) -> None:
        while len(queue) > 1:
            item = queue.pop()
            obj = item["obj"][item["prop"]]

            if isinstance(obj, (list, tuple)):
                item["obj"][item["prop"]] = list(filter(lambda el: not isinstance(el, Undefined), obj))

    @staticmethod
    def _remove_undefined_from_list(value: t.List) -> None:
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
    def _remove_undefined_from_map(obj: t.Dict) -> None:
        keys: t.List = list(obj.keys())
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
    def _dicts_are_equal(d1: t.Mapping, d2: t.Mapping, path=None) -> bool:
        if path is None:
            path = set()

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
    def combine(a: t.Union[t.Sequence, t.Any], b: t.Union[t.Sequence, t.Any]) -> t.List:
        """Combine two lists or values."""
        return [*(a if isinstance(a, (list, tuple)) else [a]), *(b if isinstance(b, (list, tuple)) else [b])]

    @staticmethod
    def apply(val: t.Union[t.Sequence, t.Any], fn: t.Callable) -> t.Union[t.List, t.Any]:
        """Apply a function to a value or a list of values."""
        return [fn(item) for item in val] if isinstance(val, (list, tuple)) else fn(val)

    @staticmethod
    def is_non_nullish_primitive(val: t.Any, skip_nulls: bool = False) -> bool:
        """Check if a value is a non-nullish primitive."""
        if val is None:
            return False

        if isinstance(val, str):
            return val != "" if skip_nulls else True

        if isinstance(val, (int, float, Decimal, bool, Enum, datetime, timedelta)):
            return True

        if isinstance(val, Undefined):
            return False

        if isinstance(val, object):
            if isinstance(val, (t.Sequence, t.Mapping)):
                return False
            return True

        return False
