import re
import typing as t
from contextlib import nullcontext as does_not_raise
from datetime import datetime
from sys import getsizeof

import pytest

from qs_codec import Charset, DecodeOptions, Duplicates, decode
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
        self, encoded: str, decoded: t.Mapping, options: t.Optional[DecodeOptions]
    ) -> None:
        if options is not None:
            assert decode(encoded, options=options) == decoded
        else:
            assert decode(encoded) == decoded

    @pytest.mark.parametrize(
        "encoded, decoded",
        [
            ("a[]=b&a[]=c", {"a": ["b", "c"]}),
            ("a[0]=b&a[1]=c", {"a": ["b", "c"]}),
            ("a=b,c", {"a": "b,c"}),
            ("a=b&a=c", {"a": ["b", "c"]}),
        ],
    )
    def test_comma_false(self, encoded: str, decoded: t.Mapping) -> None:
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
    def test_comma_true(self, encoded: str, decoded: t.Mapping) -> None:
        assert decode(encoded, DecodeOptions(comma=True)) == decoded

    def test_allows_enabling_dot_notation(self) -> None:
        assert decode("a.b=c") == {"a.b": "c"}
        assert decode("a.b=c", DecodeOptions(allow_dots=True)) == {"a": {"b": "c"}}

    def test_decode_dot_keys_correctly(self) -> None:
        assert decode(
            "name%252Eobj.first=John&name%252Eobj.last=Doe", DecodeOptions(allow_dots=False, decode_dot_in_keys=False)
        ) == {"name%2Eobj.first": "John", "name%2Eobj.last": "Doe"}
        assert decode(
            "name.obj.first=John&name.obj.last=Doe", DecodeOptions(allow_dots=True, decode_dot_in_keys=False)
        ) == {"name": {"obj": {"first": "John", "last": "Doe"}}}
        assert decode(
            "name%252Eobj.first=John&name%252Eobj.last=Doe", DecodeOptions(allow_dots=True, decode_dot_in_keys=False)
        ) == {"name%2Eobj": {"first": "John", "last": "Doe"}}
        assert decode(
            "name%252Eobj.first=John&name%252Eobj.last=Doe", DecodeOptions(allow_dots=True, decode_dot_in_keys=True)
        ) == {"name.obj": {"first": "John", "last": "Doe"}}

        assert decode(
            "name%252Eobj%252Esubobject.first%252Egodly%252Ename=John&name%252Eobj%252Esubobject.last=Doe",
            DecodeOptions(allow_dots=False, decode_dot_in_keys=False),
        ) == {
            "name%2Eobj%2Esubobject.first%2Egodly%2Ename": "John",
            "name%2Eobj%2Esubobject.last": "Doe",
        }
        assert decode(
            "name.obj.subobject.first.godly.name=John&name.obj.subobject.last=Doe",
            DecodeOptions(allow_dots=True, decode_dot_in_keys=False),
        ) == {
            "name": {
                "obj": {
                    "subobject": {
                        "first": {"godly": {"name": "John"}},
                        "last": "Doe",
                    }
                }
            }
        }
        assert decode(
            "name%252Eobj%252Esubobject.first%252Egodly%252Ename=John&name%252Eobj%252Esubobject.last=Doe",
            DecodeOptions(allow_dots=True, decode_dot_in_keys=True),
        ) == {"name.obj.subobject": {"first.godly.name": "John", "last": "Doe"}}
        assert decode("name%252Eobj.first=John&name%252Eobj.last=Doe") == {
            "name%2Eobj.first": "John",
            "name%2Eobj.last": "Doe",
        }
        assert decode("name%252Eobj.first=John&name%252Eobj.last=Doe", DecodeOptions(decode_dot_in_keys=False)) == {
            "name%2Eobj.first": "John",
            "name%2Eobj.last": "Doe",
        }
        assert decode("name%252Eobj.first=John&name%252Eobj.last=Doe", DecodeOptions(decode_dot_in_keys=True)) == {
            "name.obj": {"first": "John", "last": "Doe"}
        }

    def test_should_decode_dot_in_key_of_dict_and_allow_enabling_dot_notation_when_decode_dot_in_keys_is_set_to_true_and_allow_dots_is_undefined(
        self,
    ) -> None:
        assert decode(
            "name%252Eobj%252Esubobject.first%252Egodly%252Ename=John&name%252Eobj%252Esubobject.last=Doe",
            DecodeOptions(decode_dot_in_keys=True),
        ) == {"name.obj.subobject": {"first.godly.name": "John", "last": "Doe"}}

    def test_allows_empty_lists_in_obj_values(self) -> None:
        assert decode("foo[]&bar=baz", DecodeOptions(allow_empty_lists=True)) == {"foo": [], "bar": "baz"}
        assert decode("foo[]&bar=baz", DecodeOptions(allow_empty_lists=False)) == {"foo": [""], "bar": "baz"}

    def test_parses_a_single_nested_string(self) -> None:
        assert decode("a[b]=c") == {"a": {"b": "c"}}

    def test_parses_a_double_nested_string(self) -> None:
        assert decode("a[b][c]=d") == {"a": {"b": {"c": "d"}}}

    def test_defaults_to_a_depth_of_5(self) -> None:
        assert decode("a[b][c][d][e][f][g][h]=i") == {"a": {"b": {"c": {"d": {"e": {"f": {"[g][h]": "i"}}}}}}}

    def test_only_parses_one_level_when_depth_is_1(self) -> None:
        assert decode("a[b][c]=d", DecodeOptions(depth=1)) == {"a": {"b": {"[c]": "d"}}}
        assert decode("a[b][c][d]=e", DecodeOptions(depth=1)) == {"a": {"b": {"[c][d]": "e"}}}

    def test_uses_original_key_when_depth_is_0(self) -> None:
        assert decode("a[0]=b&a[1]=c", DecodeOptions(depth=0)) == {"a[0]": "b", "a[1]": "c"}
        assert decode("a[0][0]=b&a[0][1]=c&a[1]=d&e=2", DecodeOptions(depth=0)) == {
            "a[0][0]": "b",
            "a[0][1]": "c",
            "a[1]": "d",
            "e": "2",
        }

    def test_parses_a_simple_list(self) -> None:
        assert decode("a=b&a=c") == {"a": ["b", "c"]}

    def test_parses_an_explicit_list(self) -> None:
        assert decode("a[]=b") == {"a": ["b"]}
        assert decode("a[]=b&a[]=c") == {"a": ["b", "c"]}
        assert decode("a[]=b&a[]=c&a[]=d") == {"a": ["b", "c", "d"]}

    def test_parses_a_mix_of_simple_and_explicit_lists(self) -> None:
        assert decode("a=b&a[]=c") == {"a": ["b", "c"]}
        assert decode("a[]=b&a=c") == {"a": ["b", "c"]}
        assert decode("a[0]=b&a=c") == {"a": ["b", "c"]}
        assert decode("a=b&a[0]=c") == {"a": ["b", "c"]}

        assert decode("a[1]=b&a=c", DecodeOptions(list_limit=20)) == {"a": ["b", "c"]}
        assert decode("a[]=b&a=c", DecodeOptions(list_limit=0)) == {"a": ["b", "c"]}
        assert decode("a[]=b&a=c") == {"a": ["b", "c"]}

        assert decode("a=b&a[1]=c", DecodeOptions(list_limit=20)) == {"a": ["b", "c"]}
        assert decode("a=b&a[]=c", DecodeOptions(list_limit=0)) == {"a": ["b", "c"]}
        assert decode("a=b&a[]=c") == {"a": ["b", "c"]}

    def test_parses_a_nested_list(self) -> None:
        assert decode("a[b][]=c&a[b][]=d") == {"a": {"b": ["c", "d"]}}
        assert decode("a[>=]=25") == {"a": {">=": "25"}}

    def test_allows_to_specify_list_indices(self) -> None:
        assert decode("a[1]=c&a[0]=b&a[2]=d") == {"a": ["b", "c", "d"]}
        assert decode("a[1]=c&a[0]=b") == {"a": ["b", "c"]}
        assert decode("a[1]=c", DecodeOptions(list_limit=20)) == {"a": ["c"]}
        assert decode("a[1]=c", DecodeOptions(list_limit=0)) == {"a": {"1": "c"}}
        assert decode("a[1]=c") == {"a": ["c"]}

    def test_limits_specific_list_indices_to_list_limit(self) -> None:
        assert decode("a[20]=a", DecodeOptions(list_limit=20)) == {"a": ["a"]}
        assert decode("a[21]=a", DecodeOptions(list_limit=20)) == {"a": {"21": "a"}}
        assert decode("a[20]=a") == {"a": ["a"]}
        assert decode("a[21]=a") == {"a": {"21": "a"}}

    def test_supports_keys_that_begin_with_a_number(self) -> None:
        assert decode("a[12b]=c") == {"a": {"12b": "c"}}

    def test_supports_encoded_equals_signs(self) -> None:
        assert decode("he%3Dllo=th%3Dere") == {"he=llo": "th=ere"}

    def test_is_ok_with_url_encoded_strings(self) -> None:
        assert decode("a[b%20c]=d") == {"a": {"b c": "d"}}
        assert decode("a[b]=c%20d") == {"a": {"b": "c d"}}

    def test_allows_brackets_in_the_value(self) -> None:
        assert decode('pets=["tobi"]') == {"pets": '["tobi"]'}
        assert decode('operators=[">=", "<="]') == {"operators": '[">=", "<="]'}

    def test_allows_empty_values(self) -> None:
        assert decode("") == {}
        assert decode(None) == {}

    def test_transforms_lists_to_dicts(self) -> None:
        assert decode("foo[0]=bar&foo[bad]=baz") == {"foo": {"0": "bar", "bad": "baz"}}
        assert decode("foo[bad]=baz&foo[0]=bar") == {"foo": {"bad": "baz", "0": "bar"}}
        assert decode("foo[bad]=baz&foo[]=bar") == {"foo": {"bad": "baz", "0": "bar"}}
        assert decode("foo[]=bar&foo[bad]=baz") == {"foo": {"0": "bar", "bad": "baz"}}
        assert decode("foo[bad]=baz&foo[]=bar&foo[]=foo") == {"foo": {"bad": "baz", "0": "bar", "1": "foo"}}
        assert decode("foo[0][a]=a&foo[0][b]=b&foo[1][a]=aa&foo[1][b]=bb") == {
            "foo": [{"a": "a", "b": "b"}, {"a": "aa", "b": "bb"}]
        }

    def test_transforms_lists_to_dicts_dot_notation(self) -> None:
        assert decode("foo[0].baz=bar&fool.bad=baz", DecodeOptions(allow_dots=True)) == {
            "foo": [{"baz": "bar"}],
            "fool": {"bad": "baz"},
        }
        assert decode("foo[0].baz=bar&fool.bad.boo=baz", DecodeOptions(allow_dots=True)) == {
            "foo": [{"baz": "bar"}],
            "fool": {"bad": {"boo": "baz"}},
        }
        assert decode("foo[0][0].baz=bar&fool.bad=baz", DecodeOptions(allow_dots=True)) == {
            "foo": [[{"baz": "bar"}]],
            "fool": {"bad": "baz"},
        }
        assert decode("foo[0].baz[0]=15&foo[0].bar=2", DecodeOptions(allow_dots=True)) == {
            "foo": [{"baz": ["15"], "bar": "2"}]
        }
        assert decode("foo[0].baz[0]=15&foo[0].baz[1]=16&foo[0].bar=2", DecodeOptions(allow_dots=True)) == {
            "foo": [{"baz": ["15", "16"], "bar": "2"}]
        }
        assert decode("foo.bad=baz&foo[0]=bar", DecodeOptions(allow_dots=True)) == {"foo": {"bad": "baz", "0": "bar"}}
        assert decode("foo.bad=baz&foo[]=bar", DecodeOptions(allow_dots=True)) == {"foo": {"bad": "baz", "0": "bar"}}
        assert decode("foo[]=bar&foo.bad=baz", DecodeOptions(allow_dots=True)) == {"foo": {"0": "bar", "bad": "baz"}}
        assert decode("foo.bad=baz&foo[]=bar&foo[]=foo", DecodeOptions(allow_dots=True)) == {
            "foo": {"bad": "baz", "0": "bar", "1": "foo"}
        }
        assert decode("foo[0].a=a&foo[0].b=b&foo[1].a=aa&foo[1].b=bb", DecodeOptions(allow_dots=True)) == {
            "foo": [{"a": "a", "b": "b"}, {"a": "aa", "b": "bb"}]
        }

    def test_correctly_prunes_undefined_values_when_converting_a_list_to_a_dict(self) -> None:
        assert decode("a[2]=b&a[99999999]=c") == {"a": {"2": "b", "99999999": "c"}}

    def test_supports_malformed_uri_characters(self) -> None:
        assert decode("{%:%}", DecodeOptions(strict_null_handling=True)) == {"{%:%}": None}
        assert decode("{%:%}=") == {"{%:%}": ""}
        assert decode("foo=%:%}") == {"foo": "%:%}"}

    def test_does_not_produce_empty_keys(self) -> None:
        assert decode("_r=1&") == {"_r": "1"}

    def test_parses_lists_of_dicts(self) -> None:
        assert decode("a[][b]=c") == {"a": [{"b": "c"}]}
        assert decode("a[0][b]=c") == {"a": [{"b": "c"}]}

    def test_allows_for_empty_strings_in_lists(self) -> None:
        assert decode("a[]=b&a[]=&a[]=c") == {"a": ["b", "", "c"]}
        assert decode("a[0]=b&a[1]&a[2]=c&a[19]=", DecodeOptions(strict_null_handling=True, list_limit=20)) == {
            "a": ["b", None, "c", ""]
        }
        assert decode("a[]=b&a[]&a[]=c&a[]=", DecodeOptions(strict_null_handling=True, list_limit=0)) == {
            "a": ["b", None, "c", ""]
        }
        assert decode("a[0]=b&a[1]=&a[2]=c&a[19]", DecodeOptions(strict_null_handling=True, list_limit=20)) == {
            "a": ["b", "", "c", None]
        }
        assert decode("a[]=b&a[]=&a[]=c&a[]", DecodeOptions(strict_null_handling=True, list_limit=0)) == {
            "a": ["b", "", "c", None]
        }
        assert decode("a[]=&a[]=b&a[]=c") == {"a": ["", "b", "c"]}

    def test_compacts_sparse_lists(self) -> None:
        assert decode("a[10]=1&a[2]=2", DecodeOptions(list_limit=20)) == {"a": ["2", "1"]}
        assert decode("a[1][b][2][c]=1", DecodeOptions(list_limit=20)) == {"a": [{"b": [{"c": "1"}]}]}
        assert decode("a[1][2][3][c]=1", DecodeOptions(list_limit=20)) == {"a": [[[{"c": "1"}]]]}
        assert decode("a[1][2][3][c][1]=1", DecodeOptions(list_limit=20)) == {"a": [[[{"c": ["1"]}]]]}

    def test_parses_semi_parsed_strings(self) -> None:
        assert decode("a[b]=c") == {"a": {"b": "c"}}
        assert decode("a[b]=c&a[d]=e") == {"a": {"b": "c", "d": "e"}}

    def test_parses_buffers_correctly(self) -> None:
        b: bytes = b"test"
        assert decode({"a": b}) == {"a": b}

    def test_parses_jquery_param_strings(self) -> None:
        assert decode(
            # readable: str = 'filter[0][]=int1&filter[0][]==&filter[0][]=77&filter[]=and&filter[2][]=int2&filter[2][]==&filter[2][]=8'
            "filter%5B0%5D%5B%5D=int1&filter%5B0%5D%5B%5D=%3D&filter%5B0%5D%5B%5D=77&filter%5B%5D=and&filter%5B2%5D%5B%5D=int2&filter%5B2%5D%5B%5D=%3D&filter%5B2%5D%5B%5D=8"
        ) == {"filter": [["int1", "=", "77"], "and", ["int2", "=", "8"]]}

    def test_continues_parsing_when_no_parent_is_found(self) -> None:
        assert decode("[]=&a=b") == {"0": "", "a": "b"}
        assert decode("[]&a=b", DecodeOptions(strict_null_handling=True)) == {"0": None, "a": "b"}
        assert decode("[foo]=bar") == {"foo": "bar"}

    def test_does_not_error_when_parsing_a_very_long_list(self) -> None:
        buf: str = "a[]=a"
        while getsizeof(buf) < 128 * 1024:
            buf += "&"
            buf += buf

        with does_not_raise():
            assert decode(buf) is not None

    def test_parses_a_string_with_an_alternative_string_delimiter(self) -> None:
        assert decode("a=b;c=d", DecodeOptions(delimiter=";")) == {"a": "b", "c": "d"}

    def test_parses_a_string_with_an_alternative_regexp_delimiter(self) -> None:
        assert decode("a=b; c=d", DecodeOptions(delimiter=re.compile(r"[;,] *"))) == {"a": "b", "c": "d"}

    def test_allows_overriding_parameter_limit(self) -> None:
        assert decode("a=b&c=d", DecodeOptions(parameter_limit=1)) == {"a": "b"}

    def test_allows_setting_the_parameter_limit_to_infinity(self) -> None:
        assert decode("a=b&c=d", DecodeOptions(parameter_limit=float("inf"))) == {"a": "b", "c": "d"}

    def test_allows_overriding_list_limit(self) -> None:
        assert decode("a[0]=b", DecodeOptions(list_limit=-1)) == {"a": {"0": "b"}}
        assert decode("a[0]=b", DecodeOptions(list_limit=0)) == {"a": ["b"]}
        assert decode("a[-1]=b", DecodeOptions(list_limit=-1)) == {"a": {"-1": "b"}}
        assert decode("a[-1]=b", DecodeOptions(list_limit=0)) == {"a": {"-1": "b"}}
        assert decode("a[0]=b&a[1]=c", DecodeOptions(list_limit=-1)) == {"a": {"0": "b", "1": "c"}}
        assert decode("a[0]=b&a[1]=c", DecodeOptions(list_limit=0)) == {"a": {"0": "b", "1": "c"}}

    def test_allows_disabling_list_parsing(self) -> None:
        assert decode("a[0]=b&a[1]=c", DecodeOptions(parse_lists=False)) == {"a": {"0": "b", "1": "c"}}
        assert decode("a[]=b", DecodeOptions(parse_lists=False)) == {"a": {"0": "b"}}

    def test_allows_for_query_string_prefix(self) -> None:
        assert decode("?foo=bar", DecodeOptions(ignore_query_prefix=True)) == {"foo": "bar"}
        assert decode("foo=bar", DecodeOptions(ignore_query_prefix=True)) == {"foo": "bar"}
        assert decode("?foo=bar", DecodeOptions(ignore_query_prefix=False)) == {"?foo": "bar"}

    def test_parses_a_dict(self) -> None:
        assert decode({"user[name]": {"pop[bob]": 3}, "user[email]": None}) == {
            "user": {"name": {"pop[bob]": 3}, "email": None}
        }

    def test_parses_string_with_comma_as_list_divider(self) -> None:
        assert decode("foo=bar,tee", DecodeOptions(comma=True)) == {"foo": ["bar", "tee"]}
        assert decode("foo[bar]=coffee,tee", DecodeOptions(comma=True)) == {"foo": {"bar": ["coffee", "tee"]}}
        assert decode("foo=", DecodeOptions(comma=True)) == {"foo": ""}
        assert decode("foo", DecodeOptions(comma=True)) == {"foo": ""}
        assert decode("foo", DecodeOptions(comma=True, strict_null_handling=True)) == {"foo": None}
        assert decode("a[0]=c") == {"a": ["c"]}
        assert decode("a[]=c") == {"a": ["c"]}
        assert decode("a[]=c", DecodeOptions(comma=True)) == {"a": ["c"]}
        assert decode("a[0]=c&a[1]=d") == {"a": ["c", "d"]}
        assert decode("a[]=c&a[]=d") == {"a": ["c", "d"]}
        assert decode("a=c,d", DecodeOptions(comma=True)) == {"a": ["c", "d"]}

    def test_parses_values_with_comma_as_list_divider(self) -> None:
        assert decode({"foo": "bar,tee"}, DecodeOptions(comma=False)) == {"foo": "bar,tee"}
        assert decode({"foo": "bar,tee"}, DecodeOptions(comma=True)) == {"foo": ["bar", "tee"]}

    def test_use_number_decoder_parses_string_that_has_one_number_with_comma_option_enabled(self) -> None:
        def _decoder(s: t.Optional[str], charset: t.Optional[Charset]) -> t.Any:
            if s is not None:
                try:
                    return float(s)
                except ValueError:
                    pass
            return DecodeUtils.decode(s, charset=charset)

        assert decode("foo=1", DecodeOptions(comma=True, decoder=_decoder)) == {"foo": 1.0}
        assert decode("foo=0", DecodeOptions(comma=True, decoder=_decoder)) == {"foo": 0.0}

    def test_parses_brackets_holds_list_of_lists_when_having_two_parts_of_strings_with_comma_as_list_divider(
        self,
    ) -> None:
        assert decode("foo[]=1,2,3&foo[]=4,5,6", DecodeOptions(comma=True)) == {
            "foo": [["1", "2", "3"], ["4", "5", "6"]]
        }
        assert decode("foo[]=1,2,3&foo[]=", DecodeOptions(comma=True)) == {"foo": [["1", "2", "3"], ""]}
        assert decode("foo[]=1,2,3&foo[]=", DecodeOptions(comma=True)) == {"foo": [["1", "2", "3"], ""]}
        assert decode("foo[]=1,2,3&foo[]=", DecodeOptions(comma=True)) == {"foo": [["1", "2", "3"], ""]}
        assert decode("foo[]=1,2,3&foo[]=a", DecodeOptions(comma=True)) == {"foo": [["1", "2", "3"], "a"]}

    def test_parses_comma_delimited_list_while_having_percent_encoded_comma_treated_as_normal_text(self) -> None:
        assert decode("foo=a%2Cb", DecodeOptions(comma=True)) == {"foo": "a,b"}
        assert decode("foo=a%2C%20b,d", DecodeOptions(comma=True)) == {"foo": ["a, b", "d"]}
        assert decode("foo=a%2C%20b,c%2C%20d", DecodeOptions(comma=True)) == {"foo": ["a, b", "c, d"]}

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

        parsed: t.Optional[t.Mapping]

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

        parsed: t.Optional[t.Mapping]

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

    def test_params_starting_with_a_closing_bracket(self) -> None:
        assert decode("]=toString") == {"]": "toString"}
        assert decode("]]=toString") == {"]]": "toString"}
        assert decode("]hello]=toString") == {"]hello]": "toString"}

    def test_params_starting_with_a_starting_bracket(self) -> None:
        assert decode("[=toString") == {"[": "toString"}
        assert decode("[[=toString") == {"[[": "toString"}
        assert decode("[hello[=toString") == {"[hello[": "toString"}

    def test_add_keys_to_dicts(self) -> None:
        assert decode("a[b]=c") == {"a": {"b": "c"}}

    def test_can_return_null_dicts(self) -> None:
        expected: t.Dict[str, t.Any] = {}
        expected["a"] = {}
        expected["a"]["b"] = "c"
        expected["a"]["hasOwnProperty"] = "d"
        assert decode("a[b]=c&a[hasOwnProperty]=d") == expected

        assert decode(None) == {}

        expected_list: t.Dict[str, t.Any] = {}
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
    def test_parses_empty_keys(self, encoded: str, decoded: t.Mapping) -> None:
        assert decode(encoded) == decoded


class TestCharset:
    url_encoded_checkmark_in_utf_8: str = "%E2%9C%93"
    url_encoded_oslash_in_utf_8: str = "%C3%B8"
    url_encoded_num_checkmark: str = "%26%2310003%3B"
    url_encoded_num_smiley: str = "%26%239786%3B"

    def test_prefers_an_utf_8_charset_specified_by_the_utf8_sentinel_to_a_default_charset_of_iso_8859_1(self) -> None:
        assert decode(
            f"utf8={self.url_encoded_checkmark_in_utf_8}&{self.url_encoded_oslash_in_utf_8}={self.url_encoded_oslash_in_utf_8}",
            DecodeOptions(charset_sentinel=True, charset=Charset.LATIN1),
        ) == {"ø": "ø"}

    def test_prefers_an_iso_8859_1_charset_specified_by_the_utf8_sentinel_to_a_default_charset_of_utf_8(self) -> None:
        assert decode(
            f"utf8={self.url_encoded_num_checkmark}&{self.url_encoded_oslash_in_utf_8}={self.url_encoded_oslash_in_utf_8}",
            DecodeOptions(charset_sentinel=True, charset=Charset.UTF8),
        ) == {"Ã¸": "Ã¸"}

    def test_does_not_require_the_utf8_sentinel_to_be_defined_before_the_parameters_whose_decoding_it_affects(
        self,
    ) -> None:
        assert decode(
            f"a={self.url_encoded_oslash_in_utf_8}&utf8={self.url_encoded_num_checkmark}",
            DecodeOptions(charset_sentinel=True, charset=Charset.UTF8),
        ) == {"a": "Ã¸"}

    def test_should_ignore_an_utf8_sentinel_with_an_unknown_value(self) -> None:
        assert decode(
            f"utf8=foo&{self.url_encoded_oslash_in_utf_8}={self.url_encoded_oslash_in_utf_8}",
            DecodeOptions(charset_sentinel=True, charset=Charset.UTF8),
        ) == {"ø": "ø"}

    def test_uses_the_utf8_sentinel_to_switch_to_utf_8_when_no_default_charset_is_given(self) -> None:
        assert decode(
            f"utf8={self.url_encoded_checkmark_in_utf_8}&{self.url_encoded_oslash_in_utf_8}={self.url_encoded_oslash_in_utf_8}",
            DecodeOptions(charset_sentinel=True),
        ) == {"ø": "ø"}

    def test_uses_the_utf8_sentinel_to_switch_to_iso_8859_1_when_no_default_charset_is_given(self) -> None:
        assert decode(
            f"utf8={self.url_encoded_num_checkmark}&{self.url_encoded_oslash_in_utf_8}={self.url_encoded_oslash_in_utf_8}",
            DecodeOptions(charset_sentinel=True),
        ) == {"Ã¸": "Ã¸"}

    def test_interprets_numeric_entities_in_utf_8_when_interpret_numeric_entities(self) -> None:
        assert decode(
            f"foo={self.url_encoded_num_smiley}",
            DecodeOptions(charset=Charset.LATIN1, interpret_numeric_entities=True),
        ) == {"foo": "☺"}

    def test_handles_a_custom_decoder_returning_null_in_the_iso_8859_1_charset_when_interpret_numeric_entities(
        self,
    ) -> None:
        assert decode(
            f"foo=&bar={self.url_encoded_num_smiley}",
            DecodeOptions(
                charset=Charset.LATIN1,
                decoder=lambda s, charset: (
                    DecodeUtils.decode(s, charset=charset) if s is not None and s != "" else None
                ),
                interpret_numeric_entities=True,
            ),
        ) == {"foo": None, "bar": "☺"}

    def test_does_not_interpret_numeric_entities_in_iso_8859_1_when_interpret_numeric_entities_is_false(self) -> None:
        assert decode(
            f"foo={self.url_encoded_num_smiley}",
            DecodeOptions(charset=Charset.LATIN1, interpret_numeric_entities=False),
        ) == {"foo": "&#9786;"}

    def test_does_not_interpret_numeric_entities_when_the_charset_is_utf_8_even_when_interpret_numeric_entities(
        self,
    ) -> None:
        assert decode(
            f"foo={self.url_encoded_num_smiley}",
            DecodeOptions(charset=Charset.UTF8, interpret_numeric_entities=True),
        ) == {"foo": "&#9786;"}

    def test_does_not_interpret_uXXXX_syntax_in_utf_8_mode(self) -> None:
        assert decode("%u263A=%u263A", DecodeOptions(charset=Charset.UTF8)) == {"%u263A": "%u263A"}


class TestDuplicatesOption:
    def test_default_combine(self) -> None:
        assert decode("foo=bar&foo=baz") == {"foo": ["bar", "baz"]}

    def test_combine(self) -> None:
        assert decode("foo=bar&foo=baz", DecodeOptions(duplicates=Duplicates.COMBINE)) == {"foo": ["bar", "baz"]}

    def test_first(self) -> None:
        assert decode("foo=bar&foo=baz", DecodeOptions(duplicates=Duplicates.FIRST)) == {"foo": "bar"}

    def test_last(self) -> None:
        assert decode("foo=bar&foo=baz", DecodeOptions(duplicates=Duplicates.LAST)) == {"foo": "baz"}
