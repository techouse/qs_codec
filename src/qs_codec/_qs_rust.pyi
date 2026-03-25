from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

def encode(value: Any, config: Mapping[str, object], callbacks: object | None = ...) -> str: ...
def decode_pairs(pairs: Sequence[tuple[str, Any]], config: Mapping[str, object]) -> dict[str, Any]: ...
