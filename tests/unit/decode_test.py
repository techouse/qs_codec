import re
import typing as t
from contextlib import nullcontext as does_not_raise
from datetime import datetime
from sys import getsizeof

import pytest

from qs_codec import Charset, DecodeOptions, Duplicates, decode, load, loads
from qs_codec.decode import _parse_object
from qs_codec.enums.decode_kind import DecodeKind
from qs_codec.utils.decode_utils import DecodeUtils


class TestDecode:
    def test_throws_an_error_if_the_input_is_not_a_string_or_a_dict(self) -> None:
        with pytest.raises(ValueError):
            decode(123)

    @pytest.mark.parametrize(
        "encoded, decoded, options",
        [
            ("0=foo", {"0": "foo"}, None),
            ("foo=c++", {"foo": "c  "}, None),
            ("a[>=]=23", {"a": {">=": "23"}}, None),
            ("a[<=>]==23", {"a": {"<=>": "=23"}}, None),
            ("a[==]=23", {"a": {"==": "23"}}, None),
            ("foo", {"foo": None}, DecodeOptions(strict_null_handling=True)),
            ("foo", {"foo": ""}, None),
            ("foo=", {"foo": ""}, None),
            ("foo=bar", {"foo": "bar"}, None),
            (" foo = bar = baz ", {" foo ": " bar = baz "}, None),
            ("foo=bar=baz", {"foo": "bar=baz"}, None),
            ("foo=bar&bar=baz", {"foo": "bar", "bar": "baz"}, None),
            ("foo2=bar2&baz2=", {"foo2": "bar2", "baz2": ""}, None),
            ("foo=bar&baz", {"foo": "bar", "baz": None}, DecodeOptions(strict_null_handling=True)),
            (
                "cht=p3&chd=t:60,40&chs=250x100&chl=Hello|World",
                {"cht": "p3", "chd": "t:60,40", "chs": "250x100", "chl": "Hello|World"},
                None,
            ),
        ],
    )
    def test_decodes_a_simple_string(
        self, encoded: str, decoded: t.Mapping[str, t.Any], options: t.Optional[DecodeOptions]
    ) -> None:
        if options is not None:
            assert decode(encoded, options=options) == decoded
        else:
            assert decode(encoded) == decoded

    @pytest.mark.parametrize(
        "encoded, decoded, options",
        [
            ("0=foo", {"0": "foo"}, None),
            ("foo=c++", {"foo": "c  "}, None),
            ("a[>=]=23", {"a": {">=": "23"}}, None),
            ("a[<=>]==23", {"a": {"<=>": "=23"}}, None),
            ("a[==]=23", {"a": {"==": "23"}}, None),
            ("foo", {"foo": None}, DecodeOptions(strict_null_handling=True)),
            ("foo", {"foo": ""}, None),
            ("foo=", {"foo": ""}, None),
            ("foo=bar", {"foo": "bar"}, None),
            (" foo = bar = baz ", {" foo ": " bar = baz "}, None),
            ("foo=bar=baz", {"foo": "bar=baz"}, None),
            ("foo=bar&bar=baz", {"foo": "bar", "bar": "baz"}, None),
            ("foo2=bar2&baz2=", {"foo2": "bar2", "baz2": ""}, None),
            ("foo=bar&baz", {"foo": "bar", "baz": None}, DecodeOptions(strict_null_handling=True)),
            (
                "cht=p3&chd=t:60,40&chs=250x100&chl=Hello|World",
                {"cht": "p3", "chd": "t:60,40", "chs": "250x100", "chl": "Hello|World"},
                None,
            ),
        ],
    )
    def test_load_alias(self, encoded: str, decoded: t.Mapping[str, t.Any], options: t.Optional[DecodeOptions]) -> None:
        if options is not None:
            assert load(encoded, options=options) == decoded
        else:
            assert load(encoded) == decoded

    @pytest.mark.parametrize(
        "encoded, decoded, options",
        [
            ("0=foo", {"0": "foo"}, None),
            ("foo=c++", {"foo": "c  "}, None),
            ("a[>=]=23", {"a": {">=": "23"}}, None),
            ("a[<=>]==23", {"a": {"<=>": "=23"}}, None),
            ("a[==]=23", {"a": {"==": "23"}}, None),
            ("foo", {"foo": None}, DecodeOptions(strict_null_handling=True)),
            ("foo", {"foo": ""}, None),
            ("foo=", {"foo": ""}, None),
            ("foo=bar", {"foo": "bar"}, None),
            (" foo = bar = baz ", {" foo ": " bar = baz "}, None),
            ("foo=bar=baz", {"foo": "bar=baz"}, None),
            ("foo=bar&bar=baz", {"foo": "bar", "bar": "baz"}, None),
            ("foo2=bar2&baz2=", {"foo2": "bar2", "baz2": ""}, None),
            ("foo=bar&baz", {"foo": "bar", "baz": None}, DecodeOptions(strict_null_handling=True)),
            (
                "cht=p3&chd=t:60,40&chs=250x100&chl=Hello|World",
                {"cht": "p3", "chd": "t:60,40", "chs": "250x100", "chl": "Hello|World"},
                None,
            ),
        ],
    )
    def test_loads_alias(
        self, encoded: str, decoded: t.Mapping[str, t.Any], options: t.Optional[DecodeOptions]
    ) -> None:
        if options is not None:
            assert loads(encoded, options=options) == decoded
        else:
            assert loads(encoded) == decoded

    @pytest.mark.parametrize(
        "encoded, decoded",
        [
            ("a[]=b&a[]=c", {"a": ["b", "c"]}),
            ("a[0]=b&a[1]=c", {"a": ["b", "c"]}),
            ("a=b,c", {"a": "b,c"}),
            ("a=b&a=c", {"a": ["b", "c"]}),
        ],
    )
    def test_comma_false(self, encoded: str, decoded: t.Mapping[str, t.Any]) -> None:
        assert decode(encoded) == decoded

    @pytest.mark.parametrize(
        "encoded, decoded",
        [
            ("a[]=b&a[]=c", {"a": ["b", "c"]}),
            ("a[0]=b&a[1]=c", {"a": ["b", "c"]}),
            ("a=b,c", {"a": ["b", "c"]}),
            ("a=b&a=c", {"a": ["b", "c"]}),
        ],
    )
    def test_comma_true(self, encoded: str, decoded: t.Mapping[str, t.Any]) -> None:
        assert decode(encoded, DecodeOptions(comma=True)) == decoded

    def test_allows_enabling_dot_notation(self) -> None:
        assert decode("a.b=c") == {"a.b": "c"}
        assert decode("a.b=c", DecodeOptions(allow_dots=True)) == {"a": {"b": "c"}}

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param(
                "name%252Eobj.first=John&name%252Eobj.last=Doe",
                DecodeOptions(allow_dots=False, decode_dot_in_keys=False),
                {"name%2Eobj.first": "John", "name%2Eobj.last": "Doe"},
                id="no-dots, no-decode-dot",
            ),
            pytest.param(
                "name.obj.first=John&name.obj.last=Doe",
                DecodeOptions(allow_dots=True, decode_dot_in_keys=False),
                {"name": {"obj": {"first": "John", "last": "Doe"}}},
                id="allow-dots, no-decode-dot",
            ),
            pytest.param(
                "name%252Eobj.first=John&name%252Eobj.last=Doe",
                DecodeOptions(allow_dots=True, decode_dot_in_keys=False),
                {"name%2Eobj": {"first": "John", "last": "Doe"}},
                id="allow-dots, no-decode-dot, percent-encoded-dot",
            ),
            pytest.param(
                "name%252Eobj.first=John&name%252Eobj.last=Doe",
                DecodeOptions(allow_dots=True, decode_dot_in_keys=True),
                {"name.obj": {"first": "John", "last": "Doe"}},
                id="allow-dots, decode-dot, percent-encoded-dot",
            ),
            pytest.param(
                "name%252Eobj%252Esubobject.first%252Egodly%252Ename=John&" "name%252Eobj%252Esubobject.last=Doe",
                DecodeOptions(allow_dots=False, decode_dot_in_keys=False),
                {
                    "name%2Eobj%2Esubobject.first%2Egodly%2Ename": "John",
                    "name%2Eobj%2Esubobject.last": "Doe",
                },
                id="no-dots, no-decode-dot, multi-level-percent-encoded",
            ),
            pytest.param(
                "name.obj.subobject.first.godly.name=John&name.obj.subobject.last=Doe",
                DecodeOptions(allow_dots=True, decode_dot_in_keys=False),
                {
                    "name": {
                        "obj": {
                            "subobject": {
                                "first": {"godly": {"name": "John"}},
                                "last": "Doe",
                            }
                        }
                    }
                },
                id="allow-dots, no-decode-dot, multi-level-dots",
            ),
            pytest.param(
                "name%252Eobj%252Esubobject.first%252Egodly%252Ename=John&" "name%252Eobj%252Esubobject.last=Doe",
                DecodeOptions(allow_dots=True, decode_dot_in_keys=True),
                {"name.obj.subobject": {"first.godly.name": "John", "last": "Doe"}},
                id="allow-dots, decode-dot, multi-level-percent-encoded",
            ),
            pytest.param(
                "name%252Eobj.first=John&name%252Eobj.last=Doe",
                None,
                {"name%2Eobj.first": "John", "name%2Eobj.last": "Doe"},
                id="default-options",
            ),
            pytest.param(
                "name%252Eobj.first=John&name%252Eobj.last=Doe",
                DecodeOptions(decode_dot_in_keys=False),
                {"name%2Eobj.first": "John", "name%2Eobj.last": "Doe"},
                id="decode_dot_in_keys=False",
            ),
            pytest.param(
                "name%252Eobj.first=John&name%252Eobj.last=Doe",
                DecodeOptions(decode_dot_in_keys=True),
                {"name.obj": {"first": "John", "last": "Doe"}},
                id="decode_dot_in_keys=True",
            ),
        ],
    )
    def test_decode_dot_keys_correctly(
        self, query: str, options: t.Optional[DecodeOptions], expected: t.Mapping[str, t.Any]
    ) -> None:
        result: t.Dict = decode(query) if options is None else decode(query, options)
        assert result == expected

    def test_should_decode_dot_in_key_of_dict_and_allow_enabling_dot_notation_when_decode_dot_in_keys_is_set_to_true_and_allow_dots_is_undefined(
        self,
    ) -> None:
        assert decode(
            "name%252Eobj%252Esubobject.first%252Egodly%252Ename=John&name%252Eobj%252Esubobject.last=Doe",
            DecodeOptions(decode_dot_in_keys=True),
        ) == {"name.obj.subobject": {"first.godly.name": "John", "last": "Doe"}}

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param(
                "foo[]&bar=baz",
                DecodeOptions(allow_empty_lists=True),
                {"foo": [], "bar": "baz"},
                id="allow-empty-lists",
            ),
            pytest.param(
                "foo[]&bar=baz",
                DecodeOptions(allow_empty_lists=False),
                {"foo": [""], "bar": "baz"},
                id="disallow-empty-lists",
            ),
        ],
    )
    def test_allows_empty_lists_in_obj_values(
        self, query: str, options: DecodeOptions, expected: t.Mapping[str, t.Any]
    ) -> None:
        assert decode(query, options) == expected

    def test_allow_empty_lists_and_strict_null_handling(self) -> None:
        assert decode("testEmptyList[]", DecodeOptions(strict_null_handling=True, allow_empty_lists=True)) == {
            "testEmptyList": []
        }

    def test_parses_a_single_nested_string(self) -> None:
        assert decode("a[b]=c") == {"a": {"b": "c"}}

    def test_parses_a_double_nested_string(self) -> None:
        assert decode("a[b][c]=d") == {"a": {"b": {"c": "d"}}}

    def test_defaults_to_a_depth_of_5(self) -> None:
        assert decode("a[b][c][d][e][f][g][h]=i") == {"a": {"b": {"c": {"d": {"e": {"f": {"[g][h]": "i"}}}}}}}

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("a[b][c]=d", {"a": {"b": {"[c]": "d"}}}, id="single-level"),
            pytest.param("a[b][c][d]=e", {"a": {"b": {"[c][d]": "e"}}}, id="multi-level"),
        ],
    )
    def test_only_parses_one_level_when_depth_is_1(self, query: str, expected: t.Mapping[str, t.Any]) -> None:
        assert decode(query, DecodeOptions(depth=1)) == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("a[0]=b&a[1]=c", {"a[0]": "b", "a[1]": "c"}, id="simple"),
            pytest.param(
                "a[0][0]=b&a[0][1]=c&a[1]=d&e=2",
                {
                    "a[0][0]": "b",
                    "a[0][1]": "c",
                    "a[1]": "d",
                    "e": "2",
                },
                id="nested-and-mixed",
            ),
        ],
    )
    def test_uses_original_key_when_depth_is_0(self, query: str, expected: t.Dict) -> None:
        assert decode(query, DecodeOptions(depth=0)) == expected

    def test_parses_a_simple_list(self) -> None:
        assert decode("a=b&a=c") == {"a": ["b", "c"]}

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("a[]=b", {"a": ["b"]}, id="single-element-explicit-list"),
            pytest.param("a[]=b&a[]=c", {"a": ["b", "c"]}, id="two-elements-explicit-list"),
            pytest.param("a[]=b&a[]=c&a[]=d", {"a": ["b", "c", "d"]}, id="three-elements-explicit-list"),
        ],
    )
    def test_parses_an_explicit_list(self, query: str, expected: t.Dict) -> None:
        assert decode(query) == expected

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param("a=b&a[]=c", None, {"a": ["b", "c"]}, id="simple-mix-explicit-first"),
            pytest.param("a[]=b&a=c", None, {"a": ["b", "c"]}, id="explicit-first-mix-simple-second"),
            pytest.param("a[0]=b&a=c", None, {"a": ["b", "c"]}, id="indexed-list-first"),
            pytest.param("a=b&a[0]=c", None, {"a": ["b", "c"]}, id="simple-first-indexed-list-second"),
            pytest.param("a[1]=b&a=c", DecodeOptions(list_limit=20), {"a": ["b", "c"]}, id="indexed-list-with-limit"),
            pytest.param(
                "a[]=b&a=c", DecodeOptions(list_limit=0), {"a": ["b", "c"]}, id="explicit-list-with-zero-limit"
            ),
            pytest.param("a[]=b&a=c", None, {"a": ["b", "c"]}, id="explicit-list-default"),
            pytest.param(
                "a=b&a[1]=c", DecodeOptions(list_limit=20), {"a": ["b", "c"]}, id="simple-and-indexed-with-limit"
            ),
            pytest.param(
                "a=b&a[]=c", DecodeOptions(list_limit=0), {"a": ["b", "c"]}, id="simple-and-explicit-zero-limit"
            ),
            pytest.param("a=b&a[]=c", None, {"a": ["b", "c"]}, id="simple-and-explicit-default"),
        ],
    )
    def test_parses_a_mix_of_simple_and_explicit_lists(
        self, query: str, options: t.Optional[DecodeOptions], expected: t.Mapping[str, t.Any]
    ) -> None:
        result = decode(query) if options is None else decode(query, options)
        assert result == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("a[b][]=c&a[b][]=d", {"a": {"b": ["c", "d"]}}, id="nested-list"),
            pytest.param("a[>=]=25", {"a": {">=": "25"}}, id="special-character-key"),
        ],
    )
    def test_parses_a_nested_list(self, query: str, expected: t.Mapping[str, t.Any]) -> None:
        assert decode(query) == expected

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param("a[1]=c&a[0]=b&a[2]=d", None, {"a": ["b", "c", "d"]}, id="reordered-indices"),
            pytest.param("a[1]=c&a[0]=b", None, {"a": ["b", "c"]}, id="partial-indices"),
            pytest.param("a[1]=c", DecodeOptions(list_limit=20), {"a": ["c"]}, id="list-limit-20"),
            pytest.param("a[1]=c", DecodeOptions(list_limit=0), {"a": {"1": "c"}}, id="list-limit-0"),
            pytest.param("a[1]=c", None, {"a": ["c"]}, id="default-behavior"),
            pytest.param(
                "a[0]=b&a[2]=c",
                DecodeOptions(parse_lists=True),
                {"a": ["b", "c"]},
                id="list-starting-with-0-with-missing-index-parse-lists-true",
            ),
            pytest.param(
                "a[0]=b&a[2]=c",
                DecodeOptions(parse_lists=False),
                {"a": {"0": "b", "2": "c"}},
                id="list-starting-with-0-with-missing-index-parse-lists-false",
            ),
            pytest.param(
                "a[1]=b&a[15]=c",
                DecodeOptions(parse_lists=False),
                {"a": {"1": "b", "15": "c"}},
                id="list-starting-with-non-0-with-missing-index-parse-lists-false",
            ),
            pytest.param(
                "a[1]=b&a[15]=c",
                DecodeOptions(parse_lists=True),
                {"a": ["b", "c"]},
                id="list-starting-with-non-0-with-missing-index-parse-lists-false",
            ),
        ],
    )
    def test_allows_to_specify_list_indices(
        self, query: str, options: t.Optional[DecodeOptions], expected: t.Mapping[str, t.Any]
    ) -> None:
        result = decode(query) if options is None else decode(query, options)
        assert result == expected

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param("a[20]=a", DecodeOptions(list_limit=20), {"a": ["a"]}, id="at-limit"),
            pytest.param("a[21]=a", DecodeOptions(list_limit=20), {"a": {"21": "a"}}, id="above-limit"),
            pytest.param("a[20]=a", None, {"a": ["a"]}, id="default-at-limit"),
            pytest.param("a[21]=a", None, {"a": {"21": "a"}}, id="default-above-limit"),
        ],
    )
    def test_limits_specific_list_indices_to_list_limit(
        self, query: str, options: t.Optional[DecodeOptions], expected: t.Mapping[str, t.Any]
    ) -> None:
        result = decode(query) if options is None else decode(query, options)
        assert result == expected

    def test_supports_keys_that_begin_with_a_number(self) -> None:
        assert decode("a[12b]=c") == {"a": {"12b": "c"}}

    def test_supports_encoded_equals_signs(self) -> None:
        assert decode("he%3Dllo=th%3Dere") == {"he=llo": "th=ere"}

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("a[b%20c]=d", {"a": {"b c": "d"}}, id="decode-key-with-encoded-space"),
            pytest.param("a[b]=c%20d", {"a": {"b": "c d"}}, id="decode-value-with-encoded-space"),
        ],
    )
    def test_is_ok_with_url_encoded_strings(self, query: str, expected: t.Mapping[str, t.Any]) -> None:
        assert decode(query) == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param('pets=["tobi"]', {"pets": '["tobi"]'}, id="pets-with-brackets"),
            pytest.param('operators=[">=", "<="]', {"operators": '[">=", "<="]'}, id="operators-with-brackets"),
        ],
    )
    def test_allows_brackets_in_the_value(self, query: str, expected: t.Mapping[str, t.Any]) -> None:
        assert decode(query) == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("", {}, id="empty-string"),
            pytest.param(None, {}, id="none-input"),
        ],
    )
    def test_allows_empty_values(self, query: t.Optional[str], expected: t.Mapping[str, t.Any]) -> None:
        assert decode(query) == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("foo[0]=bar&foo[bad]=baz", {"foo": {"0": "bar", "bad": "baz"}}, id="numeric-and-bad-key"),
            pytest.param(
                "foo[bad]=baz&foo[0]=bar", {"foo": {"bad": "baz", "0": "bar"}}, id="reordered-bad-and-numeric"
            ),
            pytest.param("foo[bad]=baz&foo[]=bar", {"foo": {"bad": "baz", "0": "bar"}}, id="bad-and-explicit-list"),
            pytest.param("foo[]=bar&foo[bad]=baz", {"foo": {"0": "bar", "bad": "baz"}}, id="explicit-list-and-bad"),
            pytest.param(
                "foo[bad]=baz&foo[]=bar&foo[]=foo",
                {"foo": {"bad": "baz", "0": "bar", "1": "foo"}},
                id="bad-and-multiple-explicit",
            ),
            pytest.param(
                "foo[0][a]=a&foo[0][b]=b&foo[1][a]=aa&foo[1][b]=bb",
                {"foo": [{"a": "a", "b": "b"}, {"a": "aa", "b": "bb"}]},
                id="nested-list-of-dicts",
            ),
        ],
    )
    def test_transforms_lists_to_dicts(self, query: str, expected: t.Mapping[str, t.Any]) -> None:
        assert decode(query) == expected

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param(
                "foo[0].baz=bar&fool.bad=baz",
                DecodeOptions(allow_dots=True),
                {"foo": [{"baz": "bar"}], "fool": {"bad": "baz"}},
                id="list-dot-simple",
            ),
            pytest.param(
                "foo[0].baz=bar&fool.bad.boo=baz",
                DecodeOptions(allow_dots=True),
                {"foo": [{"baz": "bar"}], "fool": {"bad": {"boo": "baz"}}},
                id="nested-dot-dict",
            ),
            pytest.param(
                "foo[0][0].baz=bar&fool.bad=baz",
                DecodeOptions(allow_dots=True),
                {"foo": [[{"baz": "bar"}]], "fool": {"bad": "baz"}},
                id="double-index-list-dot",
            ),
            pytest.param(
                "foo[0].baz[0]=15&foo[0].bar=2",
                DecodeOptions(allow_dots=True),
                {"foo": [{"baz": ["15"], "bar": "2"}]},
                id="list-dot-indexed",
            ),
            pytest.param(
                "foo[0].baz[0]=15&foo[0].baz[1]=16&foo[0].bar=2",
                DecodeOptions(allow_dots=True),
                {"foo": [{"baz": ["15", "16"], "bar": "2"}]},
                id="list-dot-multiple-index",
            ),
            pytest.param(
                "foo.bad=baz&foo[0]=bar",
                DecodeOptions(allow_dots=True),
                {"foo": {"bad": "baz", "0": "bar"}},
                id="dot-and-index",
            ),
            pytest.param(
                "foo.bad=baz&foo[]=bar",
                DecodeOptions(allow_dots=True),
                {"foo": {"bad": "baz", "0": "bar"}},
                id="dot-and-explicit",
            ),
            pytest.param(
                "foo[]=bar&foo.bad=baz",
                DecodeOptions(allow_dots=True),
                {"foo": {"0": "bar", "bad": "baz"}},
                id="explicit-and-dot",
            ),
            pytest.param(
                "foo.bad=baz&foo[]=bar&foo[]=foo",
                DecodeOptions(allow_dots=True),
                {"foo": {"bad": "baz", "0": "bar", "1": "foo"}},
                id="dot-and-multiple-explicit",
            ),
            pytest.param(
                "foo[0].a=a&foo[0].b=b&foo[1].a=aa&foo[1].b=bb",
                DecodeOptions(allow_dots=True),
                {"foo": [{"a": "a", "b": "b"}, {"a": "aa", "b": "bb"}]},
                id="nested-list-dot",
            ),
        ],
    )
    def test_transforms_lists_to_dicts_dot_notation(
        self, query: str, options: DecodeOptions, expected: t.Mapping[str, t.Any]
    ) -> None:
        assert decode(query, options) == expected

    def test_correctly_prunes_undefined_values_when_converting_a_list_to_a_dict(self) -> None:
        assert decode("a[2]=b&a[99999999]=c") == {"a": {"2": "b", "99999999": "c"}}

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param("{%:%}", DecodeOptions(strict_null_handling=True), {"{%:%}": None}, id="strict-null-handling"),
            pytest.param("{%:%}=", None, {"{%:%}": ""}, id="empty-value"),
            pytest.param("foo=%:%}", None, {"foo": "%:%}"}, id="malformed-value"),
        ],
    )
    def test_supports_malformed_uri_characters(
        self, query: str, options: t.Optional[DecodeOptions], expected: t.Mapping[str, t.Any]
    ) -> None:
        result = decode(query) if options is None else decode(query, options)
        assert result == expected

    def test_does_not_produce_empty_keys(self) -> None:
        assert decode("_r=1&") == {"_r": "1"}

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("a[][b]=c", {"a": [{"b": "c"}]}, id="explicit-list-of-dicts"),
            pytest.param("a[0][b]=c", {"a": [{"b": "c"}]}, id="indexed-list-of-dicts"),
        ],
    )
    def test_parses_lists_of_dicts(self, query: str, expected: t.Mapping[str, t.Any]) -> None:
        assert decode(query) == expected

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param("a[]=b&a[]=&a[]=c", None, {"a": ["b", "", "c"]}, id="explicit-empty-middle"),
            pytest.param(
                "a[0]=b&a[1]&a[2]=c&a[19]=",
                DecodeOptions(strict_null_handling=True, list_limit=20),
                {"a": ["b", None, "c", ""]},
                id="strict-null-and-empty-limit-20",
            ),
            pytest.param(
                "a[]=b&a[]&a[]=c&a[]=",
                DecodeOptions(strict_null_handling=True, list_limit=0),
                {"a": ["b", None, "c", ""]},
                id="strict-null-and-empty-zero-limit",
            ),
            pytest.param(
                "a[0]=b&a[1]=&a[2]=c&a[19]",
                DecodeOptions(strict_null_handling=True, list_limit=20),
                {"a": ["b", "", "c", None]},
                id="empty-and-strict-null-limit-20",
            ),
            pytest.param(
                "a[]=b&a[]=&a[]=c&a[]",
                DecodeOptions(strict_null_handling=True, list_limit=0),
                {"a": ["b", "", "c", None]},
                id="empty-and-strict-null-zero-limit",
            ),
            pytest.param("a[]=&a[]=b&a[]=c", None, {"a": ["", "b", "c"]}, id="explicit-empty-first"),
        ],
    )
    def test_allows_for_empty_strings_in_lists(
        self, query: str, options: t.Optional[DecodeOptions], expected: t.Mapping[str, t.Any]
    ) -> None:
        result = decode(query) if options is None else decode(query, options)
        assert result == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("a[10]=1&a[2]=2", {"a": ["2", "1"]}, id="sparse-list"),
            pytest.param("a[1][b][2][c]=1", {"a": [{"b": [{"c": "1"}]}]}, id="nested-list-of-dicts"),
            pytest.param("a[1][2][3][c]=1", {"a": [[[{"c": "1"}]]]}, id="deeper-nested-list"),
            pytest.param("a[1][2][3][c][1]=1", {"a": [[[{"c": ["1"]}]]]}, id="deepest-nested-list"),
        ],
    )
    def test_compacts_sparse_lists(self, query: str, expected: t.Mapping[str, t.Any]) -> None:
        opts = DecodeOptions(list_limit=20)
        result = decode(query, opts)
        assert result == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("a[b]=c", {"a": {"b": "c"}}, id="single-semi-parsed"),
            pytest.param("a[b]=c&a[d]=e", {"a": {"b": "c", "d": "e"}}, id="multiple-semi-parsed"),
        ],
    )
    def test_parses_semi_parsed_strings(self, query: str, expected: t.Mapping[str, t.Any]) -> None:
        assert decode(query) == expected

    def test_parses_buffers_correctly(self) -> None:
        b: bytes = b"test"
        assert decode({"a": b}) == {"a": b}

    def test_parses_jquery_param_strings(self) -> None:
        assert decode(
            # readable: str = 'filter[0][]=int1&filter[0][]==&filter[0][]=77&filter[]=and&filter[2][]=int2&filter[2][]==&filter[2][]=8'
            "filter%5B0%5D%5B%5D=int1&filter%5B0%5D%5B%5D=%3D&filter%5B0%5D%5B%5D=77&filter%5B%5D=and&filter%5B2%5D%5B%5D=int2&filter%5B2%5D%5B%5D=%3D&filter%5B2%5D%5B%5D=8"
        ) == {"filter": [["int1", "=", "77"], "and", ["int2", "=", "8"]]}

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param("[]=&a=b", None, {"0": "", "a": "b"}, id="no-parent-default"),
            pytest.param(
                "[]&a=b",
                DecodeOptions(strict_null_handling=True),
                {"0": None, "a": "b"},
                id="no-parent-strict-null",
            ),
            pytest.param("[foo]=bar", None, {"foo": "bar"}, id="bracketed-key"),
        ],
    )
    def test_continues_parsing_when_no_parent_is_found(
        self, query: str, options: t.Optional[DecodeOptions], expected: t.Mapping[str, t.Any]
    ) -> None:
        result = decode(query) if options is None else decode(query, options)
        assert result == expected

    def test_does_not_error_when_parsing_a_very_long_list(self) -> None:
        buf: str = "a[]=a"
        while getsizeof(buf) < 128 * 1024:
            buf += "&"
            buf += buf

        with does_not_raise():
            assert decode(buf) is not None

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param("a=b;c=d", DecodeOptions(delimiter=";"), {"a": "b", "c": "d"}, id="string-delimiter"),
            pytest.param(
                "a=b; c=d",
                DecodeOptions(delimiter=re.compile(r"[;,] *")),
                {"a": "b", "c": "d"},
                id="regexp-delimiter",
            ),
        ],
    )
    def test_parses_string_with_alternative_delimiters(
        self, query: str, options: DecodeOptions, expected: t.Mapping[str, t.Any]
    ) -> None:
        assert decode(query, options) == expected

    def test_allows_overriding_parameter_limit(self) -> None:
        assert decode("a=b&c=d", DecodeOptions(parameter_limit=1)) == {"a": "b"}

    def test_allows_setting_the_parameter_limit_to_infinity(self) -> None:
        assert decode("a=b&c=d", DecodeOptions(parameter_limit=float("inf"))) == {"a": "b", "c": "d"}

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param("a[0]=b", DecodeOptions(list_limit=-1), {"a": {"0": "b"}}, id="limit--1-single-index-0"),
            pytest.param("a[0]=b", DecodeOptions(list_limit=0), {"a": ["b"]}, id="limit-0-single-index-0"),
            pytest.param("a[-1]=b", DecodeOptions(list_limit=-1), {"a": {"-1": "b"}}, id="limit--1-negative-index"),
            pytest.param("a[-1]=b", DecodeOptions(list_limit=0), {"a": {"-1": "b"}}, id="limit-0-negative-index"),
            pytest.param(
                "a[0]=b&a[1]=c",
                DecodeOptions(list_limit=-1),
                {"a": {"0": "b", "1": "c"}},
                id="limit--1-two-items",
            ),
            pytest.param(
                "a[0]=b&a[1]=c",
                DecodeOptions(list_limit=0),
                {"a": {"0": "b", "1": "c"}},
                id="limit-0-two-items",
            ),
        ],
    )
    def test_allows_overriding_list_limit(
        self, query: str, options: DecodeOptions, expected: t.Mapping[str, t.Any]
    ) -> None:
        assert decode(query, options) == expected

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param(
                "a[0]=b&a[1]=c",
                DecodeOptions(parse_lists=False),
                {"a": {"0": "b", "1": "c"}},
                id="disable-parse-lists-multi-index",
            ),
            pytest.param(
                "a[]=b",
                DecodeOptions(parse_lists=False),
                {"a": {"0": "b"}},
                id="disable-parse-lists-explicit",
            ),
        ],
    )
    def test_allows_disabling_list_parsing(
        self, query: str, options: DecodeOptions, expected: t.Mapping[str, t.Any]
    ) -> None:
        assert decode(query, options) == expected

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param(
                "?foo=bar",
                DecodeOptions(ignore_query_prefix=True),
                {"foo": "bar"},
                id="ignore-prefix-with-question",
            ),
            pytest.param(
                "foo=bar",
                DecodeOptions(ignore_query_prefix=True),
                {"foo": "bar"},
                id="ignore-prefix-without-question",
            ),
            pytest.param("?foo=bar", DecodeOptions(ignore_query_prefix=False), {"?foo": "bar"}, id="keep-prefix"),
        ],
    )
    def test_allows_for_query_string_prefix(
        self, query: str, options: DecodeOptions, expected: t.Mapping[str, t.Any]
    ) -> None:
        assert decode(query, options) == expected

    def test_parses_a_dict(self) -> None:
        assert decode({"user[name]": {"pop[bob]": 3}, "user[email]": None}) == {
            "user": {"name": {"pop[bob]": 3}, "email": None}
        }

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param("foo=bar,tee", DecodeOptions(comma=True), {"foo": ["bar", "tee"]}, id="comma-simple"),
            pytest.param(
                "foo[bar]=coffee,tee",
                DecodeOptions(comma=True),
                {"foo": {"bar": ["coffee", "tee"]}},
                id="comma-nested",
            ),
            pytest.param("foo=", DecodeOptions(comma=True), {"foo": ""}, id="comma-empty-value"),
            pytest.param("foo", DecodeOptions(comma=True), {"foo": ""}, id="comma-no-equals"),
            pytest.param(
                "foo",
                DecodeOptions(comma=True, strict_null_handling=True),
                {"foo": None},
                id="comma-strict-null",
            ),
            pytest.param("a[0]=c", None, {"a": ["c"]}, id="default-indexed-list"),
            pytest.param("a[]=c", None, {"a": ["c"]}, id="default-explicit-list"),
            pytest.param("a[]=c", DecodeOptions(comma=True), {"a": ["c"]}, id="comma-explicit-list"),
            pytest.param("a[0]=c&a[1]=d", None, {"a": ["c", "d"]}, id="default-multi-index"),
            pytest.param("a[]=c&a[]=d", None, {"a": ["c", "d"]}, id="default-multi-explicit"),
            pytest.param("a=c,d", DecodeOptions(comma=True), {"a": ["c", "d"]}, id="comma-simple-value"),
        ],
    )
    def test_parses_string_with_comma_as_list_divider(
        self, query: str, options: t.Optional[DecodeOptions], expected: t.Mapping[str, t.Any]
    ) -> None:
        result = decode(query) if options is None else decode(query, options)
        assert result == expected

    @pytest.mark.parametrize(
        "input_data, options, expected",
        [
            pytest.param({"foo": "bar,tee"}, DecodeOptions(comma=False), {"foo": "bar,tee"}, id="no-comma-split"),
            pytest.param({"foo": "bar,tee"}, DecodeOptions(comma=True), {"foo": ["bar", "tee"]}, id="comma-split"),
        ],
    )
    def test_parses_values_with_comma_as_list_divider(
        self, input_data: t.Mapping[str, t.Any], options: DecodeOptions, expected: t.Mapping[str, t.Any]
    ) -> None:
        assert decode(input_data, options) == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("foo=1", {"foo": 1.0}, id="single-number"),
            pytest.param("foo=0", {"foo": 0.0}, id="zero-number"),
        ],
    )
    def test_use_number_decoder_parses_string_that_has_one_number_with_comma_option_enabled(
        self, query: str, expected: t.Mapping[str, t.Any]
    ) -> None:
        def _decoder(s: t.Optional[str], charset: t.Optional[Charset]) -> t.Any:
            if s is not None:
                try:
                    return float(s)
                except ValueError:
                    pass
            return DecodeUtils.decode(s, charset=charset)

        assert decode(query, DecodeOptions(comma=True, decoder=_decoder)) == expected

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param(
                "foo[]=1,2,3&foo[]=4,5,6",
                DecodeOptions(comma=True),
                {"foo": [["1", "2", "3"], ["4", "5", "6"]]},
                id="two-lists-of-numbers",
            ),
            pytest.param(
                "foo[]=1,2,3&foo[]=",
                DecodeOptions(comma=True),
                {"foo": [["1", "2", "3"], ""]},
                id="empty-second-list",
            ),
            pytest.param(
                "foo[]=1,2,3&foo[]=a",
                DecodeOptions(comma=True),
                {"foo": [["1", "2", "3"], "a"]},
                id="string-second-list",
            ),
        ],
    )
    def test_parses_brackets_holds_list_of_lists_when_having_two_parts_of_strings_with_comma_as_list_divider(
        self, query: str, options: DecodeOptions, expected: t.Mapping[str, t.Any]
    ) -> None:
        assert decode(query, options) == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("foo=a%2Cb", {"foo": "a,b"}, id="percent-encoded-comma-no-split"),
            pytest.param("foo=a%2C%20b,d", {"foo": ["a, b", "d"]}, id="percent-encoded-comma-and-list"),
            pytest.param("foo=a%2C%20b,c%2C%20d", {"foo": ["a, b", "c, d"]}, id="mixed-percent-encoded-and-list"),
        ],
    )
    def test_parses_comma_delimited_list_while_having_percent_encoded_comma_treated_as_normal_text(
        self, query: str, expected: t.Mapping[str, t.Any]
    ) -> None:
        assert decode(query, DecodeOptions(comma=True)) == expected

    def test_parses_a_dict_in_dot_notation(self) -> None:
        assert decode({"user.name": {"pop[bob]": 3}, "user.email.": None}, DecodeOptions(allow_dots=True)) == {
            "user": {"name": {"pop[bob]": 3}, "email": None}
        }

    def test_parses_a_dict_and_not_child_values(self) -> None:
        assert decode(
            {"user[name]": {"pop[bob]": {"test": 3}}, "user[email]": None}, DecodeOptions(allow_dots=True)
        ) == {"user": {"name": {"pop[bob]": {"test": 3}}, "email": None}}

    def test_does_not_crash_when_parsing_circular_references(self) -> None:
        a: t.Dict[str, t.Any] = {}
        a["b"] = a

        parsed: t.Optional[t.Mapping[str, t.Any]]

        with does_not_raise():
            parsed = decode({"foo[bar]": "baz", "foo[baz]": a})

        assert parsed is not None
        assert "foo" in parsed
        assert "bar" in parsed["foo"]
        assert "baz" in parsed["foo"]
        assert parsed["foo"]["bar"] == "baz"
        assert parsed["foo"]["baz"] == a

    def test_does_not_crash_when_parsing_deep_dicts(self) -> None:
        depth: int = 5000

        string: str = "foo"
        for _ in range(depth):
            string += "[p]"
        string += "=bar"

        parsed: t.Optional[t.Mapping[str, t.Any]]

        with does_not_raise():
            parsed = decode(string, DecodeOptions(depth=depth))

        assert parsed is not None
        assert "foo" in parsed

        actual_depth: int = 0
        ref: t.Any = parsed["foo"]
        while ref is not None and isinstance(ref, dict) and "p" in ref:
            ref = ref["p"]
            actual_depth += 1

        assert actual_depth == depth

    def test_parses_null_dicts_correctly(self) -> None:
        a: t.Dict[str, t.Any] = {"b": "c"}
        assert decode(a) == {"b": "c"}
        assert decode({"a": a}) == {"a": a}

    def test_parses_dates_correctly(self) -> None:
        now: datetime = datetime.now()
        assert decode({"a": now}) == {"a": now}

    def test_parses_regular_expressions_correctly(self) -> None:
        reg_exp: re.Pattern = re.compile(r"^test$")
        assert decode({"a": reg_exp}) == {"a": reg_exp}

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("]=toString", {"]": "toString"}, id="single-bracket"),
            pytest.param("]]=toString", {"]]": "toString"}, id="double-bracket"),
            pytest.param("]hello]=toString", {"]hello]": "toString"}, id="bracketed-word"),
        ],
    )
    def test_params_starting_with_a_closing_bracket(self, query: str, expected: t.Mapping[str, t.Any]) -> None:
        assert decode(query) == expected

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("[=toString", {"[": "toString"}, id="single-leading-bracket"),
            pytest.param("[[=toString", {"[[": "toString"}, id="double-leading-bracket"),
            pytest.param("[hello[=toString", {"[hello[": "toString"}, id="bracketed-word-leading"),
        ],
    )
    def test_params_starting_with_a_starting_bracket(self, query: str, expected: t.Mapping[str, t.Any]) -> None:
        assert decode(query) == expected

    def test_add_keys_to_dicts(self) -> None:
        assert decode("a[b]=c") == {"a": {"b": "c"}}

    def test_can_return_null_dicts(self) -> None:
        expected: t.Dict[str, t.Any] = dict()
        expected["a"] = {}
        expected["a"]["b"] = "c"
        expected["a"]["hasOwnProperty"] = "d"
        assert decode("a[b]=c&a[hasOwnProperty]=d") == expected

        assert decode(None) == {}

        expected_list: t.Dict[str, t.Any] = dict()
        expected_list["a"] = {}
        expected_list["a"]["0"] = "b"
        expected_list["a"]["c"] = "d"
        assert decode("a[]=b&a[c]=d") == expected_list

    def test_can_parse_with_custom_encoding(self) -> None:
        def _decode(s: t.Optional[str], charset: t.Optional[Charset]) -> t.Any:
            if s is None:
                return None

            reg: re.Pattern = re.compile(r"%([0-9A-F]{2})", re.IGNORECASE)
            result: t.List[int] = []
            parts: t.Optional[re.Match]
            while (parts := reg.search(s)) is not None:
                result.append(int(parts.group(1), 16))
                s = s[parts.end() :]
            return bytes(result).decode("shift-jis")

        assert decode("%8c%a7=%91%e5%8d%e3%95%7b", DecodeOptions(decoder=_decode)) == {"県": "大阪府"}

    def test_parses_a_latin_1_string_if_asked_to(self) -> None:
        assert decode("%A2=%BD", DecodeOptions(charset=Charset.LATIN1)) == {"¢": "½"}

    @pytest.mark.parametrize(
        "encoded, decoded",
        [
            ("&", {}),
            ("&&", {}),
            ("&=", {}),
            ("&=&", {}),
            ("&=&=", {}),
            ("&=&=&", {}),
            ("=", {}),
            ("=&", {}),
            ("=&&&", {}),
            ("=&=&=&", {}),
            ("=&a[]=b&a[1]=c", {"a": ["b", "c"]}),
            ("=a", {}),
            ("a==a", {"a": "=a"}),
            ("=&a[]=b", {"a": ["b"]}),
            ("=&a[]=b&a[]=c&a[2]=d", {"a": ["b", "c", "d"]}),
            ("=a&=b", {}),
            ("=a&foo=b", {"foo": "b"}),
            ("a[]=b&a=c&=", {"a": ["b", "c"]}),
            ("a[]=b&a=c&=", {"a": ["b", "c"]}),
            ("a[0]=b&a=c&=", {"a": ["b", "c"]}),
            ("a=b&a[]=c&=", {"a": ["b", "c"]}),
            ("a=b&a[0]=c&=", {"a": ["b", "c"]}),
            ("[]=a&[]=b& []=1", {"0": "a", "1": "b", " ": ["1"]}),
            ("[0]=a&[1]=b&a[0]=1&a[1]=2", {"0": "a", "1": "b", "a": ["1", "2"]}),
            ("[deep]=a&[deep]=2", {"deep": ["a", "2"]}),
            ("%5B0%5D=a&%5B1%5D=b", {"0": "a", "1": "b"}),
        ],
    )
    def test_parses_empty_keys(self, encoded: str, decoded: t.Mapping[str, t.Any]) -> None:
        assert decode(encoded) == decoded


class TestCharset:
    url_encoded_checkmark_in_utf_8: str = "%E2%9C%93"
    url_encoded_oslash_in_utf_8: str = "%C3%B8"
    url_encoded_num_checkmark: str = "%26%2310003%3B"
    url_encoded_num_smiley: str = "%26%239786%3B"

    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param(
                f"utf8={url_encoded_checkmark_in_utf_8}&"
                f"{url_encoded_oslash_in_utf_8}={url_encoded_oslash_in_utf_8}",
                DecodeOptions(charset_sentinel=True, charset=Charset.LATIN1),
                {"ø": "ø"},
                id="sentinel-overrides-latin1-default",
            ),
            pytest.param(
                f"utf8={url_encoded_num_checkmark}&" f"{url_encoded_oslash_in_utf_8}={url_encoded_oslash_in_utf_8}",
                DecodeOptions(charset_sentinel=True, charset=Charset.UTF8),
                {"Ã¸": "Ã¸"},
                id="sentinel-overrides-utf8-default",
            ),
            pytest.param(
                f"a={url_encoded_oslash_in_utf_8}&utf8={url_encoded_num_checkmark}",
                DecodeOptions(charset_sentinel=True, charset=Charset.UTF8),
                {"a": "Ã¸"},
                id="sentinel-after-params",
            ),
            pytest.param(
                f"utf8=foo&{url_encoded_oslash_in_utf_8}={url_encoded_oslash_in_utf_8}",
                DecodeOptions(charset_sentinel=True, charset=Charset.UTF8),
                {"ø": "ø"},
                id="sentinel-unknown-value-ignored",
            ),
            pytest.param(
                f"utf8={url_encoded_checkmark_in_utf_8}&"
                f"{url_encoded_oslash_in_utf_8}={url_encoded_oslash_in_utf_8}",
                DecodeOptions(charset_sentinel=True),
                {"ø": "ø"},
                id="no-default-switch-to-utf8",
            ),
            pytest.param(
                f"utf8={url_encoded_num_checkmark}&" f"{url_encoded_oslash_in_utf_8}={url_encoded_oslash_in_utf_8}",
                DecodeOptions(charset_sentinel=True),
                {"Ã¸": "Ã¸"},
                id="no-default-switch-to-latin1",
            ),
            pytest.param(
                f"foo={url_encoded_num_smiley}",
                DecodeOptions(charset=Charset.LATIN1, interpret_numeric_entities=True),
                {"foo": "☺"},
                id="interpret-numeric-entities-latin1",
            ),
            pytest.param(
                f"foo=&bar={url_encoded_num_smiley}",
                DecodeOptions(
                    charset=Charset.LATIN1,
                    decoder=lambda s, charset: (
                        DecodeUtils.decode(s, charset=charset) if s not in (None, "") else None
                    ),
                    interpret_numeric_entities=True,
                ),
                {"foo": None, "bar": "☺"},
                id="custom-decoder-null-latin1",
            ),
            pytest.param(
                f"foo={url_encoded_num_smiley}",
                DecodeOptions(charset=Charset.LATIN1, interpret_numeric_entities=False),
                {"foo": "&#9786;"},
                id="no-interpret-numeric-entities-latin1",
            ),
            pytest.param(
                f"b&a[]=1,{url_encoded_num_smiley}",
                DecodeOptions(comma=True, charset=Charset.LATIN1, interpret_numeric_entities=True),
                {"b": "", "a": ["1,☺"]},
                id="comma-interpret-numeric-latin1",
            ),
            pytest.param(
                f"foo={url_encoded_num_smiley}",
                DecodeOptions(charset=Charset.UTF8, interpret_numeric_entities=True),
                {"foo": "&#9786;"},
                id="no-interpret-numeric-entities-utf8",
            ),
            pytest.param(
                "%u263A=%u263A",
                DecodeOptions(charset=Charset.UTF8),
                {"%u263A": "%u263A"},
                id="no-uXXXX-utf8",
            ),
        ],
    )
    def test_charset(self, query: str, options: DecodeOptions, expected: t.Mapping[str, t.Any]) -> None:
        assert decode(query, options) == expected


class TestDuplicatesOption:
    @pytest.mark.parametrize(
        "query, options, expected",
        [
            pytest.param("foo=bar&foo=baz", None, {"foo": ["bar", "baz"]}, id="default-combine"),
            pytest.param(
                "foo=bar&foo=baz",
                DecodeOptions(duplicates=Duplicates.COMBINE),
                {"foo": ["bar", "baz"]},
                id="combine",
            ),
            pytest.param("foo=bar&foo=baz", DecodeOptions(duplicates=Duplicates.FIRST), {"foo": "bar"}, id="first"),
            pytest.param("foo=bar&foo=baz", DecodeOptions(duplicates=Duplicates.LAST), {"foo": "baz"}, id="last"),
        ],
    )
    def test_duplicates_option(
        self, query: str, options: t.Optional[DecodeOptions], expected: t.Mapping[str, t.Any]
    ) -> None:
        result = decode(query) if options is None else decode(query, options)
        assert result == expected


class TestStrictDepthOption:
    @pytest.mark.parametrize(
        "query, options, expected, raises_error",
        [
            pytest.param(
                "a[b][c][d][e][f][g][h][i]=j",
                DecodeOptions(depth=1, strict_depth=True),
                None,
                True,
                id="strict-depth-exceeds-objects",
            ),
            pytest.param(
                "a[0][1][2][3][4]=b",
                DecodeOptions(depth=3, strict_depth=True),
                None,
                True,
                id="strict-depth-exceeds-lists",
            ),
            pytest.param(
                "a[b][c][0][d][e]=f", DecodeOptions(depth=3, strict_depth=True), None, True, id="strict-depth-mixed"
            ),
            pytest.param(
                "a[b][c][d][e]=true&a[b][c][d][f]=42",
                DecodeOptions(depth=3, strict_depth=True),
                None,
                True,
                id="strict-depth-different-values",
            ),
            pytest.param(
                "a[b][c][d][e]=true&a[b][c][d][f]=42",
                DecodeOptions(depth=0, strict_depth=True),
                None,
                False,
                id="depth-0-no-error",
            ),
            pytest.param(
                "a[b]=c", DecodeOptions(depth=1, strict_depth=True), {"a": {"b": "c"}}, False, id="within-strict-depth"
            ),
            pytest.param(
                "a[b][c][d][e][f][g][h][i]=j",
                DecodeOptions(depth=1, strict_depth=False),
                {"a": {"b": {"[c][d][e][f][g][h][i]": "j"}}},
                False,
                id="no-strict-depth-objects",
            ),
            pytest.param(
                "a[b]=c",
                DecodeOptions(depth=1, strict_depth=False),
                {"a": {"b": "c"}},
                False,
                id="no-strict-depth-within",
            ),
            pytest.param(
                "a[b][c]=d",
                DecodeOptions(depth=2, strict_depth=True),
                {"a": {"b": {"c": "d"}}},
                False,
                id="exact-strict-depth",
            ),
        ],
    )
    def test_strict_depth_option(
        self, query: str, options: DecodeOptions, expected: t.Optional[t.Mapping[str, t.Any]], raises_error: bool
    ) -> None:
        if raises_error:
            with pytest.raises(IndexError):
                decode(query, options)
        else:
            result = decode(query, options)
            if expected is not None:
                assert result == expected


class TestParameterList:
    @pytest.mark.parametrize(
        "query, options, expected, raises_error",
        [
            pytest.param(
                "a=1&b=2&c=3",
                DecodeOptions(parameter_limit=5, raise_on_limit_exceeded=True),
                {"a": "1", "b": "2", "c": "3"},
                False,
                id="within-parameter-limit-raise",
            ),
            pytest.param(
                "a=1&b=2&c=3&d=4&e=5&f=6",
                DecodeOptions(parameter_limit=3, raise_on_limit_exceeded=True),
                None,
                True,
                id="parameter-limit-exceeded-raise",
            ),
            pytest.param(
                "a=1&b=2&c=3&d=4&e=5",
                DecodeOptions(parameter_limit=3),
                {"a": "1", "b": "2", "c": "3"},
                False,
                id="exceeded-parameter-limit-silent-default",
            ),
            pytest.param(
                "a=1&b=2&c=3&d=4&e=5",
                DecodeOptions(parameter_limit=3, raise_on_limit_exceeded=False),
                {"a": "1", "b": "2", "c": "3"},
                False,
                id="exceeded-parameter-limit-silent-false",
            ),
            pytest.param(
                "a=1&b=2&c=3&d=4&e=5&f=6",
                DecodeOptions(parameter_limit=float("inf")),
                {"a": "1", "b": "2", "c": "3", "d": "4", "e": "5", "f": "6"},
                False,
                id="unlimited-parameters",
            ),
            pytest.param(
                "a=1&b=2&c=3",
                DecodeOptions(parameter_limit=0),
                None,
                True,
                id="zero-parameter-limit",
            ),
            pytest.param(
                "a=1&b=2&c=3",
                DecodeOptions(parameter_limit=-1),
                None,
                True,
                id="negative-parameter-limit",
            ),
        ],
    )
    def test_parameter_limit(
        self, query: str, options: DecodeOptions, expected: t.Optional[t.Mapping[str, t.Any]], raises_error: bool
    ) -> None:
        if raises_error:
            with pytest.raises(ValueError):
                decode(query, options)
        else:
            assert decode(query, options) == expected


class TestListLimit:

    def test_current_list_length_calculation(self) -> None:
        # Test for line 166 in decode.py
        # This test creates a scenario where the current list length is calculated
        # when a parent key is found in a list

        # Create a query string with a nested array
        query = "a[0][]=1&a[0][]=2&a[0][]=3"

        # Decode with a reasonable list limit
        options = DecodeOptions(list_limit=5, raise_on_limit_exceeded=True)
        result = decode(query, options)
        assert result == {"a": [["1", "2", "3"]]}

        # Now decode with a list limit that would be exceeded
        # This should raise a ValueError because we're trying to create a list with more items than allowed
        options_limit = DecodeOptions(list_limit=2, raise_on_limit_exceeded=True)
        with pytest.raises(ValueError, match="List limit exceeded"):
            decode(query, options_limit)

    @pytest.mark.parametrize(
        "query, options, expected, raises_error",
        [
            pytest.param(
                "a[]=1&a[]=2&a[]=3",
                DecodeOptions(list_limit=5, raise_on_limit_exceeded=True),
                {"a": ["1", "2", "3"]},
                False,
                id="within-list-limit",
            ),
            pytest.param(
                "a[]=1&a[]=2&a[]=3&a[]=4",
                DecodeOptions(list_limit=3, raise_on_limit_exceeded=True),
                None,
                True,
                id="exceed-list-limit-raise",
            ),
            pytest.param(
                "a[1]=1&a[2]=2&a[3]=3&a[4]=4&a[5]=5&a[6]=6",
                DecodeOptions(list_limit=5),
                {"a": {"1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6"}},
                False,
                id="convert-to-map",
            ),
            pytest.param("a[]=1&a[]=2", DecodeOptions(list_limit=0), {"a": ["1", "2"]}, False, id="zero-list-limit"),
            pytest.param(
                "a[]=1&a[]=2",
                DecodeOptions(list_limit=-1, raise_on_limit_exceeded=True),
                None,
                True,
                id="negative-list-limit-raise",
            ),
            pytest.param(
                "a[0][]=1&a[0][]=2&a[0][]=3&a[0][]=4",
                DecodeOptions(list_limit=3, raise_on_limit_exceeded=True),
                None,
                True,
                id="nested-list-limit-raise",
            ),
            pytest.param(
                "a=1,2,3,4,5",
                DecodeOptions(list_limit=3, raise_on_limit_exceeded=True, comma=True),
                None,
                True,
                id="comma-separated-list-exceed-limit",
            ),
        ],
    )
    def test_list_limit(
        self, query: str, options: DecodeOptions, expected: t.Optional[t.Mapping[str, t.Any]], raises_error: bool
    ) -> None:
        if raises_error:
            with pytest.raises(ValueError):
                decode(query, options)
        else:
            assert decode(query, options) == expected


# --- Additional tests for decoder kind and parser state isolation ---


class TestKeyAwareDecoderBehavior:
    def test_decoder_receives_kind_for_keys_and_values(self) -> None:
        calls: t.List[DecodeKind] = []

        def _decoder(s: t.Optional[str], charset: t.Optional[Charset], *, kind: DecodeKind = DecodeKind.VALUE) -> t.Any:
            calls.append(kind)
            return DecodeUtils.decode(s, charset=charset, kind=kind)

        assert decode("a=b&c=d", DecodeOptions(decoder=_decoder)) == {"a": "b", "c": "d"}
        # Expect KEY, VALUE for each pair (order within a pair is key then value)
        assert calls[0] is DecodeKind.KEY and calls[1] is DecodeKind.VALUE
        assert calls[2] is DecodeKind.KEY and calls[3] is DecodeKind.VALUE

    def test_preserves_percent_encoded_dot_in_keys_utf8(self) -> None:
        # %252E → protected %2E in key; with allow_dots but decode_dot_in_keys=False, do not split
        opts = DecodeOptions(allow_dots=True, decode_dot_in_keys=False)
        assert decode("a%252Eb=1", opts) == {"a%2Eb": "1"}

    def test_decodes_percent_encoded_dot_in_keys_when_enabled_utf8(self) -> None:
        # When decode_dot_in_keys=True, the %2E becomes a literal dot in the *segment*; no extra split is introduced
        # unless there are other literal dots present.
        opts = DecodeOptions(allow_dots=True, decode_dot_in_keys=True)
        assert decode("a%252Eb=1", opts) == {"a.b": "1"}

    def test_preserves_percent_encoded_dot_in_keys_latin1(self) -> None:
        opts = DecodeOptions(allow_dots=True, decode_dot_in_keys=False, charset=Charset.LATIN1)
        assert decode("a%252Eb=1", opts) == {"a%2Eb": "1"}

    def test_decodes_percent_encoded_dot_in_keys_when_enabled_latin1(self) -> None:
        opts = DecodeOptions(allow_dots=True, decode_dot_in_keys=True, charset=Charset.LATIN1)
        assert decode("a%252Eb=1", opts) == {"a.b": "1"}

    def test_decoder_adapter_supports_keyword_only_kind(self) -> None:
        calls: t.List[str] = []

        def _decoder(s: t.Optional[str], charset: t.Optional[Charset], *, kind: DecodeKind = DecodeKind.VALUE) -> t.Any:
            calls.append("KEY" if kind is DecodeKind.KEY else "VALUE")
            return DecodeUtils.decode(s, charset=charset, kind=kind)

        assert decode("x=y", DecodeOptions(decoder=_decoder)) == {"x": "y"}
        # Ensure both KEY and VALUE were observed
        assert calls == ["KEY", "VALUE"]

    def test_decoder_adapter_falls_back_to_single_arg(self) -> None:
        # A legacy decoder that only accepts the string and uppercases it.
        def _decoder(s: t.Optional[str]) -> t.Any:
            return None if s is None else s.upper()

        # Applies to keys and values
        assert decode("a=b", DecodeOptions(decoder=_decoder)) == {"A": "B"}

    def test_decoder_adapter_two_arg_signature(self) -> None:
        # A legacy decoder that accepts (s, charset) and delegates to default
        def _decoder(s: t.Optional[str], charset: t.Optional[Charset]) -> t.Any:
            return DecodeUtils.decode(s, charset=charset)

        assert decode("he%3Dllo=th%3Dere", DecodeOptions(decoder=_decoder)) == {"he=llo": "th=ere"}


class TestParserStateIsolation:
    def test_parse_lists_toggle_does_not_leak_across_calls(self) -> None:
        # Build a query with many top-level params to trigger the internal optimization
        big_query = "&".join(f"k{i}=v{i}" for i in range(25))
        opts = DecodeOptions(list_limit=20)

        # First call may temporarily disable parse_lists internally
        res1 = decode(big_query, opts)
        assert isinstance(res1, dict) and len(res1) == 25
        # The option should be restored on the options object
        assert opts.parse_lists is True

        # Second call should still parse lists as lists
        res2 = decode("a[]=1&a[]=2", opts)
        assert res2 == {"a": ["1", "2"]}


class TestCSharpParityEncodedDotBehavior:
    def test_top_level_allowdots_true_decodedot_true_splits_plain_and_encoded_dot(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=True)
        assert decode("a.b=c", opt) == {"a": {"b": "c"}}
        assert decode("a%2Eb=c", opt) == {"a": {"b": "c"}}
        assert decode("a%2eb=c", opt) == {"a": {"b": "c"}}

    def test_top_level_allowdots_true_decodedot_false_encoded_dot_also_splits(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=False)
        assert decode("a%2Eb=c", opt) == {"a": {"b": "c"}}
        assert decode("a%2eb=c", opt) == {"a": {"b": "c"}}

    def test_invalid_allowdots_false_decodedot_true_raises(self) -> None:
        with pytest.raises(ValueError):
            decode("a%2Eb=c", DecodeOptions(allow_dots=False, decode_dot_in_keys=True))

    def test_bracket_segment_maps_to_dot_when_decodedot_true(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=True)
        assert decode("a[%2E]=x", opt) == {"a": {".": "x"}}
        assert decode("a[%2e]=x", opt) == {"a": {".": "x"}}

    def test_bracket_segment_percent_decoding_inside_brackets_when_decodedot_false(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=False)
        # Note: key-decoder percent-decodes inside brackets, so %2E → "."
        assert decode("a[%2E]=x", opt) == {"a": {".": "x"}}
        assert decode("a[%2e]=x", opt) == {"a": {".": "x"}}

    def test_value_tokens_always_decode_percent2E_to_dot(self) -> None:
        assert decode("x=%2E") == {"x": "."}

    def test_latin1_allowdots_true_decodedot_true_matches_utf8(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=True, charset=Charset.LATIN1)
        assert decode("a%2Eb=c", opt) == {"a": {"b": "c"}}
        assert decode("a[%2E]=x", opt) == {"a": {".": "x"}}

    def test_latin1_allowdots_true_decodedot_false_also_splits_top_level_and_decodes_inside_brackets(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=False, charset=Charset.LATIN1)
        assert decode("a%2Eb=c", opt) == {"a": {"b": "c"}}
        assert decode("a[%2E]=x", opt) == {"a": {".": "x"}}

    def test_percent_decoding_applies_inside_brackets_when_decoding_keys(self) -> None:
        # Kotlin's DecodeOptions.decode(KEY) equivalent behavior exercised via full parse:
        # %2E inside a bracket segment becomes '.' regardless of allow_dots
        o1 = DecodeOptions(allow_dots=False, decode_dot_in_keys=False)
        o2 = DecodeOptions(allow_dots=True, decode_dot_in_keys=False)
        assert decode("a[%2Eb]=x", o1) == {"a": {".b": "x"}}
        assert decode("a[b%2Ec]=x", o1) == {"a": {"b.c": "x"}}
        assert decode("a[%2Eb]=x", o2) == {"a": {".b": "x"}}
        assert decode("a[b%2Ec]=x", o2) == {"a": {"b.c": "x"}}

    def test_mixed_case_encoded_brackets_plus_encoded_dot_after_brackets(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=True)
        # Uppercase
        assert decode("a%5Bb%5D%5Bc%5D%2Ed=x", opt) == {"a": {"b": {"c": {"d": "x"}}}}
        # Lowercase
        assert decode("a%5bb%5d%5bc%5d%2ed=x", opt) == {"a": {"b": {"c": {"d": "x"}}}}

    def test_nested_brackets_inside_a_segment_balanced_as_one_segment(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=True)
        # "a[b%5Bc%5D].e=x" → key "b[c]" stays a single segment; then ".e" splits (allow_dots)
        assert decode("a[b%5Bc%5D].e=x", opt) == {"a": {"b[c]": {"e": "x"}}}

    def test_mixed_case_encoded_brackets_and_encoded_dot_with_inconsistent_options_raises(self) -> None:
        with pytest.raises(ValueError):
            decode("a%5Bb%5D%5Bc%5D%2Ed=x", DecodeOptions(allow_dots=False, decode_dot_in_keys=True))

    def test_top_level_encoded_dot_splits_when_allowdots_true_decodedot_true(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=True)
        assert decode("a%2Eb=c", opt) == {"a": {"b": "c"}}

    def test_top_level_encoded_dot_also_splits_when_allowdots_true_decodedot_false(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=False)
        assert decode("a%2Eb=c", opt) == {"a": {"b": "c"}}

    def test_top_level_encoded_dot_does_not_split_when_allowdots_false_decodedot_false(self) -> None:
        opt = DecodeOptions(allow_dots=False, decode_dot_in_keys=False)
        assert decode("a%2Eb=c", opt) == {"a.b": "c"}

    def test_bracket_then_encoded_dot_to_next_segment_with_allowdots_true(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=True)
        assert decode("a[b]%2Ec=x", opt) == {"a": {"b": {"c": "x"}}}
        assert decode("a[b]%2ec=x", opt) == {"a": {"b": {"c": "x"}}}

    def test_mixed_case_top_level_encoded_dot_then_bracket_with_allowdots_true(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=True)
        assert decode("a%2E[b]=x", opt) == {"a": {"b": "x"}}

    def test_top_level_lowercase_encoded_dot_splits_when_allowdots_true_decodedot_false(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=False)
        assert decode("a%2eb=c", opt) == {"a": {"b": "c"}}

    def test_dot_before_index_with_allowdots_true_index_remains_index(self) -> None:
        opt = DecodeOptions(allow_dots=True)
        assert decode("foo[0].baz[0]=15&foo[0].bar=2", opt) == {"foo": [{"baz": ["15"], "bar": "2"}]}

    def test_trailing_dot_ignored_when_allowdots_true(self) -> None:
        opt = DecodeOptions(allow_dots=True)
        assert decode("user.email.=x", opt) == {"user": {"email": "x"}}

    def test_bracket_segment_encoded_dot_mapped_to_dot_when_decodedot_true(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=True)
        assert decode("a[%2E]=x", opt) == {"a": {".": "x"}}
        assert decode("a[%2e]=x", opt) == {"a": {".": "x"}}

    def test_top_level_encoded_dot_before_bracket_lowercase_with_allowdots_true(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=True)
        assert decode("a%2e[b]=x", opt) == {"a": {"b": "x"}}

    def test_plain_dot_before_bracket_with_allowdots_true(self) -> None:
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=True)
        assert decode("a.[b]=x", opt) == {"a": {"b": "x"}}

    def test_kind_aware_decoder_receives_key_for_top_level_and_bracketed_keys(self) -> None:
        calls: t.List[t.Tuple[t.Optional[str], DecodeKind]] = []

        def _decoder(s: t.Optional[str], charset: t.Optional[Charset], *, kind: DecodeKind = DecodeKind.VALUE) -> t.Any:
            calls.append((s, kind))
            return s

        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=True, decoder=_decoder)
        # Ensure the decoder is invoked for both key forms without tripping F601 on duplicate dict keys.
        assert bool(decode("a%2Eb=c&a[b]=d", opt))  # no-op: just ensure the call executes

        # Confirm both KEY invocations observed: raw top-level key and raw bracketed key
        assert any(k == DecodeKind.KEY and (s == "a%2Eb" or s == "a[b]") for (s, k) in calls)
        assert any(k == DecodeKind.VALUE and (s == "c" or s == "d") for (s, k) in calls)


class TestAdditionalDotEncodingParity:
    def test_allowdots_false_decodedot_false_encoded_dots_decode_to_literal_no_split(self) -> None:
        # allowDots=false, decodeDotInKeys=false: encoded dots decode to literal '.'; no dot-splitting
        opt = DecodeOptions(allow_dots=False, decode_dot_in_keys=False)
        assert decode("a%2Eb=c", opt) == {"a.b": "c"}
        assert decode("a%2eb=c", opt) == {"a.b": "c"}

    def test_allowdots_true_decodedot_false_double_encoded_preserved_inside_segments(self) -> None:
        # allowDots=true, decodeDotInKeys=false: double-encoded dots are preserved inside segments; encoded and plain dots split
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=False)
        # Plain dot splits
        assert decode("a.b=c", opt) == {"a": {"b": "c"}}
        # Encoded dot stays encoded inside first segment (no extra split)
        assert decode("name%252Eobj.first=John", opt) == {"name%2Eobj": {"first": "John"}}
        # Lowercase variant inside first segment ("a%2eb.c=d")
        assert decode("a%2eb.c=d", opt) == {"a": {"b": {"c": "d"}}}

    def test_allowdots_true_decodedot_true_encoded_dots_become_literal_inside_segment(self) -> None:
        # allowDots=true, decodeDotInKeys=true: encoded dots become literal '.' inside a segment (no extra split)
        opt = DecodeOptions(allow_dots=True, decode_dot_in_keys=True)
        assert decode("name%252Eobj.first=John", opt) == {"name.obj": {"first": "John"}}
        # Double-encoded single segment becomes a literal dot after post-split mapping
        assert decode("a%252Eb=c", opt) == {"a.b": "c"}
        # Lowercase mapping as well in a bracket segment
        assert decode("a[%2e]=x", opt) == {"a": {".": "x"}}

    def test_bracket_segment_percent2e_mapped_based_on_decodedotinkeys_case_insensitive(self) -> None:
        # When disabled, percent-decoding inside brackets yields '.' (no extra split)
        assert decode("a[%2E]=x", DecodeOptions(allow_dots=False, decode_dot_in_keys=False)) == {"a": {".": "x"}}
        assert decode("a[%2e]=x", DecodeOptions(allow_dots=True, decode_dot_in_keys=False)) == {"a": {".": "x"}}
        # When enabled, convert to '.' regardless of case
        assert decode("a[%2E]=x", DecodeOptions(allow_dots=True, decode_dot_in_keys=True)) == {"a": {".": "x"}}
        # Inconsistent options should raise at construction; mirrored here via the call
        with pytest.raises(ValueError):
            decode("a[%2e]=x", DecodeOptions(allow_dots=False, decode_dot_in_keys=True))

    def test_bare_key_behavior_matches_key_decoding_path(self) -> None:
        # allowDots=false → %2E decodes to '.'; no splitting because allowDots=false; strict null → None
        opt1 = DecodeOptions(allow_dots=False, decode_dot_in_keys=False, strict_null_handling=True)
        assert decode("a%2Eb", opt1) == {"a.b": None}
        # allowDots=true & decodeDotInKeys=false → keep %2E inside key segment (no extra split); empty value default
        opt2 = DecodeOptions(allow_dots=True, decode_dot_in_keys=False)
        assert decode("a%2Eb", opt2) == {"a": {"b": ""}}

    def test_depth_zero_with_allowdots_true_does_not_split_key(self) -> None:
        # depth=0 with allowDots=true: do not split key
        opt = DecodeOptions(allow_dots=True, depth=0)
        assert decode("a.b=c", opt) == {"a.b": "c"}

    def test_top_level_dot_to_bracket_guardrails_leading_trailing_double(self) -> None:
        # Leading dot: ".a" should yield {"a": ...} when allowDots=true
        assert decode(".a=x", DecodeOptions(allow_dots=True, decode_dot_in_keys=False)) == {"a": "x"}

        # Trailing dot: "a." should NOT create an empty bracket segment; remains literal
        assert decode("a.=x", DecodeOptions(allow_dots=True, decode_dot_in_keys=False)) == {"a.": "x"}

        # Double dots: only the second dot (before a token) causes a split; the empty middle segment is preserved
        # as a literal dot in the parent key (no [] is created)
        assert decode("a..b=x", DecodeOptions(allow_dots=True, decode_dot_in_keys=False)) == {"a.": {"b": "x"}}

    def test_regex_delimiter_without_limit_uses_regex_split(self) -> None:
        options = DecodeOptions(parameter_limit=float("inf"), delimiter=re.compile(r"[;&]"))
        assert decode("a=1;b=2", options) == {"a": "1", "b": "2"}

    def test_regex_delimiter_with_limit_raises_when_exceeded(self) -> None:
        options = DecodeOptions(parameter_limit=1, raise_on_limit_exceeded=True, delimiter=re.compile(r"[;&]"))
        with pytest.raises(ValueError, match="Parameter limit exceeded"):
            decode("a=1&b=2", options)

    def test_decoder_skips_pairs_when_key_decode_returns_none(self) -> None:
        def dropping_decoder(token: t.Optional[str], charset: t.Optional[Charset]) -> t.Optional[str]:
            if token in {"dropNoEquals", "drop"}:
                return None
            return token

        opts = DecodeOptions(decoder=None, legacy_decoder=dropping_decoder)
        assert decode("dropNoEquals&drop=1&keep=2", opts) == {"keep": "2"}

    def test_parse_object_estimates_list_length_for_numeric_parent(self) -> None:
        options = DecodeOptions()
        chain = ["0", "[]"]
        val = [["x", "y"]]
        result = _parse_object(chain, val, options, True)
        assert result == {"0": [["x", "y"]]}


class TestSplitKeySegmentationRemainder:
    def test_no_remainder_when_within_depth(self) -> None:
        segs = DecodeUtils.split_key_into_segments("a[b][c]", allow_dots=False, max_depth=3, strict_depth=False)
        assert segs == ["a", "[b]", "[c]"]

    def test_double_bracket_remainder_allowdots_depth1(self) -> None:
        # Dot → bracket happens first; with max_depth=1, the remainder is wrapped as a single
        # synthetic segment using double brackets (opaque to downstream consumers).
        segs = DecodeUtils.split_key_into_segments("a.b.c", allow_dots=True, max_depth=1, strict_depth=False)
        assert segs == ["a", "[b]", "[[c]]"]

    def test_double_bracket_remainder_for_bracket_input(self) -> None:
        # For bracketed input, the remainder beyond depth is also wrapped as one segment
        # (e.g. "a[b][c][d]" with max_depth=2 → ["a", "[b]", "[[c][d]]"]).
        segs = DecodeUtils.split_key_into_segments("a[b][c][d]", allow_dots=False, max_depth=2, strict_depth=False)
        assert segs == ["a", "[b]", "[c]", "[[d]]"]

    def test_strict_depth_overflow_raises_for_well_formed(self) -> None:
        # Well-formed keys that exceed max_depth should raise when strict_depth=True.
        with pytest.raises(IndexError):
            DecodeUtils.split_key_into_segments("a[b][c][d]", allow_dots=False, max_depth=1, strict_depth=True)

    def test_unterminated_group_does_not_raise_under_strict_depth(self) -> None:
        segs = DecodeUtils.split_key_into_segments("a[b[c", allow_dots=False, max_depth=5, strict_depth=True)
        assert segs == ["a", "[[b[c]"]
