import pytest

from qs_codec.models.key_path_node import KeyPathNode


class TestKeyPathNode:
    def test_append_empty_segment_returns_same_node(self) -> None:
        root = KeyPathNode.from_materialized("root")
        assert root.append("") is root

    def test_materialize_builds_nested_paths(self) -> None:
        path = KeyPathNode.from_materialized("a").append("[b]").append("[c]")
        assert path.materialize() == "a[b][c]"

    def test_materialize_uses_cached_value(self) -> None:
        path = KeyPathNode.from_materialized("a").append("[b]").append("[c]")
        first = path.materialize()
        second = path.materialize()
        assert first == second == "a[b][c]"

    def test_as_dot_encoded_replaces_literal_dots(self) -> None:
        path = KeyPathNode.from_materialized("a.b").append("[c.d]")
        encoded = path.as_dot_encoded()
        assert encoded.materialize() == "a%2Eb[c%2Ed]"

    def test_as_dot_encoded_reuses_cached_node(self) -> None:
        path = KeyPathNode.from_materialized("a.b").append("[c]")
        first = path.as_dot_encoded()
        second = path.as_dot_encoded()
        assert first is second

    def test_as_dot_encoded_returns_self_when_no_segments_need_encoding(self) -> None:
        path = KeyPathNode.from_materialized("a").append("[c]")
        assert path.as_dot_encoded() is path

    def test_as_dot_encoded_handles_deep_paths_without_recursion_error(self) -> None:
        path = KeyPathNode.from_materialized("root")
        for i in range(12_000):
            path = path.append(f".k{i}")

        encoded = path.as_dot_encoded().materialize()
        assert encoded.startswith("root%2Ek0%2Ek1")

    @pytest.mark.parametrize(
        "path, expected",
        [
            (KeyPathNode.from_materialized("a"), "a"),
            (KeyPathNode.from_materialized("a").append(".b"), "a.b"),
            (KeyPathNode.from_materialized("a").append("[0]").append("[b]"), "a[0][b]"),
        ],
    )
    def test_materialize_path_variants(self, path: KeyPathNode, expected: str) -> None:
        assert path.materialize() == expected
