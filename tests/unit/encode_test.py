import math
import typing as t
from contextlib import nullcontext as does_not_raise
from datetime import datetime
from decimal import Decimal
from enum import Enum
from urllib.parse import quote

import pytest

from qs_codec import Charset, EncodeOptions, Format, ListFormat, encode
from qs_codec.models.undefined import Undefined
from qs_codec.utils.encode_utils import EncodeUtils


class TestEncode:
    @pytest.mark.parametrize(
        "decoded, encoded",
        [
            ({"a": "b"}, "a=b"),
            ({"a": 1}, "a=1"),
            ({"a": 1, "b": 2}, "a=1&b=2"),
            ({"a": "A_Z"}, "a=A_Z"),
            ({"a": "€"}, "a=%E2%82%AC"),
            ({"a": ""}, "a=%EE%80%80"),
            ({"a": "א"}, "a=%D7%90"),
            ({"a": "𐐷"}, "a=%F0%90%90%B7"),
        ],
    )
    def test_encodes_a_query_string_dict(self, decoded: t.Mapping, encoded: str) -> None:
        assert encode(decoded) == encoded

    @pytest.mark.parametrize(
        "decoded, encoded",
        [
            ([1234], "0=1234"),
            (["lorem", 1234, "ipsum"], "0=lorem&1=1234&2=ipsum"),
        ],
    )
    def test_encodes_a_list(self, decoded: t.Any, encoded: str) -> None:
        assert encode(decoded) == encoded

    def test_encodes_falsy_values(self) -> None:
        assert encode({}) == ""
        assert encode(None) == ""
        assert encode(None, options=EncodeOptions(strict_null_handling=True)) == ""
        assert encode(False) == ""
        assert encode(0) == ""

    def test_encodes_decimal(self) -> None:
        pi: Decimal = Decimal(math.pi)

        def encode_with_n(
            value: t.Any,
            charset: t.Optional[Charset] = None,
            format: t.Optional[Format] = None,
        ) -> str:
            result: str = EncodeUtils.encode(value)
            return f"{result}n" if isinstance(value, Decimal) else result

        assert encode(pi) == ""
        assert encode([pi]) == "0=3.141592653589793115997963468544185161590576171875"
        assert (
            encode([pi], options=EncodeOptions(encoder=encode_with_n))
            == "0=3.141592653589793115997963468544185161590576171875n"
        )
        assert encode({"a": pi}) == "a=3.141592653589793115997963468544185161590576171875"
        assert (
            encode({"a": pi}, options=EncodeOptions(encoder=encode_with_n))
            == "a=3.141592653589793115997963468544185161590576171875n"
        )
        assert (
            encode(
                {"a": [pi]},
                options=EncodeOptions(
                    encode_values_only=True,
                    list_format=ListFormat.BRACKETS,
                ),
            )
            == "a[]=3.141592653589793115997963468544185161590576171875"
        )
        assert (
            encode(
                {"a": [pi]},
                options=EncodeOptions(
                    encode_values_only=True,
                    list_format=ListFormat.BRACKETS,
                    encoder=encode_with_n,
                ),
            )
            == "a[]=3.141592653589793115997963468544185161590576171875n"
        )

    def test_encodes_dot_in_key_of_dict_when_encode_dot_in_keys_and_allow_dots_is_provided(self) -> None:
        assert (
            encode(
                {"name.obj": {"first": "John", "last": "Doe"}},
                options=EncodeOptions(allow_dots=False, encode_dot_in_keys=False),
            )
            == "name.obj%5Bfirst%5D=John&name.obj%5Blast%5D=Doe"
        )

        assert (
            encode(
                {"name.obj": {"first": "John", "last": "Doe"}},
                options=EncodeOptions(allow_dots=True, encode_dot_in_keys=False),
            )
            == "name.obj.first=John&name.obj.last=Doe"
        )

        assert (
            encode(
                {"name.obj": {"first": "John", "last": "Doe"}},
                options=EncodeOptions(allow_dots=False, encode_dot_in_keys=True),
            )
            == "name%252Eobj%5Bfirst%5D=John&name%252Eobj%5Blast%5D=Doe"
        )

        assert (
            encode(
                {"name.obj": {"first": "John", "last": "Doe"}},
                options=EncodeOptions(allow_dots=True, encode_dot_in_keys=True),
            )
            == "name%252Eobj.first=John&name%252Eobj.last=Doe"
        )

        assert (
            encode(
                {"name.obj.subobject": {"first.godly.name": "John", "last": "Doe"}},
                options=EncodeOptions(allow_dots=True, encode_dot_in_keys=False),
            )
            == "name.obj.subobject.first.godly.name=John&name.obj.subobject.last=Doe"
        )

        assert (
            encode(
                {"name.obj.subobject": {"first.godly.name": "John", "last": "Doe"}},
                options=EncodeOptions(allow_dots=False, encode_dot_in_keys=True),
            )
            == "name%252Eobj%252Esubobject%5Bfirst.godly.name%5D=John&name%252Eobj%252Esubobject%5Blast%5D=Doe"
        )

        assert (
            encode(
                {"name.obj.subobject": {"first.godly.name": "John", "last": "Doe"}},
                options=EncodeOptions(allow_dots=True, encode_dot_in_keys=True),
            )
            == "name%252Eobj%252Esubobject.first%252Egodly%252Ename=John&name%252Eobj%252Esubobject.last=Doe"
        )

    def test_encodes_dot_in_key_of_dict_and_automatically_set_allow_dots_to_true_when_encode_dot_in_keys_is_true_and_allow_dots_in_undefined(
        self,
    ):
        assert (
            encode(
                {"name.obj.subobject": {"first.godly.name": "John", "last": "Doe"}},
                options=EncodeOptions(encode_dot_in_keys=True),
            )
            == "name%252Eobj%252Esubobject.first%252Egodly%252Ename=John&name%252Eobj%252Esubobject.last=Doe"
        )

    def test_should_encode_dot_in_key_of_dict_when_encode_dot_in_keys_and_allow_dots_is_provided_and_nothing_else_when_encode_values_only_is_provided(
        self,
    ):
        assert (
            encode(
                {"name.obj": {"first": "John", "last": "Doe"}},
                options=EncodeOptions(
                    encode_dot_in_keys=True,
                    allow_dots=True,
                    encode_values_only=True,
                ),
            )
            == "name%2Eobj.first=John&name%2Eobj.last=Doe"
        )

        assert (
            encode(
                {"name.obj.subobject": {"first.godly.name": "John", "last": "Doe"}},
                options=EncodeOptions(
                    allow_dots=True,
                    encode_dot_in_keys=True,
                    encode_values_only=True,
                ),
            )
            == "name%2Eobj%2Esubobject.first%2Egodly%2Ename=John&name%2Eobj%2Esubobject.last=Doe"
        )

    def test_adds_query_prefix(self) -> None:
        assert encode({"a": "b"}, options=EncodeOptions(add_query_prefix=True)) == "?a=b"

    def test_with_query_prefix_outputs_blank_string_given_an_empty_dict(self) -> None:
        assert encode({}, options=EncodeOptions(add_query_prefix=True)) == ""

    def test_encodes_nested_falsy_values(self) -> None:
        assert encode({"a": {"b": {"c": None}}}) == "a%5Bb%5D%5Bc%5D="
        assert encode({"a": {"b": {"c": None}}}, options=EncodeOptions(strict_null_handling=True)) == "a%5Bb%5D%5Bc%5D"
        assert encode({"a": {"b": {"c": False}}}) == "a%5Bb%5D%5Bc%5D=false"

    def test_encodes_a_nested_dict(self) -> None:
        assert encode({"a": {"b": "c"}}) == "a%5Bb%5D=c"
        assert encode({"a": {"b": {"c": {"d": "e"}}}}) == "a%5Bb%5D%5Bc%5D%5Bd%5D=e"

    def test_encodes_a_nested_dict_with_dots_notation(self) -> None:
        assert encode({"a": {"b": "c"}}, options=EncodeOptions(allow_dots=True)) == "a.b=c"
        assert encode({"a": {"b": {"c": {"d": "e"}}}}, options=EncodeOptions(allow_dots=True)) == "a.b.c.d=e"

    def test_encodes_a_list_value(self) -> None:
        assert (
            encode({"a": ["b", "c", "d"]}, options=EncodeOptions(list_format=ListFormat.INDICES))
            == "a%5B0%5D=b&a%5B1%5D=c&a%5B2%5D=d"
        )
        assert (
            encode({"a": ["b", "c", "d"]}, options=EncodeOptions(list_format=ListFormat.BRACKETS))
            == "a%5B%5D=b&a%5B%5D=c&a%5B%5D=d"
        )
        assert encode({"a": ["b", "c", "d"]}, options=EncodeOptions(list_format=ListFormat.COMMA)) == "a=b%2Cc%2Cd"
        assert (
            encode({"a": ["b", "c", "d"]}, options=EncodeOptions(list_format=ListFormat.COMMA, comma_round_trip=True))
            == "a=b%2Cc%2Cd"
        )
        assert encode({"a": ["b", "c", "d"]}) == "a%5B0%5D=b&a%5B1%5D=c&a%5B2%5D=d"

    def test_omits_nulls_when_asked(self) -> None:
        assert encode({"a": "b", "c": None}, options=EncodeOptions(skip_nulls=True)) == "a=b"
        assert encode({"a": {"b": "c", "d": None}}, options=EncodeOptions(skip_nulls=True)) == "a%5Bb%5D=c"

    def test_omits_list_indices_when_asked(self) -> None:
        assert encode({"a": ["b", "c", "d"]}, options=EncodeOptions(indices=False)) == "a=b&a=c&a=d"

    def test_omits_map_key_value_pair_when_value_is_empty_list(self) -> None:
        assert encode({"a": [], "b": "zz"}) == "b=zz"

    def test_should_omit_map_key_value_pair_when_value_is_empty_list_and_when_asked(self) -> None:
        assert encode({"a": [], "b": "zz"}) == "b=zz"
        assert encode({"a": [], "b": "zz"}, options=EncodeOptions(allow_empty_lists=False)) == "b=zz"
        assert encode({"a": [], "b": "zz"}, options=EncodeOptions(allow_empty_lists=True)) == "a[]&b=zz"

    def test_encodes_a_nested_list_value(self) -> None:
        assert (
            encode(
                {"a": {"b": ["c", "d"]}}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES)
            )
            == "a[b][0]=c&a[b][1]=d"
        )
        assert (
            encode(
                {"a": {"b": ["c", "d"]}},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
            )
            == "a[b][]=c&a[b][]=d"
        )
        assert (
            encode(
                {"a": {"b": ["c", "d"]}}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.COMMA)
            )
            == "a[b]=c,d"
        )
        assert encode({"a": {"b": ["c", "d"]}}, options=EncodeOptions(encode_values_only=True)) == "a[b][0]=c&a[b][1]=d"

    def test_encodes_comma_and_empty_list_values(self) -> None:
        assert (
            encode({"a": [",", "", "c,d%"]}, options=EncodeOptions(encode=False, list_format=ListFormat.INDICES))
            == "a[0]=,&a[1]=&a[2]=c,d%"
        )
        assert (
            encode({"a": [",", "", "c,d%"]}, options=EncodeOptions(encode=False, list_format=ListFormat.BRACKETS))
            == "a[]=,&a[]=&a[]=c,d%"
        )
        assert (
            encode({"a": [",", "", "c,d%"]}, options=EncodeOptions(encode=False, list_format=ListFormat.COMMA))
            == "a=,,,c,d%"
        )
        assert (
            encode({"a": [",", "", "c,d%"]}, options=EncodeOptions(encode=False, list_format=ListFormat.REPEAT))
            == "a=,&a=&a=c,d%"
        )
        assert (
            encode(
                {"a": [",", "", "c,d%"]},
                options=EncodeOptions(encode=True, encode_values_only=True, list_format=ListFormat.BRACKETS),
            )
            == "a[]=%2C&a[]=&a[]=c%2Cd%25"
        )
        assert (
            encode(
                {"a": [",", "", "c,d%"]},
                options=EncodeOptions(encode=True, encode_values_only=True, list_format=ListFormat.COMMA),
            )
            == "a=%2C,,c%2Cd%25"
        )
        assert (
            encode(
                {"a": [",", "", "c,d%"]},
                options=EncodeOptions(encode=True, encode_values_only=True, list_format=ListFormat.REPEAT),
            )
            == "a=%2C&a=&a=c%2Cd%25"
        )
        assert (
            encode(
                {"a": [",", "", "c,d%"]},
                options=EncodeOptions(encode=True, encode_values_only=True, list_format=ListFormat.INDICES),
            )
            == "a[0]=%2C&a[1]=&a[2]=c%2Cd%25"
        )
        assert (
            encode(
                {"a": [",", "", "c,d%"]},
                options=EncodeOptions(encode=True, encode_values_only=False, list_format=ListFormat.BRACKETS),
            )
            == "a%5B%5D=%2C&a%5B%5D=&a%5B%5D=c%2Cd%25"
        )
        assert (
            encode(
                {"a": [",", "", "c,d%"]},
                options=EncodeOptions(encode=True, encode_values_only=False, list_format=ListFormat.COMMA),
            )
            == "a=%2C%2C%2Cc%2Cd%25"
        )
        assert (
            encode(
                {"a": [",", "", "c,d%"]},
                options=EncodeOptions(encode=True, encode_values_only=False, list_format=ListFormat.REPEAT),
            )
            == "a=%2C&a=&a=c%2Cd%25"
        )
        assert (
            encode(
                {"a": [",", "", "c,d%"]},
                options=EncodeOptions(encode=True, encode_values_only=False, list_format=ListFormat.INDICES),
            )
            == "a%5B0%5D=%2C&a%5B1%5D=&a%5B2%5D=c%2Cd%25"
        )

    def test_encodes_a_nested_list_value_with_dots_notation(self) -> None:
        assert (
            encode(
                {"a": {"b": ["c", "d"]}},
                options=EncodeOptions(allow_dots=True, encode_values_only=True, list_format=ListFormat.INDICES),
            )
            == "a.b[0]=c&a.b[1]=d"
        )
        assert (
            encode(
                {"a": {"b": ["c", "d"]}},
                options=EncodeOptions(allow_dots=True, encode_values_only=True, list_format=ListFormat.BRACKETS),
            )
            == "a.b[]=c&a.b[]=d"
        )
        assert (
            encode(
                {"a": {"b": ["c", "d"]}},
                options=EncodeOptions(allow_dots=True, encode_values_only=True, list_format=ListFormat.COMMA),
            )
            == "a.b=c,d"
        )
        assert (
            encode({"a": {"b": ["c", "d"]}}, options=EncodeOptions(allow_dots=True, encode_values_only=True))
            == "a.b[0]=c&a.b[1]=d"
        )

    def test_encodes_a_dict_inside_a_list(self):
        assert (
            encode({"a": [{"b": "c"}]}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES))
            == "a[0][b]=c"
        )
        assert (
            encode({"a": [{"b": "c"}]}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.REPEAT))
            == "a[b]=c"
        )
        assert (
            encode({"a": [{"b": "c"}]}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS))
            == "a[][b]=c"
        )
        assert encode({"a": [{"b": "c"}]}, options=EncodeOptions(encode_values_only=True)) == "a[0][b]=c"
        assert (
            encode(
                {"a": [{"b": {"c": [1]}}]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
            )
            == "a[0][b][c][0]=1"
        )
        assert (
            encode(
                {"a": [{"b": {"c": [1]}}]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.REPEAT),
            )
            == "a[b][c]=1"
        )
        assert (
            encode(
                {"a": [{"b": {"c": [1]}}]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
            )
            == "a[][b][c][]=1"
        )
        assert encode({"a": [{"b": {"c": [1]}}]}, options=EncodeOptions(encode_values_only=True)) == "a[0][b][c][0]=1"

    def test_encodes_a_list_with_mixed_maps_and_primitives(self) -> None:
        assert (
            encode(
                {"a": [{"b": 1}, 2, 3]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
            )
            == "a[0][b]=1&a[1]=2&a[2]=3"
        )
        assert (
            encode(
                {"a": [{"b": 1}, 2, 3]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
            )
            == "a[][b]=1&a[]=2&a[]=3"
        )
        assert (
            encode({"a": [{"b": 1}, 2, 3]}, options=EncodeOptions(encode_values_only=True)) == "a[0][b]=1&a[1]=2&a[2]=3"
        )

    def test_encodes_a_map_inside_a_list_with_dots_notation(self) -> None:
        assert (
            encode(
                {"a": [{"b": "c"}]},
                options=EncodeOptions(allow_dots=True, encode_values_only=True, list_format=ListFormat.INDICES),
            )
            == "a[0].b=c"
        )
        assert (
            encode(
                {"a": [{"b": "c"}]},
                options=EncodeOptions(allow_dots=True, encode_values_only=True, list_format=ListFormat.BRACKETS),
            )
            == "a[].b=c"
        )
        assert (
            encode({"a": [{"b": "c"}]}, options=EncodeOptions(allow_dots=True, encode_values_only=True)) == "a[0].b=c"
        )
        assert (
            encode(
                {"a": [{"b": {"c": [1]}}]},
                options=EncodeOptions(allow_dots=True, encode_values_only=True, list_format=ListFormat.INDICES),
            )
            == "a[0].b.c[0]=1"
        )
        assert (
            encode(
                {"a": [{"b": {"c": [1]}}]},
                options=EncodeOptions(allow_dots=True, encode_values_only=True, list_format=ListFormat.BRACKETS),
            )
            == "a[].b.c[]=1"
        )
        assert (
            encode({"a": [{"b": {"c": [1]}}]}, options=EncodeOptions(allow_dots=True, encode_values_only=True))
            == "a[0].b.c[0]=1"
        )

    def test_does_not_omit_map_keys_when_indices_is_false(self) -> None:
        assert encode({"a": [{"b": "c"}]}, options=EncodeOptions(indices=False)) == "a%5Bb%5D=c"

    def test_uses_indices_notation_for_lists_when_indices_is_true(self) -> None:
        assert encode({"a": ["b", "c"]}, options=EncodeOptions(indices=True)) == "a%5B0%5D=b&a%5B1%5D=c"

    def test_uses_indices_notation_for_lists_when_no_list_format_is_specified(self) -> None:
        assert encode({"a": ["b", "c"]}) == "a%5B0%5D=b&a%5B1%5D=c"

    def test_uses_indices_notation_for_lists_when_list_format_is_indices(self) -> None:
        assert (
            encode({"a": ["b", "c"]}, options=EncodeOptions(list_format=ListFormat.INDICES)) == "a%5B0%5D=b&a%5B1%5D=c"
        )

    def test_uses_repeat_notation_for_lists_when_list_format_is_repeat(self) -> None:
        assert encode({"a": ["b", "c"]}, options=EncodeOptions(list_format=ListFormat.REPEAT)) == "a=b&a=c"

    def test_uses_brackets_notation_for_lists_when_list_format_is_brackets(self) -> None:
        assert (
            encode({"a": ["b", "c"]}, options=EncodeOptions(list_format=ListFormat.BRACKETS)) == "a%5B%5D=b&a%5B%5D=c"
        )

    def test_encodes_a_complicated_map(self) -> None:
        assert encode({"a": {"b": "c", "d": "e"}}) == "a%5Bb%5D=c&a%5Bd%5D=e"

    def test_encodes_an_empty_value(self) -> None:
        assert encode({"a": ""}) == "a="
        assert encode({"a": None}, options=EncodeOptions(strict_null_handling=True)) == "a"
        assert encode({"a": "", "b": ""}) == "a=&b="
        assert encode({"a": None, "b": ""}, options=EncodeOptions(strict_null_handling=True)) == "a&b="
        assert encode({"a": {"b": ""}}) == "a%5Bb%5D="
        assert encode({"a": {"b": None}}, options=EncodeOptions(strict_null_handling=True)) == "a%5Bb%5D"
        assert encode({"a": {"b": None}}, options=EncodeOptions(strict_null_handling=False)) == "a%5Bb%5D="

    def test_encodes_a_null_map(self) -> None:
        obj: t.Dict[str, str] = {}
        obj["a"] = "b"
        assert encode(obj) == "a=b"

    def test_returns_an_empty_string_for_invalid_input(self) -> None:
        assert encode(None) == ""
        assert encode(False) == ""
        assert encode("") == ""

    def test_encodes_a_map_with_a_null_map_as_a_child(self) -> None:
        obj: t.Dict[str, t.Dict[str, str]] = {"a": {}}
        obj["a"]["b"] = "c"
        assert encode(obj) == "a%5Bb%5D=c"

    def test_url_encodes_values(self) -> None:
        assert encode({"a": "b c"}) == "a=b%20c"

    def test_encodes_a_date(self) -> None:
        now: datetime = datetime.now()
        assert encode({"a": now}) == f"a={quote(now.isoformat())}"

    def test_encodes_the_weird_map_from_qs(self) -> None:
        assert (
            encode({"my weird field": "~q1!2\"'w$5&7/z8)?"}) == "my%20weird%20field=~q1%212%22%27w%245%267%2Fz8%29%3F"
        )

    def test_encodes_boolean_values(self) -> None:
        assert encode({"a": True}) == "a=true"
        assert encode({"a": {"b": True}}) == "a%5Bb%5D=true"
        assert encode({"b": False}) == "b=false"
        assert encode({"b": {"c": False}}) == "b%5Bc%5D=false"

    def test_encodes_bytes_values(self) -> None:
        assert encode({"a": b"test"}) == "a=test"
        assert encode({"a": {"b": b"test"}}) == "a%5Bb%5D=test"

    def test_encodes_a_map_using_an_alternative_delimiter(self) -> None:
        assert encode({"a": "b", "c": "d"}, options=EncodeOptions(delimiter=";")) == "a=b;c=d"

    def test_does_not_crash_when_parsing_circular_references(self) -> None:
        a: t.Dict[str, t.Any] = {}
        a["b"] = a

        with pytest.raises(ValueError):
            encode({"foo[bar]": "baz", "foo[baz]": a})

        circular: t.Dict[str, t.Any] = {"a": "value"}
        circular["a"] = circular

        with pytest.raises(ValueError):
            encode(circular)

        arr: t.List[str] = ["a"]

        with does_not_raise():
            encode({"x": arr, "y": arr})

        assert encode({"x": arr, "y": arr}, options=EncodeOptions(encode=False)) == "x[0]=a&y[0]=a"

    def test_non_circular_duplicated_references_can_still_work(self) -> None:
        hour_of_day: t.Dict[str, t.Any] = {"function": "hour_of_day"}

        p1: t.Dict[str, t.Any] = {"function": "gte", "arguments": [hour_of_day, 0]}

        p2: t.Dict[str, t.Any] = {"function": "lte", "arguments": [hour_of_day, 23]}

        assert (
            encode(
                {"filters": {r"$and": [p1, p2]}},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
            )
            == "filters[$and][0][function]=gte&filters[$and][0][arguments][0][function]=hour_of_day&filters[$and][0][arguments][1]=0&filters[$and][1][function]=lte&filters[$and][1][arguments][0][function]=hour_of_day&filters[$and][1][arguments][1]=23"
        )

        assert (
            encode(
                {"filters": {r"$and": [p1, p2]}},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
            )
            == "filters[$and][][function]=gte&filters[$and][][arguments][][function]=hour_of_day&filters[$and][][arguments][]=0&filters[$and][][function]=lte&filters[$and][][arguments][][function]=hour_of_day&filters[$and][][arguments][]=23"
        )

        assert (
            encode(
                {"filters": {r"$and": [p1, p2]}},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.REPEAT),
            )
            == "filters[$and][function]=gte&filters[$and][arguments][function]=hour_of_day&filters[$and][arguments]=0&filters[$and][function]=lte&filters[$and][arguments][function]=hour_of_day&filters[$and][arguments]=23"
        )

    def test_selects_properties_when_filter_is_list(self) -> None:
        assert encode({"a": "b"}, options=EncodeOptions(filter=["a"])) == "a=b"
        assert encode({"a": 1}, options=EncodeOptions(filter=[])) == ""
        assert (
            encode(
                {"a": {"b": [1, 2, 3, 4], "c": "d"}, "c": "f"},
                options=EncodeOptions(filter=["a", "b", 0, 2], list_format=ListFormat.INDICES),
            )
            == "a%5Bb%5D%5B0%5D=1&a%5Bb%5D%5B2%5D=3"
        )
        assert (
            encode(
                {"a": {"b": [1, 2, 3, 4], "c": "d"}, "c": "f"},
                options=EncodeOptions(filter=["a", "b", 0, 2], list_format=ListFormat.BRACKETS),
            )
            == "a%5Bb%5D%5B%5D=1&a%5Bb%5D%5B%5D=3"
        )
        assert (
            encode(
                {"a": {"b": [1, 2, 3, 4], "c": "d"}, "c": "f"},
                options=EncodeOptions(filter=["a", "b", 0, 2]),
            )
            == "a%5Bb%5D%5B0%5D=1&a%5Bb%5D%5B2%5D=3"
        )

    def test_supports_custom_representations_when_filter_is_function(self) -> None:
        calls = 0

        def filter_func(prefix: str, value: t.Any) -> t.Any:
            nonlocal calls
            calls += 1

            if calls == 1:
                assert prefix == ""
                assert value == {"a": "b", "c": "d", "e": {"f": datetime.fromtimestamp(1257894000)}}
            elif prefix == "c":
                assert value == "d"
                return None
            elif isinstance(value, datetime):
                assert prefix == "e[f]"
                return int(value.timestamp())
            return value

        obj = {"a": "b", "c": "d", "e": {"f": datetime.fromtimestamp(1257894000)}}

        assert encode(obj, options=EncodeOptions(filter=filter_func)) == "a=b&c=&e%5Bf%5D=1257894000"
        assert calls == 5

    def test_can_disable_uri_encoding(self) -> None:
        assert encode({"a": "b"}, options=EncodeOptions(encode=False)) == "a=b"
        assert encode({"a": {"b": "c"}}, options=EncodeOptions(encode=False)) == "a[b]=c"
        assert encode({"a": "b", "c": None}, options=EncodeOptions(encode=False, strict_null_handling=True)) == "a=b&c"

    def test_can_sort_the_keys(self) -> None:
        def sort(a: str, b: str) -> int:
            if a > b:
                return 1
            if a < b:
                return -1
            return 0

        assert encode({"a": "c", "z": "y", "b": "f"}, options=EncodeOptions(sort=sort)) == "a=c&b=f&z=y"
        assert (
            encode(
                {"a": "c", "z": {"j": "a", "i": "b"}, "b": "f"},
                options=EncodeOptions(sort=sort),
            )
            == "a=c&b=f&z%5Bi%5D=b&z%5Bj%5D=a"
        )

    def test_can_sort_the_keys_at_depth_3_or_more_too(self) -> None:
        def sort(a: str, b: str) -> int:
            if a > b:
                return 1
            if a < b:
                return -1
            return 0

        assert (
            encode(
                {"a": "a", "z": {"zj": {"zjb": "zjb", "zja": "zja"}, "zi": {"zib": "zib", "zia": "zia"}}, "b": "b"},
                options=EncodeOptions(sort=sort, encode=False),
            )
            == "a=a&b=b&z[zi][zia]=zia&z[zi][zib]=zib&z[zj][zja]=zja&z[zj][zjb]=zjb"
        )
        assert (
            encode(
                {"a": "a", "z": {"zj": {"zjb": "zjb", "zja": "zja"}, "zi": {"zib": "zib", "zia": "zia"}}, "b": "b"},
                options=EncodeOptions(encode=False),
            )
            == "a=a&z[zj][zjb]=zjb&z[zj][zja]=zja&z[zi][zib]=zib&z[zi][zia]=zia&b=b"
        )

    def test_can_encode_with_custom_encoding(self) -> None:
        def _encode(string: str, charset: t.Optional[Charset] = None, format: t.Optional[Format] = None) -> str:
            return "".join([f"%{i:02x}" for i in bytes(string, "shift-jis")])

        assert encode({"県": "大阪府", "": ""}, options=EncodeOptions(encoder=_encode)) == "%8c%a7=%91%e5%8d%e3%95%7b&="

    def test_can_encode_with_custom_encoding_for_a_buffer_map(self) -> None:
        buf: bytes = bytes([1])

        def _encode1(buffer: t.AnyStr, charset: t.Optional[Charset] = None, format: t.Optional[Format] = None) -> str:
            if isinstance(buffer, str):
                return buffer
            return chr(buffer[0] + 97)

        assert encode({"a": buf}, options=EncodeOptions(encoder=_encode1)) == "a=b"

        buf2: bytes = "a b".encode("utf-8")

        def _encode2(buffer: t.AnyStr, charset: t.Optional[Charset] = None, format: t.Optional[Format] = None) -> str:
            if isinstance(buffer, bytes):
                return buffer.decode("utf-8")
            return buffer

        assert encode({"a": buf2}, options=EncodeOptions(encoder=_encode2)) == "a=a b"

    def test_serialize_date_option(self) -> None:
        date: datetime = datetime.now()
        assert encode({"a": date}) == f'a={date.isoformat().replace(":", "%3A")}'
        assert (
            encode(
                {"a": date},
                options=EncodeOptions(serialize_date=lambda d: str(int(d.timestamp()))),
            )
            == f"a={int(date.timestamp())}"
        )
        specific_date: datetime = datetime.fromtimestamp(6)
        assert (
            encode(
                {"a": specific_date},
                options=EncodeOptions(serialize_date=lambda d: str(int(d.timestamp()) * 7)),
            )
            == "a=42"
        )
        assert (
            encode(
                {"a": [date]},
                options=EncodeOptions(
                    serialize_date=lambda d: str(int(d.timestamp())),
                    list_format=ListFormat.COMMA,
                ),
            )
            == f"a={int(date.timestamp())}"
        )
        assert (
            encode(
                {"a": [date]},
                options=EncodeOptions(
                    serialize_date=lambda d: str(int(d.timestamp())),
                    list_format=ListFormat.COMMA,
                    comma_round_trip=True,
                ),
            )
            == f"a%5B%5D={int(date.timestamp())}"
        )

    def test_rfc_1738_serialization(self) -> None:
        assert encode({"a": "b c"}, options=EncodeOptions(format=Format.RFC1738)) == "a=b+c"
        assert encode({"a b": "c d"}, options=EncodeOptions(format=Format.RFC1738)) == "a+b=c+d"
        assert encode({"a b": "a b"}, options=EncodeOptions(format=Format.RFC1738)) == "a+b=a+b"
        assert encode({"foo(ref)": "bar"}, options=EncodeOptions(format=Format.RFC1738)) == "foo(ref)=bar"

    def test_rfc_3986_spaces_serialization(self) -> None:
        assert encode({"a": "b c"}, options=EncodeOptions(format=Format.RFC3986)) == "a=b%20c"
        assert encode({"a b": "c d"}, options=EncodeOptions(format=Format.RFC3986)) == "a%20b=c%20d"
        assert encode({"a b": "a b"}, options=EncodeOptions(format=Format.RFC3986)) == "a%20b=a%20b"

    def test_backward_compatibility_to_rfc_3986(self) -> None:
        assert encode({"a": "b c"}) == "a=b%20c"
        assert encode({"a b": "a b"}) == "a%20b=a%20b"

    def test_encode_values_only(self) -> None:
        assert (
            encode(
                {"a": "b", "c": ["d", "e=f"], "f": [["g"], ["h"]]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
            )
            == "a=b&c[0]=d&c[1]=e%3Df&f[0][0]=g&f[1][0]=h"
        )

        assert (
            encode(
                {"a": "b", "c": ["d", "e=f"], "f": [["g"], ["h"]]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
            )
            == "a=b&c[]=d&c[]=e%3Df&f[][]=g&f[][]=h"
        )

        assert (
            encode(
                {"a": "b", "c": ["d", "e=f"], "f": [["g"], ["h"]]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.REPEAT),
            )
            == "a=b&c=d&c=e%3Df&f=g&f=h"
        )

        assert (
            encode(
                {"a": "b", "c": ["d", "e"], "f": [["g"], ["h"]]}, options=EncodeOptions(list_format=ListFormat.INDICES)
            )
            == "a=b&c%5B0%5D=d&c%5B1%5D=e&f%5B0%5D%5B0%5D=g&f%5B1%5D%5B0%5D=h"
        )

        assert (
            encode(
                {"a": "b", "c": ["d", "e"], "f": [["g"], ["h"]]}, options=EncodeOptions(list_format=ListFormat.BRACKETS)
            )
            == "a=b&c%5B%5D=d&c%5B%5D=e&f%5B%5D%5B%5D=g&f%5B%5D%5B%5D=h"
        )

        assert (
            encode(
                {"a": "b", "c": ["d", "e"], "f": [["g"], ["h"]]}, options=EncodeOptions(list_format=ListFormat.REPEAT)
            )
            == "a=b&c=d&c=e&f=g&f=h"
        )

    def test_encode_values_only_and_strict_null_handling(self) -> None:
        assert (
            encode({"a": {"b": None}}, options=EncodeOptions(encode_values_only=True, strict_null_handling=True))
            == "a[b]"
        )

    def test_respects_a_charset_of_iso_8859_1(self) -> None:
        assert encode({"æ": "æ"}, options=EncodeOptions(charset=Charset.LATIN1)) == "%E6=%E6"

    def test_encodes_unrepresentable_chars_as_numeric_entities_in_iso_8859_1_mode(self) -> None:
        assert encode({"a": "☺"}, options=EncodeOptions(charset=Charset.LATIN1)) == "a=%26%239786%3B"

    def test_respects_an_explicit_charset_of_utf_8_the_default(self) -> None:
        assert encode({"a": "æ"}, options=EncodeOptions(charset=Charset.UTF8)) == "a=%C3%A6"

    def test_charset_sentinel_option(self) -> None:
        assert (
            encode({"a": "æ"}, options=EncodeOptions(charset_sentinel=True, charset=Charset.UTF8))
            == "utf8=%E2%9C%93&a=%C3%A6"
        )
        assert (
            encode({"a": "æ"}, options=EncodeOptions(charset_sentinel=True, charset=Charset.LATIN1))
            == "utf8=%26%2310003%3B&a=%E6"
        )

    def test_strict_null_handling_works_with_null_serialize_date(self) -> None:
        assert (
            encode(
                {"key": datetime.now()},
                options=EncodeOptions(
                    strict_null_handling=True,
                    serialize_date=lambda _: None,
                ),
            )
            == "key"
        )

    def test_does_not_mutate_the_options_argument(self) -> None:
        options = EncodeOptions()
        encode({}, options)
        assert options == EncodeOptions()

    def test_strict_null_handling_works_with_custom_filter(self) -> None:
        options = EncodeOptions(strict_null_handling=True, filter=lambda prefix, value: value)
        assert encode({"key": None}, options) == "key"

    def test_objects_inside_lists(self) -> None:
        obj: t.Dict[str, t.Any] = {"a": {"b": {"c": "d", "e": "f"}}}
        with_list: t.Dict[str, t.Any] = {"a": {"b": [{"c": "d", "e": "f"}]}}

        assert encode(obj, options=EncodeOptions(encode=False)) == "a[b][c]=d&a[b][e]=f"
        assert (
            encode(obj, options=EncodeOptions(encode=False, list_format=ListFormat.BRACKETS)) == "a[b][c]=d&a[b][e]=f"
        )
        assert encode(obj, options=EncodeOptions(encode=False, list_format=ListFormat.INDICES)) == "a[b][c]=d&a[b][e]=f"
        assert encode(obj, options=EncodeOptions(encode=False, list_format=ListFormat.REPEAT)) == "a[b][c]=d&a[b][e]=f"
        assert encode(obj, options=EncodeOptions(encode=False, list_format=ListFormat.COMMA)) == "a[b][c]=d&a[b][e]=f"

        assert encode(with_list, options=EncodeOptions(encode=False)) == "a[b][0][c]=d&a[b][0][e]=f"
        assert (
            encode(with_list, options=EncodeOptions(encode=False, list_format=ListFormat.BRACKETS))
            == "a[b][][c]=d&a[b][][e]=f"
        )
        assert (
            encode(with_list, options=EncodeOptions(encode=False, list_format=ListFormat.INDICES))
            == "a[b][0][c]=d&a[b][0][e]=f"
        )
        assert (
            encode(with_list, options=EncodeOptions(encode=False, list_format=ListFormat.REPEAT))
            == "a[b][c]=d&a[b][e]=f"
        )

    def test_encodes_lists_with_nulls(self) -> None:
        assert (
            encode(
                {"a": [None, "2", None, None, "1"]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
            )
            == "a[0]=&a[1]=2&a[2]=&a[3]=&a[4]=1"
        )
        assert (
            encode(
                {"a": [None, "2", None, None, "1"]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
            )
            == "a[]=&a[]=2&a[]=&a[]=&a[]=1"
        )
        assert (
            encode(
                {"a": [None, "2", None, None, "1"]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.REPEAT),
            )
            == "a=&a=2&a=&a=&a=1"
        )
        assert (
            encode(
                {"a": [None, {"b": [None, None, {"c": "1"}]}]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
            )
            == "a[0]=&a[1][b][0]=&a[1][b][1]=&a[1][b][2][c]=1"
        )
        assert (
            encode(
                {"a": [None, {"b": [None, None, {"c": "1"}]}]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
            )
            == "a[]=&a[][b][]=&a[][b][]=&a[][b][][c]=1"
        )
        assert (
            encode(
                {"a": [None, {"b": [None, None, {"c": "1"}]}]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.REPEAT),
            )
            == "a=&a[b]=&a[b]=&a[b][c]=1"
        )
        assert (
            encode(
                {"a": [None, [None, [None, None, {"c": "1"}]]]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
            )
            == "a[0]=&a[1][0]=&a[1][1][0]=&a[1][1][1]=&a[1][1][2][c]=1"
        )
        assert (
            encode(
                {"a": [None, [None, [None, None, {"c": "1"}]]]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
            )
            == "a[]=&a[][]=&a[][][]=&a[][][]=&a[][][][c]=1"
        )
        assert (
            encode(
                {"a": [None, [None, [None, None, {"c": "1"}]]]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.REPEAT),
            )
            == "a=&a=&a=&a=&a[c]=1"
        )

    def test_encodes_url(self) -> None:
        assert (
            encode(
                {"url": "https://example.com?foo=bar&baz=qux"},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
            )
            == "url=https%3A%2F%2Fexample.com%3Ffoo%3Dbar%26baz%3Dqux"
        )

    def test_encodes_spatie_dict(self) -> None:
        assert (
            encode(
                {
                    "filters": {
                        r"$or": [
                            {"date": {r"$eq": "2020-01-01"}},
                            {"date": {r"$eq": "2020-01-02"}},
                        ],
                        "author": {"name": {r"$eq": "John doe"}},
                    },
                },
                options=EncodeOptions(encode=False, list_format=ListFormat.BRACKETS),
            )
            == r"filters[$or][][date][$eq]=2020-01-01&filters[$or][][date][$eq]=2020-01-02&filters[author][name][$eq]=John doe"
        )

        assert (
            encode(
                {
                    "filters": {
                        r"$or": [
                            {"date": {r"$eq": "2020-01-01"}},
                            {"date": {r"$eq": "2020-01-02"}},
                        ],
                        "author": {"name": {r"$eq": "John doe"}},
                    },
                },
                options=EncodeOptions(list_format=ListFormat.BRACKETS),
            )
            == "filters%5B%24or%5D%5B%5D%5Bdate%5D%5B%24eq%5D=2020-01-01&filters%5B%24or%5D%5B%5D%5Bdate%5D%5B%24eq%5D=2020-01-02&filters%5Bauthor%5D%5Bname%5D%5B%24eq%5D=John%20doe"
        )


class TestEncodesAListValueWithOneItemVsMultipleItems:
    def test_non_list_item(self) -> None:
        assert (
            encode({"a": "c"}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES)) == "a=c"
        )
        assert (
            encode({"a": "c"}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS)) == "a=c"
        )
        assert encode({"a": "c"}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.COMMA)) == "a=c"
        assert encode({"a": "c"}, options=EncodeOptions(encode_values_only=True)) == "a=c"

    def test_list_with_a_single_item(self) -> None:
        assert (
            encode({"a": ["c"]}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES))
            == "a[0]=c"
        )
        assert (
            encode({"a": ["c"]}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS))
            == "a[]=c"
        )
        assert (
            encode({"a": ["c"]}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.COMMA)) == "a=c"
        )
        assert (
            encode(
                {"a": ["c"]},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.COMMA, comma_round_trip=True),
            )
            == "a[]=c"
        )
        assert encode({"a": ["c"]}, options=EncodeOptions(encode_values_only=True)) == "a[0]=c"

    def test_list_with_multiple_items(self) -> None:
        assert (
            encode({"a": ["c", "d"]}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES))
            == "a[0]=c&a[1]=d"
        )
        assert (
            encode({"a": ["c", "d"]}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS))
            == "a[]=c&a[]=d"
        )
        assert (
            encode({"a": ["c", "d"]}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.COMMA))
            == "a=c,d"
        )
        assert (
            encode(
                {"a": ["c", "d"]},
                options=EncodeOptions(
                    encode_values_only=True,
                    list_format=ListFormat.COMMA,
                    comma_round_trip=True,
                ),
            )
            == "a=c,d"
        )
        assert encode({"a": ["c", "d"]}, options=EncodeOptions(encode_values_only=True)) == "a[0]=c&a[1]=d"

    def test_list_with_multiple_items_with_a_comma_inside(self) -> None:
        assert (
            encode({"a": ["c,d", "e"]}, options=EncodeOptions(encode_values_only=True, list_format=ListFormat.COMMA))
            == "a=c%2Cd,e"
        )
        assert encode({"a": ["c,d", "e"]}, options=EncodeOptions(list_format=ListFormat.COMMA)) == "a=c%2Cd%2Ce"
        assert (
            encode(
                {"a": ["c,d", "e"]},
                options=EncodeOptions(
                    encode_values_only=True,
                    list_format=ListFormat.COMMA,
                    comma_round_trip=True,
                ),
            )
            == "a=c%2Cd,e"
        )
        assert (
            encode({"a": ["c,d", "e"]}, options=EncodeOptions(list_format=ListFormat.COMMA, comma_round_trip=True))
            == "a=c%2Cd%2Ce"
        )


class TestEncodesAListInDifferentListFormats:
    def test_default_parameters(self) -> None:
        assert encode({"a": [], "b": [None], "c": "c"}, options=EncodeOptions(encode=False)) == "b[0]=&c=c"

    def test_list_format_default(self) -> None:
        assert encode({"a": [], "b": [None], "c": "c"}, options=EncodeOptions(encode=False)) == "b[0]=&c=c"
        assert (
            encode(
                {"a": [], "b": [None], "c": "c"}, options=EncodeOptions(encode=False, list_format=ListFormat.INDICES)
            )
            == "b[0]=&c=c"
        )
        assert (
            encode(
                {"a": [], "b": [None], "c": "c"}, options=EncodeOptions(encode=False, list_format=ListFormat.BRACKETS)
            )
            == "b[]=&c=c"
        )
        assert (
            encode({"a": [], "b": [None], "c": "c"}, options=EncodeOptions(encode=False, list_format=ListFormat.REPEAT))
            == "b=&c=c"
        )
        assert (
            encode({"a": [], "b": [None], "c": "c"}, options=EncodeOptions(encode=False, list_format=ListFormat.COMMA))
            == "b=&c=c"
        )
        assert (
            encode(
                {"a": [], "b": [None], "c": "c"},
                options=EncodeOptions(encode=False, list_format=ListFormat.COMMA, comma_round_trip=True),
            )
            == "b[]=&c=c"
        )

    def test_with_strict_null_handling(self) -> None:
        assert (
            encode(
                {"a": [], "b": [None], "c": "c"},
                options=EncodeOptions(encode=False, list_format=ListFormat.BRACKETS, strict_null_handling=True),
            )
            == "b[]&c=c"
        )
        assert (
            encode(
                {"a": [], "b": [None], "c": "c"},
                options=EncodeOptions(encode=False, list_format=ListFormat.REPEAT, strict_null_handling=True),
            )
            == "b&c=c"
        )
        assert (
            encode(
                {"a": [], "b": [None], "c": "c"},
                options=EncodeOptions(encode=False, list_format=ListFormat.COMMA, strict_null_handling=True),
            )
            == "b&c=c"
        )
        assert (
            encode(
                {"a": [], "b": [None], "c": "c"},
                options=EncodeOptions(
                    encode=False, list_format=ListFormat.COMMA, strict_null_handling=True, comma_round_trip=True
                ),
            )
            == "b[]&c=c"
        )

    def test_with_skip_nulls(self) -> None:
        assert (
            encode(
                {"a": [], "b": [None], "c": "c"},
                options=EncodeOptions(encode=False, list_format=ListFormat.INDICES, skip_nulls=True),
            )
            == "c=c"
        )
        assert (
            encode(
                {"a": [], "b": [None], "c": "c"},
                options=EncodeOptions(encode=False, list_format=ListFormat.BRACKETS, skip_nulls=True),
            )
            == "c=c"
        )
        assert (
            encode(
                {"a": [], "b": [None], "c": "c"},
                options=EncodeOptions(encode=False, list_format=ListFormat.REPEAT, skip_nulls=True),
            )
            == "c=c"
        )
        assert (
            encode(
                {"a": [], "b": [None], "c": "c"},
                options=EncodeOptions(encode=False, list_format=ListFormat.COMMA, skip_nulls=True),
            )
            == "c=c"
        )


class TestEncodesEmptyKeys:
    @pytest.mark.parametrize(
        "with_empty_keys, indices, brackets, repeat",
        [
            ({}, "", "", ""),
            ({}, "", "", ""),
            ({"": ""}, "=", "=", "="),
            ({"": ""}, "=", "=", "="),
            ({"": ["", ""]}, "[0]=&[1]=", "[]=&[]=", "=&="),
            ({"": ["", ""]}, "[0]=&[1]=", "[]=&[]=", "=&="),
            ({"": ""}, "=", "=", "="),
            ({"": ""}, "=", "=", "="),
            ({"": ""}, "=", "=", "="),
            ({"": ["", "", ""]}, "[0]=&[1]=&[2]=", "[]=&[]=&[]=", "=&=&="),
            ({"": "", "a": ["b", "c"]}, "=&a[0]=b&a[1]=c", "=&a[]=b&a[]=c", "=&a=b&a=c"),
            ({"": "a"}, "=a", "=a", "=a"),
            ({"a": "=a"}, "a==a", "a==a", "a==a"),
            ({"": "", "a": ["b"]}, "=&a[0]=b", "=&a[]=b", "=&a=b"),
            ({"": "", "a": ["b", "c", "d"]}, "=&a[0]=b&a[1]=c&a[2]=d", "=&a[]=b&a[]=c&a[]=d", "=&a=b&a=c&a=d"),
            ({"": ["a", "b"]}, "[0]=a&[1]=b", "[]=a&[]=b", "=a&=b"),
            ({"": "a", "foo": "b"}, "=a&foo=b", "=a&foo=b", "=a&foo=b"),
            ({"": "", "a": ["b", "c"]}, "=&a[0]=b&a[1]=c", "=&a[]=b&a[]=c", "=&a=b&a=c"),
            ({"": "", "a": ["b", "c"]}, "=&a[0]=b&a[1]=c", "=&a[]=b&a[]=c", "=&a=b&a=c"),
            ({"": "", "a": ["b", "c"]}, "=&a[0]=b&a[1]=c", "=&a[]=b&a[]=c", "=&a=b&a=c"),
            ({"": "", "a": ["b", "c"]}, "=&a[0]=b&a[1]=c", "=&a[]=b&a[]=c", "=&a=b&a=c"),
            ({"": "", "a": ["b", "c"]}, "=&a[0]=b&a[1]=c", "=&a[]=b&a[]=c", "=&a=b&a=c"),
            ({"": ["a", "b"], " ": ["1"]}, "[0]=a&[1]=b& [0]=1", "[]=a&[]=b& []=1", "=a&=b& =1"),
            ({"": ["a", "b"], "a": ["1", "2"]}, "[0]=a&[1]=b&a[0]=1&a[1]=2", "[]=a&[]=b&a[]=1&a[]=2", "=a&=b&a=1&a=2"),
            ({"": {"deep": ["a", "2"]}}, "[deep][0]=a&[deep][1]=2", "[deep][]=a&[deep][]=2", "[deep]=a&[deep]=2"),
            ({"": ["a", "b"]}, "[0]=a&[1]=b", "[]=a&[]=b", "=a&=b"),
        ],
    )
    def test_encodes_a_dict_with_empty_string_keys(
        self, with_empty_keys: t.Mapping[str, t.Any], indices: str, brackets: str, repeat: str
    ) -> None:
        assert encode(with_empty_keys, options=EncodeOptions(encode=False)) == indices
        assert encode(with_empty_keys, options=EncodeOptions(encode=False, list_format=ListFormat.INDICES)) == indices
        assert encode(with_empty_keys, options=EncodeOptions(encode=False, list_format=ListFormat.BRACKETS)) == brackets
        assert encode(with_empty_keys, options=EncodeOptions(encode=False, list_format=ListFormat.REPEAT)) == repeat

    def test_edge_case_with_map_lists(self) -> None:
        assert encode({"": {"": [2, 3]}}, options=EncodeOptions(encode=False)) == "[][0]=2&[][1]=3"
        assert encode({"": {"": [2, 3], "a": 2}}, options=EncodeOptions(encode=False)) == "[][0]=2&[][1]=3&[a]=2"
        assert (
            encode({"": {"": [2, 3]}}, options=EncodeOptions(encode=False, list_format=ListFormat.INDICES))
            == "[][0]=2&[][1]=3"
        )
        assert (
            encode({"": {"": [2, 3], "a": 2}}, options=EncodeOptions(encode=False, list_format=ListFormat.INDICES))
            == "[][0]=2&[][1]=3&[a]=2"
        )


class TestEncodeNonStrings:
    def test_encodes_a_null_value(self) -> None:
        assert encode({"a": None}) == "a="

    def test_encodes_a_boolean_value(self) -> None:
        assert encode({"a": True}) == "a=true"
        assert encode({"a": False}) == "a=false"

    def test_encodes_a_number_value(self) -> None:
        assert encode({"a": 0}) == "a=0"
        assert encode({"a": 1}) == "a=1"
        assert encode({"a": 1.1}) == "a=1.1"

    def test_encodes_a_buffer_value(self) -> None:
        assert encode({"a": b"test"}) == "a=test"

    def test_encodes_a_date_value(self) -> None:
        now: datetime = datetime.now()
        assert encode({"a": now}) == f"a={now.isoformat().replace(':', '%3A')}"

    def test_encodes_a_decimal(self) -> None:
        assert encode({"a": Decimal("1.23456")}) == "a=1.23456"

    def test_encodes_a_list_value(self) -> None:
        assert encode({"a": [1, 2, 3]}) == "a%5B0%5D=1&a%5B1%5D=2&a%5B2%5D=3"

    def test_encodes_a_map_value(self) -> None:
        assert encode({"a": {"b": "c"}}) == "a%5Bb%5D=c"

    def test_encodes_a_map_with_a_null_map_as_a_child(self) -> None:
        obj: t.Dict[str, t.Any] = {"a": {}}
        obj["a"]["b"] = "c"
        assert encode(obj) == "a%5Bb%5D=c"

    def test_encodes_a_map_with_an_enum_as_a_child(self) -> None:
        class DummyEnum(Enum):
            lorem = "lorem"
            ipsum = "ipsum"
            dolor = "dolor"

            def __str__(self):
                return self.value

        assert (
            encode({"a": DummyEnum.lorem, "b": "foo", "c": 1, "d": 1.234, "e": True})
            == "a=lorem&b=foo&c=1&d=1.234&e=true"
        )

    def test_does_not_encode_undefined(self) -> None:
        assert encode({"a": Undefined()}) == ""
