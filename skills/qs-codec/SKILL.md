---
name: qs-codec
description: Use this skill whenever a user wants to install, configure, troubleshoot, or write Python application code for encoding and decoding nested query strings with the qs-codec package. This skill helps produce practical qs_codec.decode, qs_codec.encode, qs_codec.loads, and qs_codec.dumps snippets, choose DecodeOptions and EncodeOptions, explain option tradeoffs, and avoid qs-codec edge-case pitfalls around lists, dot notation, duplicates, null handling, charset sentinels, depth limits, and untrusted input.
---

# qs-codec Usage Assistant

Help users parse and build query strings with the Python `qs-codec` package.
Focus on user application code and interoperability outcomes, not repository
maintenance.

## Start With Inputs

Before producing a final snippet, collect only the missing details that change
the code:

- Runtime: Python script, web framework, tests, library code, or generated
  example.
- Direction: decode an incoming query string, encode Python data, or normalize
  query-string handling around an existing URL/request object.
- The actual query string or Python structure when available.
- Target API convention for lists: indexed brackets, empty brackets, repeated
  keys, or comma-separated values.
- Whether the query may include a leading `?`, dot notation, literal dots in
  keys, duplicate keys, custom delimiters, comma-separated lists, `None` flags,
  Latin-1/legacy charset behavior, or untrusted user input.

Do not over-ask when the desired behavior is obvious. State assumptions in the
answer and give the user a concrete snippet they can paste.

## Installation

Install the package from PyPI:

```bash
python -m pip install qs-codec
```

Use the package-level public API:

```python
import qs_codec as qs
```

When snippets use regex delimiters, dates, or custom codecs, include the needed
standard-library imports such as `re`, `datetime`, `codecs`, or `typing`.

## Base Patterns

Decode a query string into nested Python values:

```python
import qs_codec as qs

params = qs.decode("a[b][c]=d&tags[]=python&tags[]=web")
assert params == {"a": {"b": {"c": "d"}}, "tags": ["python", "web"]}
```

Encode nested Python values into a query string:

```python
import qs_codec as qs

query = qs.encode({
    "a": {"b": {"c": "d"}},
    "tags": ["python", "web"],
})
assert query == "a%5Bb%5D%5Bc%5D=d&tags%5B0%5D=python&tags%5B1%5D=web"
```

Use `qs.loads(...)` as a string-only alias for `qs.decode(...)`, and
`qs.dumps(...)` as an alias for `qs.encode(...)`.

## Decode Recipes

Use these options with `qs.decode(query, qs.DecodeOptions(...))`:

- Leading question mark: `ignore_query_prefix=True`.
- Dot notation such as `a.b=c`: `allow_dots=True`.
- Double-encoded literal dots in keys such as `name%252Eobj.first=John`:
  `decode_dot_in_keys=True`.
- Duplicate keys: `duplicates=qs.Duplicates.COMBINE` keeps all values as a
  list; use `qs.Duplicates.FIRST` or `qs.Duplicates.LAST` to collapse.
- Bracket lists: enabled by default; set `parse_lists=False` to treat list
  syntax as dictionary keys.
- Large or sparse list indices: default `list_limit` is `20`; indices above the
  limit become dictionary keys.
- Comma-separated values such as `a=b,c`: `comma=True`.
- Tokens without `=` as `None`: `strict_null_handling=True`.
- Custom delimiters: `delimiter=";"` or `delimiter=re.compile(r"[;,]")`.
- Legacy charset input: `charset=qs.Charset.LATIN1`; use
  `charset_sentinel=True` when a form may include `utf8=...` to signal the real
  charset.
- HTML numeric entities: `interpret_numeric_entities=True`, usually with
  Latin-1 or charset sentinel handling.
- Untrusted input: keep `depth`, `parameter_limit`, and `list_limit` bounded;
  use `strict_depth=True` plus `raise_on_limit_exceeded=True` when callers need
  hard failures instead of soft limiting.

Example for a request query:

```python
import qs_codec as qs

params = qs.decode(
    "?filter.status=open&tag=python&tag=web",
    qs.DecodeOptions(
        ignore_query_prefix=True,
        allow_dots=True,
        duplicates=qs.Duplicates.COMBINE,
    ),
)
assert params == {"filter": {"status": "open"}, "tag": ["python", "web"]}
```

## Encode Recipes

Use these options with `qs.encode(data, qs.EncodeOptions(...))`:

- List style defaults to `qs.ListFormat.INDICES`:
  `tags%5B0%5D=python&tags%5B1%5D=web`.
- Empty brackets: `list_format=qs.ListFormat.BRACKETS`.
- Repeated keys: `list_format=qs.ListFormat.REPEAT`.
- Comma-separated values: `list_format=qs.ListFormat.COMMA`.
- Single-item comma lists that must round-trip as lists:
  `comma_round_trip=True`.
- Drop `None` items before comma-joining lists: `comma_compact_nulls=True`.
- Dot notation for nested dictionaries: `allow_dots=True`.
- Literal dots in keys: `encode_dot_in_keys=True`; leave `allow_dots`
  unspecified or set it explicitly based on whether nested paths should use
  dot notation.
- Add a leading `?`: `add_query_prefix=True`.
- Custom pair delimiter: `delimiter=";"`.
- Preserve readable bracket/dot keys while encoding values:
  `encode_values_only=True`.
- Disable percent encoding entirely for debugging or documented examples:
  `encode=False`.
- Emit `None` without `=`: `strict_null_handling=True`.
- Omit `None` keys: `skip_nulls=True`.
- Emit empty lists as `foo[]`: `allow_empty_lists=True`.
- Omit a value entirely: use `qs.Undefined()`.
- Legacy form spaces as `+`: `format=qs.Format.RFC1738`; the default is
  `qs.Format.RFC3986`, which emits spaces as `%20`.
- Legacy charset output: `charset=qs.Charset.LATIN1`; use
  `charset_sentinel=True` to prepend the `utf8=...` sentinel.
- Custom behavior: use `encoder`, `serialize_date`, `sort`, or `filter` when
  the target API needs special scalar encoding, date formatting, stable key
  order, or selected fields.
- Maximum traversal depth: `max_depth=<positive int>`; `None` means unbounded by
  this option.

Example for an API that expects repeated keys:

```python
import qs_codec as qs

query = qs.encode(
    {
        "q": "query strings",
        "tag": ["python", "web"],
    },
    qs.EncodeOptions(
        list_format=qs.ListFormat.REPEAT,
        add_query_prefix=True,
    ),
)
assert query == "?q=query%20strings&tag=python&tag=web"
```

## Combinations To Check

Warn or adjust before giving code for these cases:

- `qs.DecodeOptions(decode_dot_in_keys=True, allow_dots=False)` is invalid.
- `parameter_limit` must be positive or `float("inf")`; use
  `raise_on_limit_exceeded=True` to raise when the limit is exceeded instead of
  silently truncating.
- `list_limit` has nuanced list-construction behavior; negative values disable
  numeric-index list parsing, and `raise_on_limit_exceeded=True` turns list
  limit violations into `ValueError`.
- Built-in charset handling supports only `qs.Charset.UTF8` and
  `qs.Charset.LATIN1`; other encodings require a custom `encoder` or `decoder`.
- `EncodeOptions.encoder` is ignored when `encode=False`.
- Combining `encode_values_only=True` and `encode_dot_in_keys=True` encodes only
  dots in keys; values remain otherwise unchanged.
- `DecodeOptions.comma` parses simple comma-separated values, but does not
  decode nested dictionary syntax such as `a={b:1},{c:d}`.
- `encode(None)`, scalar roots, empty dictionaries, and empty containers
  generally produce an empty string.
- The standard library and many web frameworks flatten duplicates or nested
  query syntax. Prefer `qs.decode` on the raw query string when qs-style nested
  or repeated values matter.

## Response Shape

For code-generation requests, answer with:

1. A short statement of assumptions, especially list format, null handling,
   charset, prefix handling, and whether input is trusted.
2. One concrete Python snippet using `qs.decode`, `qs.encode`, `qs.loads`, or
   `qs.dumps`.
3. A brief explanation of only the options used.
4. A small verification example, such as an expected dictionary, expected query
   string, or a `pytest` assertion.

Keep snippets application-oriented. Prefer public API imports from `qs_codec`;
do not ask users to import from `qs_codec.src` or private modules.
