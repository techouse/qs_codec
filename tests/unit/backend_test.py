import types

import pytest

import qs_codec._backend as backend


def test_resolve_backend_pure_skips_native_import(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QS_CODEC_BACKEND", "pure")
    monkeypatch.setattr(
        backend,
        "_import_native_module",
        lambda: (_ for _ in ()).throw(AssertionError("native import should not be attempted")),
    )

    selection = backend.resolve_backend()

    assert selection.name == "pure"
    assert selection.native_module is None


def test_resolve_backend_auto_falls_back_to_pure_when_native_import_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QS_CODEC_BACKEND", "auto")
    monkeypatch.setattr(backend, "_supports_native_backend", lambda: True)
    monkeypatch.setattr(backend, "_import_native_module", lambda: (_ for _ in ()).throw(ImportError("boom")))

    selection = backend.resolve_backend()

    assert selection.name == "pure"
    assert selection.native_module is None


def test_resolve_backend_auto_uses_rust_when_native_module_is_available(monkeypatch: pytest.MonkeyPatch) -> None:
    native_module = types.SimpleNamespace(name="_qs_rust")
    monkeypatch.setenv("QS_CODEC_BACKEND", "auto")
    monkeypatch.setattr(backend, "_supports_native_backend", lambda: True)
    monkeypatch.setattr(backend, "_import_native_module", lambda: native_module)

    selection = backend.resolve_backend()

    assert selection.name == "rust"
    assert selection.native_module is native_module


def test_resolve_backend_rust_requires_native_module(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QS_CODEC_BACKEND", "rust")
    monkeypatch.setattr(backend, "_supports_native_backend", lambda: True)
    monkeypatch.setattr(backend, "_import_native_module", lambda: (_ for _ in ()).throw(ImportError("boom")))

    with pytest.raises(RuntimeError, match="QS_CODEC_BACKEND=rust was requested"):
        backend.resolve_backend()


def test_resolve_backend_rust_rejects_non_cpython(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QS_CODEC_BACKEND", "rust")
    monkeypatch.setattr(backend, "_supports_native_backend", lambda: False)

    with pytest.raises(RuntimeError, match="only supported on CPython"):
        backend.resolve_backend()


def test_invalid_backend_value_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QS_CODEC_BACKEND", "wat")

    with pytest.raises(RuntimeError, match="Invalid QS_CODEC_BACKEND value"):
        backend.resolve_backend()
