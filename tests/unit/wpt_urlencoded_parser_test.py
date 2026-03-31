"""WPT-derived coverage for flat ``application/x-www-form-urlencoded`` parsing.

Vendored and adapted from:
https://github.com/web-platform-tests/wpt/blob/master/url/urlencoded-parser.any.js

These cases intentionally exercise the public ``decode()`` API only. The WPT
corpus models parsing as an ordered list of key/value tuples; this module maps
those tuples to ``qs.py``'s flat dict/list result shape.
"""

import typing as t

import pytest

from qs_codec import decode


def _wpt_pairs_to_qs_expected(pairs: t.Iterable[t.Tuple[str, str]]) -> t.Dict[str, t.Any]:
    expected: t.Dict[str, t.Any] = {}

    for key, value in pairs:
        if key == "":
            continue

        if key in expected:
            current = expected[key]
            if isinstance(current, list):
                current.append(value)
            else:
                expected[key] = [current, value]
        else:
            expected[key] = value

    return expected


def _wpt_case(query: str, pairs: t.Iterable[t.Tuple[str, str]], *, id: str) -> t.Any:
    return pytest.param(query, _wpt_pairs_to_qs_expected(pairs), id=id)


@pytest.mark.parametrize(
    "query, expected",
    [
        _wpt_case("test", (("test", ""),), id="bare-token"),
        _wpt_case("\ufefftest=\ufeff", (("\ufefftest", "\ufeff"),), id="bom-literal"),
        _wpt_case("%EF%BB%BFtest=%EF%BB%BF", (("\ufefftest", "\ufeff"),), id="bom-percent-encoded"),
        _wpt_case("%EF%BF%BF=%EF%BF%BF", (("\uffff", "\uffff"),), id="noncharacter-ffff"),
        _wpt_case("%FE%FF", (("\ufffd\ufffd", ""),), id="invalid-utf8-fe-ff"),
        _wpt_case("%FF%FE", (("\ufffd\ufffd", ""),), id="invalid-utf8-ff-fe"),
        _wpt_case("†&†=x", (("†", ""), ("†", "x")), id="duplicate-unicode-key"),
        _wpt_case("%C2", (("\ufffd", ""),), id="truncated-utf8-byte"),
        _wpt_case("%C2x", (("\ufffdx", ""),), id="truncated-utf8-byte-with-suffix"),
        _wpt_case(
            "_charset_=windows-1252&test=%C2x",
            (("_charset_", "windows-1252"), ("test", "\ufffdx")),
            id="charset-pseudo-field",
        ),
        _wpt_case("", (), id="empty-input"),
        _wpt_case("a", (("a", ""),), id="bare-name"),
        _wpt_case("a=b", (("a", "b"),), id="name-value"),
        _wpt_case("a=", (("a", ""),), id="explicit-empty-value"),
        _wpt_case("&", (), id="delimiter-only"),
        _wpt_case("&a", (("a", ""),), id="leading-delimiter"),
        _wpt_case("a&", (("a", ""),), id="trailing-delimiter"),
        _wpt_case("a&a", (("a", ""), ("a", "")), id="duplicate-empty-values"),
        _wpt_case("a&b&c", (("a", ""), ("b", ""), ("c", "")), id="multiple-bare-names"),
        _wpt_case("a=b&c=d", (("a", "b"), ("c", "d")), id="two-pairs"),
        _wpt_case("a=b&c=d&", (("a", "b"), ("c", "d")), id="two-pairs-trailing-delimiter"),
        _wpt_case("&&&a=b&&&&c=d&", (("a", "b"), ("c", "d")), id="noisy-delimiters"),
        _wpt_case("a=a&a=b&a=c", (("a", "a"), ("a", "b"), ("a", "c")), id="duplicate-values"),
        _wpt_case("a==a", (("a", "=a"),), id="extra-equals"),
        _wpt_case("a=a+b+c+d", (("a", "a b c d"),), id="plus-as-space"),
        _wpt_case("%=a", (("%", "a"),), id="lone-percent-key"),
        _wpt_case("%a=a", (("%a", "a"),), id="partial-percent-key"),
        _wpt_case("%a_=a", (("%a_", "a"),), id="partial-percent-key-with-suffix"),
        _wpt_case("%61=a", (("a", "a"),), id="percent-decoded-key"),
        _wpt_case("%61+%4d%4D=", (("a MM", ""),), id="percent-decoded-key-with-plus"),
        _wpt_case("id=0&value=%", (("id", "0"), ("value", "%")), id="literal-percent-value"),
        _wpt_case("b=%2sf%2a", (("b", "%2sf*"),), id="invalid-percent-triplet-before-escaped-asterisk"),
        _wpt_case("b=%2%2af%2a", (("b", "%2*f*"),), id="split-invalid-percent-before-escaped-asterisk"),
        _wpt_case("b=%%2a", (("b", "%*"),), id="literal-percent-before-escaped-asterisk"),
    ],
)
def test_wpt_urlencoded_parser_cases(query: str, expected: t.Mapping[str, t.Any]) -> None:
    assert decode(query) == expected


def test_wpt_empty_key_divergence_is_documented() -> None:
    # URLSearchParams preserves the empty key in "=b"; qs.py intentionally drops it.
    assert decode("=b") == {}
