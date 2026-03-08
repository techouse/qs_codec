import copy
import inspect
import queue
import sys
import threading
import time
import typing as t

import pytest

from qs_codec import DecodeOptions, Duplicates, EncodeOptions, ListFormat, decode, encode
from qs_codec.models.key_path_node import KeyPathNode
from qs_codec.models.weak_wrapper import WeakWrapper, _proxy_cache

IS_PYPY_38: bool = sys.implementation.name == "pypy" and sys.version_info[:2] == (3, 8)
THREAD_COUNT: int = 8
ITERATION_COUNT: int = 100 if IS_PYPY_38 else 250
HEAVY_ENCODE_ITERATION_COUNT: int = 25 if IS_PYPY_38 else ITERATION_COUNT
JOIN_TIMEOUT_SECONDS: float = 60.0 if IS_PYPY_38 else 30.0


def _run_concurrently(
    worker: t.Callable[[queue.Queue], None],
    *,
    thread_count: int = THREAD_COUNT,
    join_timeout: float = JOIN_TIMEOUT_SECONDS,
) -> t.List[t.Any]:
    start_barrier = threading.Barrier(thread_count)
    results: "queue.Queue[t.Any]" = queue.Queue()
    errors: "queue.Queue[BaseException]" = queue.Queue()
    threads: t.List[threading.Thread] = []

    def run_worker() -> None:
        try:
            start_barrier.wait()
            worker(results)
        except BaseException as exc:  # pragma: no cover - assertion path
            errors.put(exc)

    for index in range(thread_count):
        thread = threading.Thread(target=run_worker, name="thread-safety-%d" % index, daemon=True)
        thread.start()
        threads.append(thread)

    deadline = time.monotonic() + join_timeout
    for thread in threads:
        remaining = deadline - time.monotonic()
        if remaining > 0:
            thread.join(remaining)

    alive_threads = [thread.name for thread in threads if thread.is_alive()]
    if alive_threads:
        pytest.fail("worker threads did not finish: %s" % ", ".join(alive_threads))

    if not errors.empty():
        exc = errors.get()
        raise AssertionError("worker thread failed") from exc

    collected: t.List[t.Any] = []
    while not results.empty():
        collected.append(results.get())
    return collected


class TestThreadSafety:
    def test_encode_signature_uses_none_default(self) -> None:
        signature = inspect.signature(encode)
        assert signature.parameters["options"].default is None

    def test_concurrent_weakwrapper_same_payload_is_stable(self) -> None:
        payload = {"alpha": {"beta": ["gamma"]}}

        def worker(results: queue.Queue) -> None:
            local_wrappers: t.List[WeakWrapper] = []
            for _ in range(ITERATION_COUNT):
                wrapper = WeakWrapper(payload)
                local_wrappers.append(wrapper)
                results.put(wrapper)
            results.put(local_wrappers)

        raw_results = _run_concurrently(worker)

        wrappers: t.List[WeakWrapper] = []
        retained_wrapper_lists: t.List[t.List[WeakWrapper]] = []
        for item in raw_results:
            if isinstance(item, WeakWrapper):
                wrappers.append(item)
            else:
                retained_wrapper_lists.append(t.cast(t.List[WeakWrapper], item))

        assert len(wrappers) == THREAD_COUNT * ITERATION_COUNT
        assert len(retained_wrapper_lists) == THREAD_COUNT
        assert id(payload) in _proxy_cache

        first_wrapper = wrappers[0]
        first_hash = hash(first_wrapper)
        for wrapper in wrappers[1:]:
            assert wrapper == first_wrapper
            assert hash(wrapper) == first_hash

    def test_concurrent_key_path_node_lazy_caches_are_stable(self) -> None:
        path = KeyPathNode.from_materialized("user.name").append("[a.b]").append(".tail")
        expected_materialized = "user.name[a.b].tail"
        expected_dot_materialized = "user%2Ename[a%2Eb]%2Etail"

        def worker(results: queue.Queue) -> None:
            for _ in range(ITERATION_COUNT):
                results.put((path.materialize(), path.as_dot_encoded().materialize()))

        raw_results = _run_concurrently(worker)

        assert len(raw_results) == THREAD_COUNT * ITERATION_COUNT
        for materialized, dot_materialized in raw_results:
            assert materialized == expected_materialized
            assert dot_materialized == expected_dot_materialized

        cached_dot_path = path.as_dot_encoded()
        assert cached_dot_path.materialize() == expected_dot_materialized
        assert path.as_dot_encoded() is cached_dot_path

    def test_concurrent_encode_with_default_options_is_stable(self) -> None:
        payload = {"a": "b", "c": ["d", "e"], "f": {"g": "h"}}
        expected = "a=b&c%5B0%5D=d&c%5B1%5D=e&f%5Bg%5D=h"
        payload_snapshot = copy.deepcopy(payload)

        def worker(results: queue.Queue) -> None:
            for _ in range(HEAVY_ENCODE_ITERATION_COUNT):
                results.put(encode(payload))

        raw_results = _run_concurrently(worker)

        assert len(raw_results) == THREAD_COUNT * HEAVY_ENCODE_ITERATION_COUNT
        assert all(result == expected for result in raw_results)
        assert payload == payload_snapshot

    def test_concurrent_encode_with_shared_options_is_stable(self) -> None:
        payload = {"a": ["x y", "z"], "b": "c=d"}
        shared_options = EncodeOptions(encode_values_only=True, list_format=ListFormat.REPEAT)
        expected = "a=x%20y&a=z&b=c%3Dd"
        payload_snapshot = copy.deepcopy(payload)
        shared_options_snapshot = copy.deepcopy(shared_options)

        def worker(results: queue.Queue) -> None:
            for _ in range(HEAVY_ENCODE_ITERATION_COUNT):
                results.put(encode(payload, shared_options))

        raw_results = _run_concurrently(worker)

        assert len(raw_results) == THREAD_COUNT * HEAVY_ENCODE_ITERATION_COUNT
        assert all(result == expected for result in raw_results)
        assert payload == payload_snapshot
        assert shared_options == shared_options_snapshot

    def test_concurrent_decode_with_shared_options_is_stable(self) -> None:
        query = "a.b=c&a.b=d&x%5By%5D=z"
        shared_options = DecodeOptions(allow_dots=True, duplicates=Duplicates.COMBINE)
        expected = {"a": {"b": ["c", "d"]}, "x": {"y": "z"}}
        shared_options_snapshot = copy.deepcopy(shared_options)

        def worker(results: queue.Queue) -> None:
            for _ in range(ITERATION_COUNT):
                results.put(decode(query, shared_options))

        raw_results = _run_concurrently(worker)

        assert len(raw_results) == THREAD_COUNT * ITERATION_COUNT
        assert all(result == expected for result in raw_results)
        assert shared_options == shared_options_snapshot

    def test_concurrent_encode_and_decode_together_are_stable(self) -> None:
        encode_payload = {"a": "b", "c": ["d", "e"], "f": {"g": "h"}}
        encode_expected = "a=b&c%5B0%5D=d&c%5B1%5D=e&f%5Bg%5D=h"
        decode_query = "a.b=c&a.b=d&x%5By%5D=z"
        decode_options = DecodeOptions(allow_dots=True, duplicates=Duplicates.COMBINE)
        decode_expected = {"a": {"b": ["c", "d"]}, "x": {"y": "z"}}
        encode_payload_snapshot = copy.deepcopy(encode_payload)
        decode_options_snapshot = copy.deepcopy(decode_options)

        def worker(results: queue.Queue) -> None:
            for _ in range(HEAVY_ENCODE_ITERATION_COUNT):
                results.put(("encode", encode(encode_payload)))
                results.put(("decode", decode(decode_query, decode_options)))

        raw_results = _run_concurrently(worker)

        assert len(raw_results) == THREAD_COUNT * HEAVY_ENCODE_ITERATION_COUNT * 2
        for kind, result in raw_results:
            if kind == "encode":
                assert result == encode_expected
            else:
                assert result == decode_expected
        assert encode_payload == encode_payload_snapshot
        assert decode_options == decode_options_snapshot
