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