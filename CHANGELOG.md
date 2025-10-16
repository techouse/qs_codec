## 1.3.0

* [FEAT] add `EncodeOptions.comma_compact_nulls`, allowing omission of `None` entries in lists when using the `ListFormat.COMMA`. This results in cleaner output (e.g., `[True, False, None, True]` becomes `"true,false,true"`).

## 1.2.5

* [CHORE] add support for Python 3.14
* [CHORE] reinstate Python 3.8 support

## 1.2.4

* [FIX] encode booleans in lowercase to match JavaScript behavior
* [CHORE] add tests for boolean encoding and decoding parity

## 1.2.3

* [CHORE] add highlights section to README and docs with key features and usage notes

## 1.2.2

* [CHORE] update pyproject.toml with improved metadata, optional dev dependencies, and wheel build config
* [CHORE] add project logo to README and documentation

## 1.2.1

* [FIX] fix top-level dot splitting in keys to preserve encoded dots and handle degenerate cases
* [FIX] normalize percent-encoded dots in bracketed keys when `decode_dot_in_keys` is enabled
* [FIX] handle leading dot in keys by converting to bracket segment in `dot_to_bracket_top_level`
* [FIX] fix strict_depth enforcement to avoid raising on unterminated bracket groups in decode logic
* [FIX] fix dot-to-bracket decoding to preserve leading dots in consecutive dot sequences
* [FIX] fix percent-decoding to handle dot in keys and clarify top-level percent sequence handling
* [FIX] handle ambiguous '.]' in key decoding and prevent bracket segment overrun on closing brackets
* [CHORE]️ refactor `DecodeOptions` to support legacy decoders and add unified decode methods
* [CHORE]️ update type annotations in `decode_options_test` for decoder and `legacy_decoder` signatures
* [CHORE] add tests for `DecodeOptions` dot-in-keys and custom decoder behaviors
* [CHORE] add C# port (QsNet) parity tests for encoded dot behavior in `DecodeOptions`
* [CHORE] add tests for decoder precedence over `legacy_decoder` and non-string `decoder` results in `DecodeOptions`
* [CHORE] add tests for dot encoding and decoding parity across `DecodeOptions` configurations
* [CHORE] revise decode test to avoid duplicate dict key assertion and ensure decoder invocation for dot-encoded and bracketed keys
* [CHORE] add tests for `split_key_into_segments` remainder handling and strict depth enforcement

## 1.2.0

* [FIX] preserve percent-encoded dots in keys during decoding
* [CHORE] refactor merge logic for improved readability and performance in utils
* [CHORE] optimize encoding logic for improved performance and clarity in encode_utils
* [CHORE] optimize decode logic for improved performance and clarity in decode_utils
* [CHORE] optimize key handling and object normalization for improved performance and clarity in encode.py
* [CHORE] optimize delimiter splitting and list parsing logic for improved performance and clarity in decode.py
* [CHORE] optimize proxy caching and dict hashing logic for improved performance and determinism in weak_wrapper
* [CHORE] optimize Undefined singleton logic for thread safety and clarity; prevent subclassing and ensure identity preservation
* [CHORE] optimize EncodeOptions initialization and equality logic for improved clarity and determinism
* [CHORE] optimize DecodeOptions post-init logic for improved determinism and enforce consistency between decode_dot_in_keys and allow_dots
* [CHORE] optimize list merging logic in Utils.merge for improved determinism and handling of Undefined values
* [CHORE] optimize type checking in list merging logic for improved clarity and consistency in Utils.merge
* [CHORE] optimize encode logic for improved determinism and clarity; use UNDEFINED singleton and refine ListFormat.COMMA comparison
* [CHORE] optimize decode logic to use UNDEFINED singleton for list initialization

## 1.1.8

* [FIX] fix stable hashing for mappings and sets by sorting on hashed keys and elements to prevent ordering errors
* [FIX] fix percent-encoding to operate on UTF-16 code units for accurate surrogate pair handling and JS compatibility
* [FIX] handle surrogate pairs only when valid high+low combination is present in UTF-8 encoding
* [FIX] replace code_unit_at with ord for direct code unit retrieval in EncodeUtils methods
* [FIX] fix WeakWrapper equality to compare underlying object identity instead of proxy instance
* [FIX] ensure thread-safe access to _proxy_cache with RLock in get_proxy
* [CHORE] add tests for EncodeUtils._encode_string with RFC3986 format and emoji handling
* [CHORE] update documentation

## 1.1.7

* [CHORE] optimize `decode` performance

## 1.1.6

* [FIX] remove redundant `WeakWrapper` instances in `encode`

## 1.1.5

* [FEAT] add `load` and `loads` alias methods for `decode`
* [FEAT] add `dump` and `dumps` alias methods for `encode`

## 1.1.4

* [CHORE] update readme for clarity around RFC 3986 and RFC 1738 space encoding

## 1.1.3

* [FIX] fix list with indices always getting parsed into a dict ([#19](https://github.com/techouse/qs_codec/pull/19))

## 1.1.2

* [FEAT] **WeakWrapper** now fully supports using mutable objects (e.g. `dict`, `list`, `set`) as weak-keys  
  * shared proxy layer stored in a `WeakValueDictionary` → automatic cleanup when the original object is GC’d  
  * deep-content hashing + identity-based equality  
  * safeguards for circular references and configurable depth limit
* [FIX] prevent recursion crashes when hashing very deep or cyclic structures (raises `RecursionError` / `ValueError` with clear messages)
* [CHORE] refactor `WeakWrapper` internals for clarity and performance
* [CHORE] add an extensive WeakWrapper test-suite (proxy sharing, GC removal, stable hashes, error conditions)
* [CHORE] tighten type-hints  
  * use `weakref.ReferenceType[_Refable]`  

## 1.1.1

* [CHORE] enhance type hints and improve code clarity ([#17](https://github.com/techouse/qs_codec/pull/17))

## 1.1.0

* [CHORE] drop support for Python 3.8 and update dependencies for Python 3.9+

## 1.0.7

* [FIX] fix `EncodeUtils.encode` for non-BMP characters
* [CHORE] refactor `EncodeUtils` and `DecodeUtils`
* [CHORE] add more tests

## 1.0.6

* [FIX] fix encoding non-BMP characters when using `charset=Charset.LATIN1`

## 1.0.5

* [FEAT] add `DecodeOptions.raise_on_limit_exceeded` option ([#11](https://github.com/techouse/qs_codec/pull/11))
* [CHORE] remove dead code in `Utils`
* [CHORE] add more tests
* [CHORE] update dependencies


## 1.0.4

* [FIX] `decode`: avoid a crash with `comma=True`, `charset=Charset.LATIN1`, `interpret_numeric_entities=True`
* [CHORE] add more tests

## 1.0.3

* [FEAT] add `DecodeOptions.strict_depth` option to throw when input is beyond depth ([#8](https://github.com/techouse/qs_codec/pull/8))

## 1.0.2

* [FIX] fix `decode` output when both `strict_null_handling` and `allow_empty_lists` are set to `True` ([#5](https://github.com/techouse/qs_codec/pull/5))

## 1.0.1

* [CHORE] update documentation

## 1.0.0

* [CHORE] first stable release

## 0.2.2

* [FEAT] `decode` returns `dict[str, Any]` instead of `dict` ([#4](https://github.com/techouse/qs_codec/pull/4))
* [FIX] fix decoding encoded square brackets in key names

## 0.2.1

* [CHORE] update dependencies

## 0.2.0

* [CHORE] update dependencies
* [CHORE] update README

## 0.1.6

* [CHORE] update README with links to [documentation](https://techouse.github.io/qs_codec/)

## 0.1.5

* [CHORE] added Sphinx [documentation](https://techouse.github.io/qs_codec/)

## 0.1.4

* [FIX] incorrect parsing of nested params with closing square bracket `]` in the property name ([#1](https://github.com/techouse/qs_codec/pull/1))

## 0.1.3

* [CHORE] update README.md
* [CHORE] add comparison test between output of qs_codec and [qs](https://www.npmjs.com/package/qs)

## 0.1.2

* [CHORE] minor improvements

## 0.1.1

* [CHORE] update README.md

## 0.1.0

* [CHORE] initial release