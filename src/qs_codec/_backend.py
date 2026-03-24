"""Internal backend selection for qs_codec."""

from __future__ import annotations

import functools
import importlib
import os
import sys
import typing as t
from dataclasses import dataclass

QS_CODEC_BACKEND_ENV = "QS_CODEC_BACKEND"
_VALID_BACKENDS = frozenset({"auto", "pure", "rust"})


@dataclass(frozen=True)
class BackendSelection:
    """Resolved backend for the current process."""

    name: t.Literal["pure", "rust"]
    native_module: t.Any = None


def _supports_native_backend() -> bool:
    return sys.implementation.name == "cpython"


def _requested_backend() -> str:
    raw_value = os.getenv(QS_CODEC_BACKEND_ENV, "auto").strip().lower() or "auto"
    if raw_value not in _VALID_BACKENDS:
        expected = ", ".join(sorted(_VALID_BACKENDS))
        raise RuntimeError(
            f"Invalid {QS_CODEC_BACKEND_ENV} value {raw_value!r}. Expected one of: {expected}."
        )
    return raw_value


@functools.lru_cache(maxsize=1)
def _import_native_module() -> t.Any:
    return importlib.import_module("qs_codec._qs_rust")


def resolve_backend() -> BackendSelection:
    """Resolve the effective backend for the current interpreter and env."""
    requested = _requested_backend()

    if requested == "pure":
        return BackendSelection(name="pure")

    if not _supports_native_backend():
        if requested == "auto":
            return BackendSelection(name="pure")
        raise RuntimeError(
            "QS_CODEC_BACKEND=rust is only supported on CPython and free-threaded CPython in this tranche."
        )

    try:
        native_module = _import_native_module()
    except ImportError as exc:
        if requested == "auto":
            return BackendSelection(name="pure")
        raise RuntimeError(
            "QS_CODEC_BACKEND=rust was requested, but qs_codec._qs_rust could not be imported."
        ) from exc

    return BackendSelection(name="rust", native_module=native_module)
