import re
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
            ("", "", None),
            ("(abc)", "%28abc%29", None),
            ("\x28\x29", "%28%29", None),
            ("\x28\x29", "()", Format.RFC1738),
            ("Āက豈", "%C4%80%E1%80%80%EF%A4%80", None),
            ("💩", "%F0%9F%92%A9", None),
            ("abc 123 💩", "abc%20123%20%F0%9F%92%A9", None),
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
            ("a%2Bb", "a+b"),
            ("name%2Eobj", "name.obj"),
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
            ("💩", "%26%2355357%3B%26%2356489%3B", None),
            ("abc 123 💩", "abc%20123%20%26%2355357%3B%26%2356489%3B", None),
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
            ("name%2Eobj%2Efoo", "name.obj.foo"),
        ],
    )
    def test_decode_latin1(self, encoded: str, decoded: str) -> None:
        assert DecodeUtils.decode(encoded, charset=Charset.LATIN1) == decoded

    @pytest.mark.parametrize(
        "unescaped, escaped, format",
        [
            # Basic alphanumerics (remain unchanged)
            ("abc123", "abc123", None),
            # Accented characters (Latin-1 range uses %XX)
            ("äöü", "%E4%F6%FC", None),
            # Non-ASCII that falls outside Latin-1 uses %uXXXX
            ("ć", "%u0107", None),
            # Characters that are defined as safe
            ("@*_+-./", "@*_+-./", None),
            # Parentheses: in RFC3986 they are encoded
            ("(", "%28", None),
            (")", "%29", None),
            # Space character
            (" ", "%20", None),
            # Tilde is safe
            ("~", "%7E", None),
            # Punctuation that is not safe: exclamation and comma
            ("!", "%21", None),
            (",", "%2C", None),
            # Mixed safe and unsafe characters
            ("hello world!", "hello%20world%21", None),
            # Multiple spaces are each encoded
            ("a b c", "a%20b%20c", None),
            # A string with various punctuation
            ("Hello, World!", "Hello%2C%20World%21", None),
            # Null character should be encoded
            ("\x00", "%00", None),
            # Emoji (e.g. 😀 U+1F600)
            ("😀", "%uD83D%uDE00", None),
            # Test RFC1738 format: Parentheses are safe (left unchanged)
            ("(", "(", Format.RFC1738),
            (")", ")", Format.RFC1738),
            # Mixed test with RFC1738: other unsafe characters are still encoded
            ("(hello)!", "(hello)%21", Format.RFC1738),
        ],
    )
    def test_escape(self, unescaped: str, escaped: str, format: t.Optional[Format]) -> None:
        assert EncodeUtils.escape(unescaped, format=format) == escaped

    @pytest.mark.parametrize(
        "escaped, unescaped",
        [
            # No escapes.
            ("abc123", "abc123"),
            # Hex escapes with uppercase hex digits.
            ("%E4%F6%FC", "äöü"),
            # Hex escapes with lowercase hex digits.
            ("%e4%f6%fc", "äöü"),
            # Unicode escape.
            ("%u0107", "ć"),
            # Unicode escape with lowercase digits.
            ("%u0061", "a"),
            # Characters that do not need escaping.
            ("@*_+-./", "@*_+-./"),
            # Hex escapes for punctuation.
            ("%28", "("),
            ("%29", ")"),
            ("%20", " "),
            ("%7E", "~"),
            # A long string with only safe characters.
            (
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@*_+-./",
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@*_+-./",
            ),
            # A mix of Unicode and hex escapes.
            ("%u0041%20%42", "A B"),
            # A mix of literal text and hex escapes.
            ("hello%20world", "hello world"),
            # A literal percent sign that is not followed by a valid escape remains unchanged.
            ("100% sure", "100% sure"),
            # Mixed Unicode and hex escapes.
            ("%u0041%65", "Ae"),  # %u0041 -> "A", %65 -> "e"
            # Escaped percent signs that do not form a valid escape remain unchanged.
            ("50%% off", "50%% off"),
            # Consecutive escapes producing multiple spaces.
            ("%20%u0020", "  "),
            # An invalid escape sequence should remain unchanged.
            ("abc%g", "abc%g"),
        ],
    )
    def test_unescape(self, escaped: str, unescaped: str) -> None:
        assert DecodeUtils.unescape(escaped) == unescaped

    def test_unescape_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Test that the unescape replacer falls back correctly when neither named group is set.

        We override the UNESCAPE_PATTERN to include a fallback alternative that matches a lone '%'
        (i.e. a '%' not followed by 'u' or two hex digits). When unescape is called on a string
        containing such a '%', the fallback branch in the replacer should return the matched '%' unchanged.
        """

        # Build a new pattern that, in addition to the normal valid escapes, matches a lone '%'
        # using a fallback alternative.
        new_pattern: t.Pattern[str] = re.compile(
            r"%u(?P<unicode>[0-9A-Fa-f]{4})|%(?P<hex>[0-9A-Fa-f]{2})|%(?!u|[0-9A-Fa-f]{2})"
        )
        monkeypatch.setattr(DecodeUtils, "UNESCAPE_PATTERN", new_pattern)

        # The input string contains a lone '%' (followed by a space, so it doesn't form a valid escape).
        input_string: str = "100% sure"
        # We expect the '%' to be left as-is (via the fallback branch).
        expected_output: str = "100% sure"

        result: str = DecodeUtils.unescape(input_string)
        assert result == expected_output

        # Optionally, you can also check with a string where the fallback alternative is the only match.
        input_string2: str = "abc% def"
        expected_output2: str = "abc% def"
        assert DecodeUtils.unescape(input_string2) == expected_output2

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

    def test_merges_with_tuples(self) -> None:
        # Test for lines 59 and 63 in utils.py
        # Test merging when target is a tuple (should convert to list before extending)
        result1 = Utils.merge({"foo": ("a", "b")}, {"foo": ["c", "d"]})
        assert result1 == {"foo": ["a", "b", "c", "d"]}

        # Test merging when target is a tuple and source is not a list/tuple (should convert to list before appending)
        result2 = Utils.merge({"foo": ("a", "b")}, {"foo": "c"})
        assert result2 == {"foo": ["a", "b", "c"]}

    def test_merges_object_into_array(self) -> None:
        assert Utils.merge({"foo": ["bar"]}, {"foo": {"baz": "xyzzy"}}) == {"foo": {"0": "bar", "baz": "xyzzy"}}

    def test_merges_array_into_object(self) -> None:
        assert Utils.merge(
            {"foo": {"bar": "baz"}},
            {"foo": ["xyzzy"]},
        ) == {"foo": {"bar": "baz", "0": "xyzzy"}}

    def test_combine_both_arrays(self) -> None:
        a: t.List[int] = [1]
        b: t.List[int] = [2]
        combined: t.List[int] = Utils.combine(a, b)

        assert a == [1]
        assert b == [2]
        assert a is not combined
        assert b is not combined
        assert combined == [1, 2]

    def test_combine_one_array_one_non_array(self) -> None:
        a_n: int = 1
        a: t.List[int] = [a_n]
        b_n: int = 2
        b: t.List[int] = [b_n]

        combined_an_b: t.List[int] = Utils.combine(a_n, b)
        assert b == [b_n]
        assert a_n is not combined_an_b
        assert a is not combined_an_b
        assert b_n is not combined_an_b
        assert b is not combined_an_b
        assert combined_an_b == [1, 2]

        combined_a_bn = Utils.combine(a, b_n)
        assert a == [a_n]
        assert a_n is not combined_a_bn
        assert a is not combined_a_bn
        assert b_n is not combined_a_bn
        assert b is not combined_a_bn
        assert combined_a_bn == [1, 2]

    def test_combine_neither_is_an_array(self) -> None:
        a: int = 1
        b: int = 2
        combined: t.List[int] = Utils.combine(a, b)

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

    def test_remove_undefined_from_list_with_tuple(self) -> None:
        # Test for lines 148-149 in utils.py
        # Create a list with a tuple that contains an Undefined value
        test_list = ["a", ("b", Undefined(), "c"), "d"]

        # Remove undefined values
        Utils._remove_undefined_from_list(test_list)

        # The tuple should be converted to a list with Undefined removed
        assert test_list == ["a", ["b", "c"], "d"]

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

    def test_remove_undefined_from_map_with_tuple(self) -> None:
        # Test for lines 164-165 in utils.py
        # Create a map with a tuple value that contains an Undefined value
        test_map = {"a": "value", "b": ("item1", Undefined(), "item2")}

        # Remove undefined values
        Utils._remove_undefined_from_map(test_map)

        # The tuple should be converted to a list with Undefined removed
        assert test_map == {"a": "value", "b": ["item1", "item2"]}

    def test_dicts_are_equal_with_non_dicts(self) -> None:
        # Test for lines 189 and 192 in utils.py
        # Test comparing a dict with a non-dict (should return False)
        assert not Utils._dicts_are_equal({"a": 1}, "not a dict")

        # Test comparing two non-dicts that are equal
        assert Utils._dicts_are_equal("same", "same")

        # Test comparing two non-dicts that are not equal
        assert not Utils._dicts_are_equal("one", "two")

    def test_is_non_nullish_primitive_catch_all(self) -> None:
        # Test for line 226-228 in utils.py
        # Create a custom class that doesn't match any of the explicit type checks
        class CustomType:
            pass

        # This should trigger the check for isinstance(val, object) and not isinstance(val, (list, tuple, t.Mapping))
        # which returns True for custom objects
        assert Utils.is_non_nullish_primitive(CustomType())

    @pytest.mark.parametrize(
        "input_str, expected",
        [
            # Test with an empty string
            ("", ""),
            # Test with a string containing only BMP characters
            ("Hello, world!", "Hello, world!"),
            # Test with a single non-BMP character (💩, U+1F4A9)
            # Expected surrogate pair: "\ud83d\udca9"
            ("💩", "\ud83d\udca9"),
            # Test with a mix of BMP and non-BMP characters
            ("A💩B", "A\ud83d\udca9B"),
            # Test with two non-BMP characters in sequence (💩💩)
            ("💩💩", "\ud83d\udca9\ud83d\udca9"),
            # Test with another non-BMP character, e.g., Gothic letter 𐍈 (U+10348)
            # Correct expected surrogate pair: "\ud800\udf48"
            ("𐍈", "\ud800\udf48"),
        ],
    )
    def test_to_surrogates(self, input_str: str, expected: str) -> None:
        assert EncodeUtils._to_surrogates(input_str) == expected

    @pytest.mark.parametrize(
        "char, format, expected",
        [
            # Alphanumeric characters (always safe)
            ("a", Format.RFC3986, True),
            ("Z", Format.RFC3986, True),
            ("0", Format.RFC3986, True),
            # The safe punctuation in SAFE_CHARS: -, ., _, ~
            ("-", Format.RFC3986, True),
            (".", Format.RFC3986, True),
            ("_", Format.RFC3986, True),
            ("~", Format.RFC3986, True),
            # Parentheses are not in SAFE_CHARS but are in RFC1738_SAFE_CHARS.
            ("(", Format.RFC3986, False),
            (")", Format.RFC3986, False),
            ("(", Format.RFC1738, True),
            (")", Format.RFC1738, True),
            # Characters that are not safe in either case.
            ("@", Format.RFC3986, False),
            ("@", Format.RFC1738, False),
            ("*", Format.RFC3986, False),
            ("*", Format.RFC1738, False),
        ],
    )
    def test_is_safe_char(self, char: str, format: Format, expected: bool) -> None:
        assert EncodeUtils._is_safe_char(ord(char), format) is expected
