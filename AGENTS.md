# Repository Guidelines

## Project Structure & Module Organization
- `src/qs_codec/` contains the codec implementation, option models, and helpers; place new modules here and keep exports deliberate.
- `tests/` mirrors the package layout with `test_*.py` files so every feature has a nearby regression check.
- `docs/` builds the Sphinx site; refresh guides when behavior or options change.
- `requirements_dev.txt` pins tooling and `tox.ini` mirrors the CI matrix—update both when adding dependencies.

## Build, Test, and Development Commands
- `python -m pip install -e .[dev]` installs the package alongside linting and typing extras.
- `pytest -v --cov=src/qs_codec` drives the unit suite and produces the coverage XML consumed by codecov.
- `tox -e python3.13` runs tests in an isolated interpreter; swap the env name to target other supported versions.
- `tox -e linters` chains Black, isort, flake8, pylint, bandit, pyright, and mypy to catch style or security drift before review.

## Coding Style & Naming Conventions
- Format code with Black (120-char lines) and order imports with isort's Black profile, both configured in `pyproject.toml`.
- Keep functions and modules in snake_case, reserve PascalCase for classes reflecting `qs` data structures, and type hint public APIs.
- Respect docstring tone and option names from the JavaScript `qs` package to signal parity.

## Testing Guidelines
- Add or extend pytest cases under `tests/`, leaning on parametrization for the different encoder/decoder modes.
- Preserve or raise the coverage level tracked in `coverage.xml`; CI flags regressions.
- Name tests `test_{feature}_{scenario}` and refresh fixtures whenever query-string semantics shift.
- When touching cross-language behavior, run `tests/comparison/compare_outputs.sh` to confirm parity with the Node reference.
  - For encoding depth changes, cover `EncodeOptions.max_depth` (positive int/None): `None` means unbounded traversal
    (`sys.maxsize`) and explicit values are enforced directly (no recursion-limit capping).

## Commit & Pull Request Guidelines
- Follow the emoji-prefixed summaries visible in `git log` (e.g., `:arrow_up: Bump actions/setup-python from 5 to 6 (#26)`), using the imperative mood.
- Keep each commit focused; include a short body for impactful changes explaining compatibility or migration notes.
- For PRs, push only after `tox` succeeds, link the driving issue, outline user-facing changes, and note the tests you ran (attach before/after snippets for docs tweaks).

## Security & Compatibility Notes
- Follow `SECURITY.md` for private vulnerability disclosure and avoid posting sensitive details in public threads.
- This port tracks the npm `qs` package; document intentional divergences in both code and docs as soon as they occur.
