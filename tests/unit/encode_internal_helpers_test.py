import typing as t

from qs_codec.encode import _compute_step_and_check_cycle, _identity_key, _next_path_for_sequence, _pop_current_node
from qs_codec.models.cycle_state import CycleState
from qs_codec.models.key_path_node import KeyPathNode
from qs_codec.models.weak_wrapper import WeakWrapper


def test_identity_key_returns_int_unchanged() -> None:
    assert _identity_key(42) == 42


def test_identity_key_handles_collected_weak_wrapper() -> None:
    wrapper = WeakWrapper({"a": "b"})
    object.__setattr__(wrapper, "_wref", lambda: None)
    assert _identity_key(wrapper) == id(wrapper)


def test_identity_key_returns_object_id_for_non_wrapper_values() -> None:
    value = {"a": "b"}
    assert _identity_key(value) == id(value)


def test_compute_step_and_check_cycle_returns_zero_when_node_has_no_entries() -> None:
    assert _compute_step_and_check_cycle(CycleState(), {"a": "b"}, 3) == 0


def test_pop_current_node_deletes_last_entry() -> None:
    value = {"a": "b"}
    state = CycleState()
    state.entries[id(value)] = [(0, 0, False)]

    _pop_current_node(state, value)

    assert state.entries == {}


def test_next_path_for_sequence_uses_custom_suffix_when_child_starts_with_parent() -> None:
    root = KeyPathNode.from_materialized("root")

    def custom_generator(prefix: str, key: t.Optional[str]) -> str:
        return f"{prefix}<{key}>"

    next_path = _next_path_for_sequence(root, custom_generator, "item")
    assert next_path.materialize() == "root<item>"


def test_next_path_for_sequence_rebuilds_when_child_is_not_prefixed() -> None:
    root = KeyPathNode.from_materialized("root")

    def custom_generator(prefix: str, key: t.Optional[str]) -> str:  # pylint: disable=W0613  # noqa: ARG001
        return f"other[{key}]"

    next_path = _next_path_for_sequence(root, custom_generator, "item")
    assert next_path.materialize() == "other[item]"
