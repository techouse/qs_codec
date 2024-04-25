import typing as t
from weakref import WeakKeyDictionary

from qs_codec.models.weak_wrapper import WeakWrapper


class TestWeakrefWithDictKeys:
    def test_weak_key_dict_with_dict_keys(self) -> None:
        value: t.Dict[str, t.Any] = {"foo": "bar"}
        foo: WeakWrapper = WeakWrapper(value)
        foo_copy: WeakWrapper = WeakWrapper(value)
        assert foo == foo_copy
        d: WeakKeyDictionary = WeakKeyDictionary()
        d[foo] = 123
        assert d.get(foo) == 123
        assert d.get(foo_copy) == 123
        del foo
        assert len(d) == 0
        assert d.get(foo_copy) is None

    def test_weak_key_dict_with_nested_dict_keys(self) -> None:
        value: t.Dict[str, t.Any] = {"a": {"b": {"c": None}}}
        foo: WeakWrapper = WeakWrapper(value)
        foo_copy: WeakWrapper = WeakWrapper(value)
        assert foo == foo_copy
        d: WeakKeyDictionary = WeakKeyDictionary()
        d[foo] = 123
        assert d.get(foo) == 123
        assert d.get(foo_copy) == 123
        del foo
        assert len(d) == 0
        assert d.get(foo_copy) is None
