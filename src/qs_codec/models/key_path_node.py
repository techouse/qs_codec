"""Linked key-path nodes used by the encoder to reduce string churn."""

from __future__ import annotations

import typing as t


class KeyPathNode:
    """Key-path node with immutable path semantics and write-once lazy caches.

    The parent/segment chain defines the path and does not change after
    construction. For performance, ``dot_encoded`` and ``materialized`` are
    lazily populated cache slots; they are written once and do not alter the
    path semantics.
    """

    __slots__ = ("depth", "dot_encoded", "materialized", "parent", "segment")
    parent: t.Optional["KeyPathNode"]
    segment: str
    depth: int
    dot_encoded: t.Optional["KeyPathNode"]
    materialized: t.Optional[str]

    def __init__(self, parent: t.Optional["KeyPathNode"], segment: str) -> None:
        """Create a path node linked to an optional parent."""
        self.parent = parent
        self.segment = segment
        self.depth = (parent.depth if parent is not None else 0) + 1
        self.dot_encoded: t.Optional["KeyPathNode"] = None
        self.materialized: t.Optional[str] = None

    @classmethod
    def from_materialized(cls, value: str) -> "KeyPathNode":
        """Create a root node from a full materialized prefix."""
        return cls(None, value)

    def append(self, segment: str) -> "KeyPathNode":
        """Append a segment and return a new node, or self for empty segments."""
        return self if not segment else KeyPathNode(self, segment)

    def as_dot_encoded(self) -> "KeyPathNode":
        """Return a cached view where literal dots are encoded as ``%2E``."""
        cached = self.dot_encoded
        if cached is not None:
            return cached

        unresolved: t.List["KeyPathNode"] = []
        node: t.Optional["KeyPathNode"] = self
        while node is not None and node.dot_encoded is None:
            unresolved.append(node)
            node = node.parent

        for current in reversed(unresolved):
            encoded_segment = current.segment.replace(".", "%2E") if "." in current.segment else current.segment
            parent = current.parent
            if parent is None:
                encoded = current if encoded_segment is current.segment else KeyPathNode(None, encoded_segment)
            else:
                encoded_parent = parent.dot_encoded
                if encoded_parent is None:  # pragma: no cover - internal invariant
                    raise RuntimeError("dot_encoded parent is not initialized")  # noqa: TRY003
                if encoded_parent is parent and encoded_segment is current.segment:
                    encoded = current
                else:
                    encoded = KeyPathNode(encoded_parent, encoded_segment)
            current.dot_encoded = encoded

        return self.dot_encoded if self.dot_encoded is not None else self

    def materialize(self) -> str:
        """Render and cache the full path text."""
        cached = self.materialized
        if cached is not None:
            return cached

        parent = self.parent
        if parent is None:
            self.materialized = self.segment
            return self.segment

        if self.depth == 2:
            parent_part = parent.materialized
            if parent_part is None:
                parent_part = parent.segment
                parent.materialized = parent_part
            value = parent_part + self.segment
            self.materialized = value
            return value

        parts = [""] * self.depth
        node: t.Optional["KeyPathNode"] = self
        index = self.depth - 1
        while node is not None:
            parts[index] = node.segment
            node = node.parent
            index -= 1

        value = "".join(parts)
        self.materialized = value
        return value
