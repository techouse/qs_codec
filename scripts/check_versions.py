#!/usr/bin/env python
"""Assert that Python and Rust package versions stay in lockstep."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import toml


ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = ROOT / "pyproject.toml"
INIT_PATH = ROOT / "src" / "qs_codec" / "__init__.py"
CARGO_PATH = ROOT / "rust" / "Cargo.toml"
VERSION_RE = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.MULTILINE)


def _project_version() -> str:
    return str(toml.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]["version"])


def _init_version() -> str:
    match = VERSION_RE.search(INIT_PATH.read_text(encoding="utf-8"))
    if match is None:
        raise RuntimeError(f"Could not find __version__ in {INIT_PATH}")
    return match.group(1)


def _cargo_version() -> str:
    return str(toml.loads(CARGO_PATH.read_text(encoding="utf-8"))["package"]["version"])


def main() -> int:
    versions = {
        "pyproject.toml": _project_version(),
        "src/qs_codec/__init__.py": _init_version(),
        "rust/Cargo.toml": _cargo_version(),
    }
    unique_versions = set(versions.values())
    if len(unique_versions) == 1:
        print(next(iter(unique_versions)))
        return 0

    for path, version in versions.items():
        print(f"{path}: {version}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
