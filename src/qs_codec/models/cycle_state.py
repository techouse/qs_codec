"""CycleState model for storing cycle state information."""

import typing as t
from dataclasses import dataclass, field


@dataclass
class CycleState:
    """Model for storing cycle state information."""

    entries: t.Dict[int, t.List[t.Tuple[int, t.Any, bool]]] = field(default_factory=dict)
