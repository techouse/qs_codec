# Copilot Project Instructions: qs_codec

Concise, project-specific guidance for AI coding agents working on this repo. Focus on preserving behavioral parity with the Node.js `qs` library while embracing Pythonic clarity.

## 1. Project Purpose & Architecture
- Library: High-fidelity Python port of the JavaScript `qs` query string encoder/decoder.
- Core public API re-exported in `qs_codec/__init__.py`: `encode`, `decode`, `dumps`, `loads`, plus enums (`Charset`, `Format`, `ListFormat`, `Duplicates`, `Sentinel`, `DecodeKind`) and option models (`EncodeOptions`, `DecodeOptions`, `Undefined`).
- Two main modules:
  - `encode.py`: Converts mappings/sequences → query string. Emphasizes deterministic ordering, flexible list formats, dot vs bracket notation, charset sentinel emission, null/undefined semantics, cycle detection via a `WeakKeyDictionary` side-channel.
  - `decode.py`: Parses raw query string or mapping → nested dict/list. Mirrors control flow of upstream `qs` for parity; stages: early option cloning, tokenization (`_parse_query_string_values`), structural reconstruction (`_parse_keys` / `_parse_object`), merge via `Utils.merge`, final compaction.
- Support code in `utils/` (`utils.py`, `decode_utils.py`) and enums/models folders. Option dataclasses centralize behavioral switches; never scatter ad-hoc flags.

## 2. Key Behavioral Invariants
- DO NOT mutate caller inputs—copy/normalize (shallow copy for mappings; deep-copy only when a callable filter may mutate; index-projection for sequences) before traversal.
- Cycle detection in `encode._encode` must raise `ValueError("Circular reference detected")`—preserve side-channel algorithm.
- Depth, list, and parameter limits are security/safety features: respect `depth`, `max_depth`, `list_limit`, `parameter_limit`, and `strict_depth` / `raise_on_limit_exceeded` exactly as tests assert. `max_depth` is capped to the current recursion limit.
- Duplicate key handling delegated to `Duplicates` enum: COMBINE → list accumulation; FIRST/LAST semantics enforced during merge.
- List format semantics (`ListFormat` enum) change how prefixes are generated; COMMA + `comma_round_trip=True` must emit single-element marker for round-trip fidelity.
- Charset sentinel logic: when `charset_sentinel=True`, prepend sentinel *before* payload; obey override rules when both charset and sentinel present.
- Dot handling: `allow_dots` toggles dotted path parsing; `encode_dot_in_keys` / `decode_dot_in_keys` percent-encode or decode literal dots—order and validation enforced (see tests & README examples).

## 3. Conventions & Patterns
- Public API only via root `__all__`; keep new exports deliberate.
- Use `Enum`-backed strategy objects where JS version uses option strings (e.g., list format generators). Avoid magic strings.
- Input/option validation yields `ValueError` or specific errors (`IndexError` for strict depth). Match existing error types/messages where tests assert them.
- Keep docstrings descriptive and parity-focused; reuse language style in existing modules.
- Maintain 120-char line formatting (Black) and import ordering (isort, black profile).

## 4. Developer Workflow
- Install (dev): `python -m pip install -e .[dev]`.
- Run full test suite: `pytest -v --cov=src/qs_codec` (coverage enforced in CI).
- Lint/type check: `tox -e linters` (chains Black, isort, flake8, pylint, mypy, pyright, bandit).
- Multi-version tests: `tox -e python3.13` (swap env name for other versions).
- Docs build: `make -C docs html` (update Sphinx when public behavior or options change).
- Cross-language parity verification: run `tests/comparison/compare_outputs.sh` (invokes Node reference `qs.js` with shared `test_cases.json`). Update cases when adding features—maintain symmetry.

## 5. Adding / Modifying Features
- Extend option behavior by updating the relevant dataclass (`encode_options.py` or `decode_options.py`)—include defaults and type hints; update tests + README examples.
- When altering merge or list/index logic, adjust `Utils.merge` or decoding helpers—never inline merging elsewhere.
- New list or formatting strategies: add Enum member with associated generator/formatter; augment tests to cover serialization/deserialization round trip.
- Performance-sensitive paths: avoid repeated regex compilation or deep copies inside tight loops; reuse existing pre-processing structure (tokenize first, structure later).
  - `Utils.merge` is internal and may reuse dict targets for performance; do not assume it preserves caller immutability.

## 6. Testing Strategy
- Mirror existing parametric test style in `tests/unit/*_test.py`.
- Always add regression tests for: edge limits (depth, list_limit, parameter_limit), duplicate policies, charset sentinel interactions, dot-notation toggles, comma round-trip.
- For new error messages, assert exact string if existing tests do so for similar errors; otherwise prefer substring containment to reduce brittleness.

## 7. Common Pitfalls to Avoid
- Accidentally mutating option instances (treat dataclasses as immutable input; clone with `replace` when toggling transient flags—see `decode.decode`).
- Emitting leading '?' incorrectly: only when `add_query_prefix=True` and before sentinel tokens.
- Losing order determinism when a custom `sort` comparator is passed—must apply before recursive descent (root and nested key collections).
- Failing to percent-encode '.' when `encode_dot_in_keys=True` and `allow_dots=True`.

## 8. External Parity Notes
- Behavior aims to match npm `qs`; intentional divergences must be documented in README + docs and reflected in comparison test fixtures.
- Keep option naming aligned with JS library even if Python style would differ.

## 9. When Unsure
- Check README examples first—they are authoritative for semantics.
- Inspect related unit test to understand expected edge behavior before refactoring.
- Preserve public function signatures; add kwargs only if necessary and with backward compatibility.

---
Feedback welcome: If any section is unclear or missing context you need, request clarification or propose an addition.
