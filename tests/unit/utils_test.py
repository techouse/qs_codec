import typing as t

import pytest

from qs_codec.enums.charset import Charset
from qs_codec.enums.format import Format
from qs_codec.models.undefined import Undefined
from qs_codec.utils.decode_utils import DecodeUtils
from qs_codec.utils.encode_utils import EncodeUtils
from qs_codec.utils.utils import Utils


class TestUtils:
    def test_hex_table(self) -> None:
        assert EncodeUtils.HEX_TABLE == (
            "%00",
            "%01",
            "%02",
            "%03",
            "%04",
            "%05",
            "%06",
            "%07",
            "%08",
            "%09",
            "%0A",
            "%0B",
            "%0C",
            "%0D",
            "%0E",
            "%0F",
            "%10",
            "%11",
            "%12",
            "%13",
            "%14",
            "%15",
            "%16",
            "%17",
            "%18",
            "%19",
            "%1A",
            "%1B",
            "%1C",
            "%1D",
            "%1E",
            "%1F",
            "%20",
            "%21",
            "%22",
            "%23",
            "%24",
            "%25",
            "%26",
            "%27",
            "%28",
            "%29",
            "%2A",
            "%2B",
            "%2C",
            "%2D",
            "%2E",
            "%2F",
            "%30",
            "%31",
            "%32",
            "%33",
            "%34",
            "%35",
            "%36",
            "%37",
            "%38",
            "%39",
            "%3A",
            "%3B",
            "%3C",
            "%3D",
            "%3E",
            "%3F",
            "%40",
            "%41",
            "%42",
            "%43",
            "%44",
            "%45",
            "%46",
            "%47",
            "%48",
            "%49",
            "%4A",
            "%4B",
            "%4C",
            "%4D",
            "%4E",
            "%4F",
            "%50",
            "%51",
            "%52",
            "%53",
            "%54",
            "%55",
            "%56",
            "%57",
            "%58",
            "%59",
            "%5A",
            "%5B",
            "%5C",
            "%5D",
            "%5E",
            "%5F",
            "%60",
            "%61",
            "%62",
            "%63",
            "%64",
            "%65",
            "%66",
            "%67",
            "%68",
            "%69",
            "%6A",
            "%6B",
            "%6C",
            "%6D",
            "%6E",
            "%6F",
            "%70",
            "%71",
            "%72",
            "%73",
            "%74",
            "%75",
            "%76",
            "%77",
            "%78",
            "%79",
            "%7A",
            "%7B",
            "%7C",
            "%7D",
            "%7E",
            "%7F",
            "%80",
            "%81",
            "%82",
            "%83",
            "%84",
            "%85",
            "%86",
            "%87",
            "%88",
            "%89",
            "%8A",
            "%8B",
            "%8C",
            "%8D",
            "%8E",
            "%8F",
            "%90",
            "%91",
            "%92",
            "%93",
            "%94",
            "%95",
            "%96",
            "%97",
            "%98",
            "%99",
            "%9A",
            "%9B",
            "%9C",
            "%9D",
            "%9E",
            "%9F",
            "%A0",
            "%A1",
            "%A2",
            "%A3",
            "%A4",
            "%A5",
            "%A6",
            "%A7",
            "%A8",
            "%A9",
            "%AA",
            "%AB",
            "%AC",
            "%AD",
            "%AE",
            "%AF",
            "%B0",
            "%B1",
            "%B2",
            "%B3",
            "%B4",
            "%B5",
            "%B6",
            "%B7",
            "%B8",
            "%B9",
            "%BA",
            "%BB",
            "%BC",
            "%BD",
            "%BE",
            "%BF",
            "%C0",
            "%C1",
            "%C2",
            "%C3",
            "%C4",
            "%C5",
            "%C6",
            "%C7",
            "%C8",
            "%C9",
            "%CA",
            "%CB",
            "%CC",
            "%CD",
            "%CE",
            "%CF",
            "%D0",
            "%D1",
            "%D2",
            "%D3",
            "%D4",
            "%D5",
            "%D6",
            "%D7",
            "%D8",
            "%D9",
            "%DA",
            "%DB",
            "%DC",
            "%DD",
            "%DE",
            "%DF",
            "%E0",
            "%E1",
            "%E2",
            "%E3",
            "%E4",
            "%E5",
            "%E6",
            "%E7",
            "%E8",
            "%E9",
            "%EA",
            "%EB",
            "%EC",
            "%ED",
            "%EE",
            "%EF",
            "%F0",
            "%F1",
            "%F2",
            "%F3",
            "%F4",
            "%F5",
            "%F6",
            "%F7",
            "%F8",
            "%F9",
            "%FA",
            "%FB",
            "%FC",
            "%FD",
            "%FE",
            "%FF",
        )

    @pytest.mark.parametrize(
        "decoded, encoded, format",
        [
            ("foo+bar", "foo%2Bbar", None),
            ("foo-bar", "foo-bar", None),
            ("foo_bar", "foo_bar", None),
            ("foo~bar", "foo~bar", None),
            ("foo.bar", "foo.bar", None),
            ("foo bar", "foo%20bar", None),
            ("foo(bar)", "foo%28bar%29", None),
            ("foo(bar)", "foo(bar)", Format.RFC1738),
            ([1, 2], "", None),
            ({"a": "b"}, "", None),
            (("a", "b"), "", None),
            (1, "1", None),
            (1.0, "1.0", None),
            (True, "true", None),
        ],
    )
    def test_encode(self, decoded: t.Any, encoded: str, format: t.Optional[Format]) -> None:
        assert EncodeUtils.encode(decoded, format=format) == encoded

    @pytest.mark.parametrize(
        "encoded, decoded",
        [
            ("foo%2Bbar", "foo+bar"),
            ("foo-bar", "foo-bar"),
            ("foo_bar", "foo_bar"),
            ("foo~bar", "foo~bar"),
            ("foo.bar", "foo.bar"),
            ("foo%20bar", "foo bar"),
            ("foo%28bar%29", "foo(bar)"),
        ],
    )
    def test_decode(self, encoded: str, decoded: str) -> None:
        assert DecodeUtils.decode(encoded) == decoded

    @pytest.mark.parametrize(
        "decoded, encoded, format",
        [
            ("foo+bar", "foo%2Bbar", None),
            ("foo-bar", "foo-bar", None),
            ("foo_bar", "foo_bar", None),
            ("foo~bar", "foo~bar", None),
            ("foo.bar", "foo.bar", None),
            ("foo bar", "foo%20bar", None),
            ("foo(bar)", "foo%28bar%29", None),
            ("foo(bar)", "foo(bar)", Format.RFC1738),
            ([1, 2], "", None),
            ({"a": "b"}, "", None),
            (("a", "b"), "", None),
            (1, "1", None),
            (1.0, "1.0", None),
        ],
    )
    def test_encode_utf8(self, decoded: t.Any, encoded: str, format: t.Optional[Format]) -> None:
        assert EncodeUtils.encode(decoded, charset=Charset.UTF8, format=format) == encoded

    @pytest.mark.parametrize(
        "encoded, decoded",
        [
            ("foo%2Bbar", "foo+bar"),
            ("foo-bar", "foo-bar"),
            ("foo_bar", "foo_bar"),
            ("foo~bar", "foo~bar"),
            ("foo.bar", "foo.bar"),
            ("foo%20bar", "foo bar"),
            ("foo%28bar%29", "foo(bar)"),
        ],
    )
    def test_decode_utf8(self, encoded: str, decoded: str) -> None:
        assert DecodeUtils.decode(encoded, charset=Charset.UTF8) == decoded

    @pytest.mark.parametrize(
        "decoded, encoded, format",
        [
            ("foo+bar", "foo+bar", None),
            ("foo-bar", "foo-bar", None),
            ("foo_bar", "foo_bar", None),
            ("foo~bar", "foo%7Ebar", None),
            ("foo.bar", "foo.bar", None),
            ("foo bar", "foo%20bar", None),
            ("foo(bar)", "foo%28bar%29", None),
            ("foo(bar)", "foo(bar)", Format.RFC1738),
            ([1, 2], "", None),
            ({"a": "b"}, "", None),
            (("a", "b"), "", None),
            (1, "1", None),
            (1.0, "1.0", None),
        ],
    )
    def test_encode_latin1(self, decoded: t.Any, encoded: str, format: t.Optional[Format]) -> None:
        assert EncodeUtils.encode(decoded, charset=Charset.LATIN1, format=format) == encoded

    @pytest.mark.parametrize(
        "encoded, decoded",
        [
            ("foo+bar", "foo bar"),
            ("foo-bar", "foo-bar"),
            ("foo_bar", "foo_bar"),
            ("foo%7Ebar", "foo~bar"),
            ("foo.bar", "foo.bar"),
            ("foo%20bar", "foo bar"),
            ("foo%28bar%29", "foo(bar)"),
        ],
    )
    def test_decode_latin1(self, encoded: str, decoded: str) -> None:
        assert DecodeUtils.decode(encoded, charset=Charset.LATIN1) == decoded

    @pytest.mark.parametrize(
        "unescaped, escaped",
        [
            ("abc123", "abc123"),
            ("äöü", "%E4%F6%FC"),
            ("ć", "%u0107"),
            ("@*_+-./", "@*_+-./"),
            ("(", "%28"),
            (")", "%29"),
            (" ", "%20"),
            ("~", "%7E"),
            (
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@*_+-./",
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@*_+-./",
            ),
        ],
    )
    def test_escape(self, unescaped: str, escaped: str) -> None:
        assert EncodeUtils.escape(unescaped) == escaped

    @pytest.mark.parametrize(
        "escaped, unescaped",
        [
            ("abc123", "abc123"),
            ("%E4%F6%FC", "äöü"),
            ("%u0107", "ć"),
            ("@*_+-./", "@*_+-./"),
            ("%28", "("),
            ("%29", ")"),
            ("%20", " "),
            ("%7E", "~"),
            (
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@*_+-./",
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@*_+-./",
            ),
        ],
    )
    def test_unescape(self, escaped: str, unescaped: str) -> None:
        assert DecodeUtils.unescape(escaped) == unescaped

    def test_merges_dict_with_list(self) -> None:
        assert Utils.merge({"0": "a"}, [Undefined(), "b"]) == {"0": "a", "1": "b"}

    def test_merges_two_dicts_with_the_same_key_and_different_values(self) -> None:
        assert Utils.merge({"foo": [{"a": "a", "b": "b"}, {"a": "aa"}]}, {"foo": [Undefined(), {"b": "bb"}]}) == {
            "foo": [{"a": "a", "b": "b"}, {"a": "aa", "b": "bb"}]
        }

    def test_merges_two_dicts_with_the_same_key_and_different_list_values(self) -> None:
        assert Utils.merge({"foo": [{"baz": ["15"]}]}, {"foo": [{"baz": [Undefined(), "16"]}]}) == {
            "foo": [{"baz": ["15", "16"]}]
        }

    def test_merges_two_dicts_with_the_same_key_and_different_values_into_a_list(self) -> None:
        assert Utils.merge({"foo": [{"a": "b"}]}, {"foo": [{"c": "d"}]}) == {"foo": [{"a": "b", "c": "d"}]}

    def test_merge_true_into_null(self) -> None:
        assert Utils.merge(None, True) == [None, True]

    def test_merge_null_into_array(self) -> None:
        assert Utils.merge(None, [42]) == [None, 42]

    def test_merges_two_dicts_with_same_key(self) -> None:
        assert Utils.merge({"a": "b"}, {"a": "c"}) == {"a": ["b", "c"]}

    def test_merges_standalone_and_object_into_array(self) -> None:
        assert Utils.merge({"foo": "bar"}, {"foo": {"first": "123"}}) == {"foo": ["bar", {"first": "123"}]}

    def test_merges_standalone_and_two_objects_into_array(self) -> None:
        assert Utils.merge({"foo": ["bar", {"first": "123"}]}, {"foo": {"second": "456"}}) == {
            "foo": {"0": "bar", "1": {"first": "123"}, "second": "456"}
        }

    def test_merges_object_sandwiched_by_two_standalones_into_array(self) -> None:
        assert Utils.merge({"foo": ["bar", {"first": "123", "second": "456"}]}, {"foo": "baz"}) == {
            "foo": ["bar", {"first": "123", "second": "456"}, "baz"]
        }

    def test_merges_two_arrays_into_an_array(self) -> None:
        assert Utils.merge({"foo": ["baz"]}, {"foo": ["bar", "xyzzy"]}) == {"foo": ["baz", "bar", "xyzzy"]}

    def test_merges_object_into_array(self) -> None:
        assert Utils.merge({"foo": ["bar"]}, {"foo": {"baz": "xyzzy"}}) == {"foo": {"0": "bar", "baz": "xyzzy"}}

    def test_merges_array_into_object(self) -> None:
        assert Utils.merge(
            {"foo": {"bar": "baz"}},
            {"foo": ["xyzzy"]},
        ) == {"foo": {"bar": "baz", "0": "xyzzy"}}

    def test_combine_both_arrays(self) -> None:
        a = [1]
        b = [2]
        combined = Utils.combine(a, b)

        assert a == [1]
        assert b == [2]
        assert a is not combined
        assert b is not combined
        assert combined == [1, 2]

    def test_combine_one_array_one_non_array(self) -> None:
        aN = 1
        a = [aN]
        bN = 2
        b = [bN]

        combined_an_b = Utils.combine(aN, b)
        assert b == [bN]
        assert aN is not combined_an_b
        assert a is not combined_an_b
        assert bN is not combined_an_b
        assert b is not combined_an_b
        assert combined_an_b == [1, 2]

        combined_a_bn = Utils.combine(a, bN)
        assert a == [aN]
        assert aN is not combined_a_bn
        assert a is not combined_a_bn
        assert bN is not combined_a_bn
        assert b is not combined_a_bn
        assert combined_a_bn == [1, 2]

    def test_combine_neither_is_an_array(self) -> None:
        a = 1
        b = 2
        combined = Utils.combine(a, b)

        assert a is not combined
        assert b is not combined
        assert combined == [1, 2]

    def test_remove_undefined_from_list(self) -> None:
        map_with_undefined: t.Dict[str, t.Any] = {
            "a": [
                "a",
                Undefined(),
                "b",
                Undefined(),
                "c",
            ],
        }

        Utils._remove_undefined_from_map(map_with_undefined)

        assert map_with_undefined == {
            "a": ["a", "b", "c"],
        }

    def test_remove_undefined_from_map(self) -> None:
        map_with_undefined: t.Dict[str, t.Any] = {
            "a": {
                "a": "a",
                "b": Undefined(),
                "c": "c",
            },
        }

        Utils._remove_undefined_from_map(map_with_undefined)

        assert map_with_undefined == {
            "a": {
                "a": "a",
                "c": "c",
            },
        }
