## 1.1.3

* [FIX] list with indexes always get parsed into dict ([#19](https://github.com/techouse/qs_codec/pull/19))

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