import gc
import typing as t
from weakref import WeakKeyDictionary

import pytest

from qs_codec.models.weak_wrapper import WeakWrapper, _proxy_cache


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

    def test_wrapper_hash_stable_over_lifetime(self) -> None:
        # ensure that hash(w) == hash(w_copy) so lookups work
        v = {"a": {"b": 2}}
        w1 = WeakWrapper(v)
        w2 = WeakWrapper(v)
        assert hash(w1) == hash(w2)
        assert w1 == w2

    def test_wrappers_for_different_objects_are_not_equal(self) -> None:
        v1 = {"foo": "bar"}
        v2 = {"foo": "bar"}  # separate dict with identical content
        w1 = WeakWrapper(v1)
        w2 = WeakWrapper(v2)
        # Different identity  →  not equal
        assert w1 != w2
        # hashes match because contents match
        assert hash(w1) == hash(w2)

    def test_repr_includes_value_when_proxy_alive(self) -> None:
        wrapper = WeakWrapper({"k": "v"})
        text = repr(wrapper)
        assert text.startswith("WeakWrapper(") and "'v'" in text

    def test_hash_handles_sets(self) -> None:
        s1 = {"a", "b"}
        s2 = {"b", "a"}
        w1 = WeakWrapper(s1)
        w2 = WeakWrapper(s2)
        assert hash(w1) == hash(w2)

    def test_hash_fallback_uses_repr_for_unhashable_object(self) -> None:
        class Unhashable:
            __hash__ = None

            def __repr__(self) -> str:  # pragma: no cover - trivial repr
                return "<Unhashable>"

        wrapper = WeakWrapper(Unhashable())
        assert isinstance(hash(wrapper), int)

    def test_repr_after_proxy_collected_returns_placeholder(self) -> None:
        wrapper = WeakWrapper({"k": "v"})
        object.__setattr__(wrapper, "_wref", lambda: None)
        assert repr(wrapper) == "WeakWrapper(<gc'd>)"

    def test_eq_non_wrapper_returns_notimplemented(self) -> None:
        wrapper = WeakWrapper({})
        assert wrapper.__eq__(object()) is NotImplemented

    def test_hash_detects_circular_references(self) -> None:
        a: t.Dict[str, t.Any] = {}
        a["self"] = a
        wrapper = WeakWrapper(a)
        with pytest.raises(ValueError, match="Circular reference detected"):
            _ = hash(wrapper)

    def test_hash_detects_excessive_depth(self) -> None:
        # artificially create a super deep nested list
        deep = current = []
        for _ in range(401):  # 400 is the limit
            new_list = []
            current.append(new_list)
            current = new_list
        wrapper = WeakWrapper(deep)
        with pytest.raises(RecursionError):
            _ = hash(wrapper)

    def test_deleted_object_raises_reference_error_on_access(self) -> None:
        value: t.Dict[str, t.Any] = {"foo": "bar"}
        wrapper = WeakWrapper(value)

        # weak reference to the proxy object
        wref = wrapper._wref
        assert wref() is not None  # proxy alive

        # drop BOTH the original dict and the wrapper
        del value
        del wrapper
        gc.collect()

        # proxy should be gone now
        assert wref() is None

    def test_wrappers_share_same_proxy(self) -> None:
        d: t.Dict[str, t.Any] = {"k": "v"}
        w1 = WeakWrapper(d)
        w2 = WeakWrapper(d)

        # Same proxy instance means identity equality passes
        assert w1._proxy is w2._proxy
        assert w1 == w2

    def test_proxy_removed_when_all_wrappers_gone(self) -> None:
        d: t.Dict[str, t.Any] = {"k": "v"}
        wrapper = WeakWrapper(d)
        cache_key = id(d)

        # proxy is cached while a wrapper exists
        assert cache_key in _proxy_cache

        # remove every strong reference
        del d
        del wrapper
        gc.collect()

        # cache entry gone
        assert cache_key not in _proxy_cache

    def test_accessing_value_after_gc_raises_reference_error(self) -> None:
        d: t.Dict[str, t.Any] = {"k": "v"}
        wrapper = WeakWrapper(d)

        # Get the weak reference
        wref = wrapper._wref

        # Manually set the weak reference to None to simulate garbage collection
        # This is a bit of a hack, but it allows us to test the behavior
        object.__setattr__(wrapper, "_wref", lambda: None)

        # Accessing value should raise ReferenceError
        with pytest.raises(ReferenceError, match="Original object has been garbage-collected"):
            _ = wrapper.value

        # Restore the original weak reference to avoid affecting other tests
        object.__setattr__(wrapper, "_wref", wref)
