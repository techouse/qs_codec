import math
import typing as t
from contextlib import nullcontext as does_not_raise
from datetime import datetime
from decimal import Decimal
from enum import Enum
from urllib.parse import quote

import pytest

from qs_codec import Charset, EncodeOptions, Format, ListFormat, dumps, encode
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
    def test_dumps_alias(self, decoded: t.Mapping, encoded: str) -> None:
        assert dumps(decoded) == encoded

    @pytest.mark.parametrize(
        "decoded, encoded",
        [
            ([1234], "0=1234"),
            (["lorem", 1234, "ipsum"], "0=lorem&1=1234&2=ipsum"),
        ],
    )
    def test_encodes_a_list(self, decoded: t.Any, encoded: str) -> None:
        assert encode(decoded) == encoded

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param({}, None, "", id="empty-dict"),
            pytest.param(None, None, "", id="none-default"),
            pytest.param(None, EncodeOptions(strict_null_handling=True), "", id="none-strict-null"),
            pytest.param(False, None, "", id="false"),
            pytest.param(0, None, "", id="zero"),
        ],
    )
    def test_encodes_falsy_values(self, data: t.Any, options: t.Optional[EncodeOptions], expected: str) -> None:
        result = encode(data) if options is None else encode(data, options)
        assert result == expected

    _PI: Decimal = Decimal(math.pi)

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(_PI, None, "", id="decimal-root"),
            pytest.param([_PI], None, f"0=3.141592653589793115997963468544185161590576171875", id="list-decimal"),
            pytest.param(
                [_PI],
                EncodeOptions(
                    encoder=lambda v, charset=None, format=None: (
                        f"{EncodeUtils.encode(v)}n" if isinstance(v, Decimal) else EncodeUtils.encode(v)
                    )
                ),
                f"0=3.141592653589793115997963468544185161590576171875n",
                id="list-decimal-with-n",
            ),
            pytest.param({"a": _PI}, None, f"a=3.141592653589793115997963468544185161590576171875", id="dict-decimal"),
            pytest.param(
                {"a": _PI},
                EncodeOptions(
                    encoder=lambda v, charset=None, format=None: (
                        f"{EncodeUtils.encode(v)}n" if isinstance(v, Decimal) else EncodeUtils.encode(v)
                    )
                ),
                f"a=3.141592653589793115997963468544185161590576171875n",
                id="dict-decimal-with-n",
            ),
            pytest.param(
                {"a": [_PI]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
                f"a[]=3.141592653589793115997963468544185161590576171875",
                id="brackets-list-decimal",
            ),
            pytest.param(
                {"a": [_PI]},
                EncodeOptions(
                    encode_values_only=True,
                    list_format=ListFormat.BRACKETS,
                    encoder=lambda v, charset=None, format=None: (
                        f"{EncodeUtils.encode(v)}n" if isinstance(v, Decimal) else EncodeUtils.encode(v)
                    ),
                ),
                f"a[]=3.141592653589793115997963468544185161590576171875n",
                id="brackets-list-decimal-with-n",
            ),
        ],
    )
    def test_encodes_decimal(self, data: t.Any, options: t.Optional[EncodeOptions], expected: str) -> None:
        result = encode(data) if options is None else encode(data, options)
        assert result == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"name.obj": {"first": "John", "last": "Doe"}},
                EncodeOptions(allow_dots=False, encode_dot_in_keys=False),
                "name.obj%5Bfirst%5D=John&name.obj%5Blast%5D=Doe",
                id="no-dots-no-encode-dot",
            ),
            pytest.param(
                {"name.obj": {"first": "John", "last": "Doe"}},
                EncodeOptions(allow_dots=True, encode_dot_in_keys=False),
                "name.obj.first=John&name.obj.last=Doe",
                id="allow-dots-no-encode-dot",
            ),
            pytest.param(
                {"name.obj": {"first": "John", "last": "Doe"}},
                EncodeOptions(allow_dots=False, encode_dot_in_keys=True),
                "name%252Eobj%5Bfirst%5D=John&name%252Eobj%5Blast%5D=Doe",
                id="no-dots-encode-dot",
            ),
            pytest.param(
                {"name.obj": {"first": "John", "last": "Doe"}},
                EncodeOptions(allow_dots=True, encode_dot_in_keys=True),
                "name%252Eobj.first=John&name%252Eobj.last=Doe",
                id="allow-dots-encode-dot",
            ),
            pytest.param(
                {"name.obj.subobject": {"first.godly.name": "John", "last": "Doe"}},
                EncodeOptions(allow_dots=True, encode_dot_in_keys=False),
                "name.obj.subobject.first.godly.name=John&name.obj.subobject.last=Doe",
                id="subobj-allow-dots-no-encode-dot",
            ),
            pytest.param(
                {"name.obj.subobject": {"first.godly.name": "John", "last": "Doe"}},
                EncodeOptions(allow_dots=False, encode_dot_in_keys=True),
                "name%252Eobj%252Esubobject%5Bfirst.godly.name%5D=John&name%252Eobj%252Esubobject%5Blast%5D=Doe",
                id="subobj-no-dots-encode-dot",
            ),
            pytest.param(
                {"name.obj.subobject": {"first.godly.name": "John", "last": "Doe"}},
                EncodeOptions(allow_dots=True, encode_dot_in_keys=True),
                "name%252Eobj%252Esubobject.first%252Egodly%252Ename=John&name%252Eobj%252Esubobject.last=Doe",
                id="subobj-allow-dots-encode-dot",
            ),
        ],
    )
    def test_encodes_dot_in_key_of_dict_when_encode_dot_in_keys_and_allow_dots_is_provided(
        self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str
    ) -> None:
        assert encode(data, options) == expected

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

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"name.obj": {"first": "John", "last": "Doe"}},
                EncodeOptions(encode_dot_in_keys=True, allow_dots=True, encode_values_only=True),
                "name%2Eobj.first=John&name%2Eobj.last=Doe",
                id="encode-dot-only-values-simple",
            ),
            pytest.param(
                {"name.obj.subobject": {"first.godly.name": "John", "last": "Doe"}},
                EncodeOptions(allow_dots=True, encode_dot_in_keys=True, encode_values_only=True),
                "name%2Eobj%2Esubobject.first%2Egodly%2Ename=John&name%2Eobj%2Esubobject.last=Doe",
                id="encode-dot-only-values-nested",
            ),
        ],
    )
    def test_should_encode_dot_in_key_of_dict_when_encode_dot_in_keys_and_allow_dots_is_provided_and_nothing_else_when_encode_values_only_is_provided(
        self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str
    ) -> None:
        assert encode(data, options) == expected

    def test_adds_query_prefix(self) -> None:
        assert encode({"a": "b"}, options=EncodeOptions(add_query_prefix=True)) == "?a=b"

    def test_with_query_prefix_outputs_blank_string_given_an_empty_dict(self) -> None:
        assert encode({}, options=EncodeOptions(add_query_prefix=True)) == ""

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param({"a": {"b": {"c": None}}}, None, "a%5Bb%5D%5Bc%5D=", id="nested-null-default"),
            pytest.param(
                {"a": {"b": {"c": None}}},
                EncodeOptions(strict_null_handling=True),
                "a%5Bb%5D%5Bc%5D",
                id="nested-null-strict",
            ),
            pytest.param({"a": {"b": {"c": False}}}, None, "a%5Bb%5D%5Bc%5D=false", id="nested-false-default"),
        ],
    )
    def test_encodes_nested_falsy_values(
        self, data: t.Mapping[str, t.Any], options: t.Optional[EncodeOptions], expected: str
    ) -> None:
        result = encode(data) if options is None else encode(data, options)
        assert result == expected

    @pytest.mark.parametrize(
        "data, expected",
        [
            pytest.param({"a": {"b": "c"}}, "a%5Bb%5D=c", id="one-level-nested"),
            pytest.param({"a": {"b": {"c": {"d": "e"}}}}, "a%5Bb%5D%5Bc%5D%5Bd%5D=e", id="multi-level-nested"),
        ],
    )
    def test_encodes_a_nested_dict(self, data: t.Mapping[str, t.Any], expected: str) -> None:
        assert encode(data) == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param({"a": {"b": "c"}}, EncodeOptions(allow_dots=True), "a.b=c", id="one-level-dots"),
            pytest.param(
                {"a": {"b": {"c": {"d": "e"}}}}, EncodeOptions(allow_dots=True), "a.b.c.d=e", id="multi-level-dots"
            ),
        ],
    )
    def test_encodes_a_nested_dict_with_dots_notation(
        self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str
    ) -> None:
        assert encode(data, options) == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": ["b", "c", "d"]},
                EncodeOptions(list_format=ListFormat.INDICES),
                "a%5B0%5D=b&a%5B1%5D=c&a%5B2%5D=d",
                id="list-indices",
            ),
            pytest.param(
                {"a": ["b", "c", "d"]},
                EncodeOptions(list_format=ListFormat.BRACKETS),
                "a%5B%5D=b&a%5B%5D=c&a%5B%5D=d",
                id="list-brackets",
            ),
            pytest.param(
                {"a": ["b", "c", "d"]}, EncodeOptions(list_format=ListFormat.COMMA), "a=b%2Cc%2Cd", id="list-comma"
            ),
            pytest.param(
                {"a": ["b", "c", "d"]},
                EncodeOptions(list_format=ListFormat.COMMA, comma_round_trip=True),
                "a=b%2Cc%2Cd",
                id="list-comma-round-trip",
            ),
            pytest.param({"a": ["b", "c", "d"]}, None, "a%5B0%5D=b&a%5B1%5D=c&a%5B2%5D=d", id="default-list-format"),
        ],
    )
    def test_encodes_a_list_value(
        self, data: t.Mapping[str, t.Any], options: t.Optional[EncodeOptions], expected: str
    ) -> None:
        result = encode(data) if options is None else encode(data, options)
        assert result == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param({"a": "b", "c": None}, EncodeOptions(skip_nulls=True), "a=b", id="skip-nulls-simple"),
            pytest.param(
                {"a": {"b": "c", "d": None}},
                EncodeOptions(skip_nulls=True),
                "a%5Bb%5D=c",
                id="skip-nulls-nested",
            ),
            pytest.param({"a": ["b", "c", "d"]}, EncodeOptions(indices=False), "a=b&a=c&a=d", id="no-indices-list"),
            pytest.param({"a": [], "b": "zz"}, None, "b=zz", id="empty-list-default"),
            pytest.param(
                {"a": [], "b": "zz"},
                EncodeOptions(allow_empty_lists=False),
                "b=zz",
                id="empty-list-disallow-empty-lists",
            ),
            pytest.param(
                {"a": [], "b": "zz"},
                EncodeOptions(allow_empty_lists=True),
                "a[]&b=zz",
                id="empty-list-allow-empty-lists",
            ),
        ],
    )
    def test_omits_nulls_list_indices_and_empty_lists(
        self, data: t.Mapping[str, t.Any], options: t.Optional[EncodeOptions], expected: str
    ) -> None:
        result = encode(data) if options is None else encode(data, options)
        assert result == expected

    def test_empty_list_with_strict_null_handling(self) -> None:
        assert (
            encode({"testEmptyList": []}, options=EncodeOptions(strict_null_handling=True, allow_empty_lists=True))
            == "testEmptyList[]"
        )

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": {"b": ["c", "d"]}},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
                "a[b][0]=c&a[b][1]=d",
                id="nested-list-indices",
            ),
            pytest.param(
                {"a": {"b": ["c", "d"]}},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a[b][]=c&a[b][]=d",
                id="nested-list-brackets",
            ),
            pytest.param(
                {"a": {"b": ["c", "d"]}},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.COMMA),
                "a[b]=c,d",
                id="nested-list-comma",
            ),
            pytest.param(
                {"a": {"b": ["c", "d"]}},
                EncodeOptions(encode_values_only=True),
                "a[b][0]=c&a[b][1]=d",
                id="nested-list-default",
            ),
        ],
    )
    def test_encodes_a_nested_list_value(
        self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str
    ) -> None:
        assert encode(data, options) == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": [",", "", "c,d%"]},
                EncodeOptions(encode=False, list_format=ListFormat.INDICES),
                "a[0]=,&a[1]=&a[2]=c,d%",
                id="no-encode-indices",
            ),
            pytest.param(
                {"a": [",", "", "c,d%"]},
                EncodeOptions(encode=False, list_format=ListFormat.BRACKETS),
                "a[]=,&a[]=&a[]=c,d%",
                id="no-encode-brackets",
            ),
            pytest.param(
                {"a": [",", "", "c,d%"]},
                EncodeOptions(encode=False, list_format=ListFormat.COMMA),
                "a=,,,c,d%",
                id="no-encode-comma",
            ),
            pytest.param(
                {"a": [",", "", "c,d%"]},
                EncodeOptions(encode=False, list_format=ListFormat.REPEAT),
                "a=,&a=&a=c,d%",
                id="no-encode-repeat",
            ),
            pytest.param(
                {"a": [",", "", "c,d%"]},
                EncodeOptions(encode=True, encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a[]=%2C&a[]=&a[]=c%2Cd%25",
                id="values-only-brackets",
            ),
            pytest.param(
                {"a": [",", "", "c,d%"]},
                EncodeOptions(encode=True, encode_values_only=True, list_format=ListFormat.COMMA),
                "a=%2C,,c%2Cd%25",
                id="values-only-comma",
            ),
            pytest.param(
                {"a": [",", "", "c,d%"]},
                EncodeOptions(encode=True, encode_values_only=True, list_format=ListFormat.REPEAT),
                "a=%2C&a=&a=c%2Cd%25",
                id="values-only-repeat",
            ),
            pytest.param(
                {"a": [",", "", "c,d%"]},
                EncodeOptions(encode=True, encode_values_only=True, list_format=ListFormat.INDICES),
                "a[0]=%2C&a[1]=&a[2]=c%2Cd%25",
                id="values-only-indices",
            ),
            pytest.param(
                {"a": [",", "", "c,d%"]},
                EncodeOptions(encode=True, encode_values_only=False, list_format=ListFormat.BRACKETS),
                "a%5B%5D=%2C&a%5B%5D=&a%5B%5D=c%2Cd%25",
                id="all-brackets",
            ),
            pytest.param(
                {"a": [",", "", "c,d%"]},
                EncodeOptions(encode=True, encode_values_only=False, list_format=ListFormat.COMMA),
                "a=%2C%2C%2Cc%2Cd%25",
                id="all-comma",
            ),
            pytest.param(
                {"a": [",", "", "c,d%"]},
                EncodeOptions(encode=True, encode_values_only=False, list_format=ListFormat.REPEAT),
                "a=%2C&a=&a=c%2Cd%25",
                id="all-repeat",
            ),
            pytest.param(
                {"a": [",", "", "c,d%"]},
                EncodeOptions(encode=True, encode_values_only=False, list_format=ListFormat.INDICES),
                "a%5B0%5D=%2C&a%5B1%5D=&a%5B2%5D=c%2Cd%25",
                id="all-indices",
            ),
        ],
    )
    def test_encodes_comma_and_empty_list_values(
        self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str
    ) -> None:
        assert encode(data, options) == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": {"b": ["c", "d"]}},
                EncodeOptions(allow_dots=True, encode_values_only=True, list_format=ListFormat.INDICES),
                "a.b[0]=c&a.b[1]=d",
                id="dots-indices",
            ),
            pytest.param(
                {"a": {"b": ["c", "d"]}},
                EncodeOptions(allow_dots=True, encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a.b[]=c&a.b[]=d",
                id="dots-brackets",
            ),
            pytest.param(
                {"a": {"b": ["c", "d"]}},
                EncodeOptions(allow_dots=True, encode_values_only=True, list_format=ListFormat.COMMA),
                "a.b=c,d",
                id="dots-comma",
            ),
            pytest.param(
                {"a": {"b": ["c", "d"]}},
                EncodeOptions(allow_dots=True, encode_values_only=True),
                "a.b[0]=c&a.b[1]=d",
                id="dots-default",
            ),
        ],
    )
    def test_encodes_a_nested_list_value_with_dots_notation(
        self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str
    ) -> None:
        assert encode(data, options) == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": [{"b": "c"}]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
                "a[0][b]=c",
                id="dict-inside-list-indices",
            ),
            pytest.param(
                {"a": [{"b": "c"}]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.REPEAT),
                "a[b]=c",
                id="dict-inside-list-repeat",
            ),
            pytest.param(
                {"a": [{"b": "c"}]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a[][b]=c",
                id="dict-inside-list-brackets",
            ),
            pytest.param(
                {"a": [{"b": "c"}]}, EncodeOptions(encode_values_only=True), "a[0][b]=c", id="dict-inside-list-default"
            ),
            pytest.param(
                {"a": [{"b": {"c": [1]}}]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
                "a[0][b][c][0]=1",
                id="nested-dict-list-indices",
            ),
            pytest.param(
                {"a": [{"b": {"c": [1]}}]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.REPEAT),
                "a[b][c]=1",
                id="nested-dict-list-repeat",
            ),
            pytest.param(
                {"a": [{"b": {"c": [1]}}]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a[][b][c][]=1",
                id="nested-dict-list-brackets",
            ),
            pytest.param(
                {"a": [{"b": {"c": [1]}}]},
                EncodeOptions(encode_values_only=True),
                "a[0][b][c][0]=1",
                id="nested-dict-list-default",
            ),
        ],
    )
    def test_encodes_a_dict_inside_a_list(
        self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str
    ) -> None:
        assert encode(data, options) == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": [{"b": 1}, 2, 3]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
                "a[0][b]=1&a[1]=2&a[2]=3",
                id="mixed-indices",
            ),
            pytest.param(
                {"a": [{"b": 1}, 2, 3]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a[][b]=1&a[]=2&a[]=3",
                id="mixed-brackets",
            ),
            pytest.param(
                {"a": [{"b": 1}, 2, 3]},
                EncodeOptions(encode_values_only=True),
                "a[0][b]=1&a[1]=2&a[2]=3",
                id="mixed-default",
            ),
        ],
    )
    def test_encodes_a_list_with_mixed_maps_and_primitives(
        self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str
    ) -> None:
        assert encode(data, options) == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": [{"b": "c"}]},
                EncodeOptions(allow_dots=True, encode_values_only=True, list_format=ListFormat.INDICES),
                "a[0].b=c",
                id="dots-indices-list-map",
            ),
            pytest.param(
                {"a": [{"b": "c"}]},
                EncodeOptions(allow_dots=True, encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a[].b=c",
                id="dots-brackets-list-map",
            ),
            pytest.param(
                {"a": [{"b": "c"}]},
                EncodeOptions(allow_dots=True, encode_values_only=True),
                "a[0].b=c",
                id="dots-default-list-map",
            ),
            pytest.param(
                {"a": [{"b": {"c": [1]}}]},
                EncodeOptions(allow_dots=True, encode_values_only=True, list_format=ListFormat.INDICES),
                "a[0].b.c[0]=1",
                id="dots-indices-nested",
            ),
            pytest.param(
                {"a": [{"b": {"c": [1]}}]},
                EncodeOptions(allow_dots=True, encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a[].b.c[]=1",
                id="dots-brackets-nested",
            ),
            pytest.param(
                {"a": [{"b": {"c": [1]}}]},
                EncodeOptions(allow_dots=True, encode_values_only=True),
                "a[0].b.c[0]=1",
                id="dots-default-nested",
            ),
        ],
    )
    def test_encodes_a_map_inside_a_list_with_dots_notation(
        self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str
    ) -> None:
        assert encode(data, options) == expected

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

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param({"a": ""}, None, "a=", id="empty-string"),
            pytest.param({"a": None}, EncodeOptions(strict_null_handling=True), "a", id="none-strict-null"),
            pytest.param({"a": "", "b": ""}, None, "a=&b=", id="multiple-empty"),
            pytest.param(
                {"a": None, "b": ""},
                EncodeOptions(strict_null_handling=True),
                "a&b=",
                id="none-and-empty-strict",
            ),
            pytest.param({"a": {"b": ""}}, None, "a%5Bb%5D=", id="nested-empty"),
            pytest.param(
                {"a": {"b": None}},
                EncodeOptions(strict_null_handling=True),
                "a%5Bb%5D",
                id="nested-none-strict",
            ),
            pytest.param(
                {"a": {"b": None}},
                EncodeOptions(strict_null_handling=False),
                "a%5Bb%5D=",
                id="nested-none-default",
            ),
        ],
    )
    def test_encodes_an_empty_value(
        self, data: t.Mapping[str, t.Any], options: t.Optional[EncodeOptions], expected: str
    ) -> None:
        result = encode(data) if options is None else encode(data, options)
        assert result == expected

    def test_encodes_a_null_map(self) -> None:
        obj: t.Dict[str, str] = dict()
        obj["a"] = "b"
        assert encode(obj) == "a=b"

    @pytest.mark.parametrize(
        "data, expected",
        [
            pytest.param(None, "", id="none-input"),
            pytest.param(False, "", id="false-input"),
            pytest.param("", "", id="empty-string-input"),
        ],
    )
    def test_returns_an_empty_string_for_invalid_input(self, data: t.Any, expected: str) -> None:
        assert encode(data) == expected

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

    @pytest.mark.parametrize(
        "data, expected",
        [
            pytest.param({"a": True}, "a=true", id="top-level-true"),
            pytest.param({"a": {"b": True}}, "a%5Bb%5D=true", id="nested-true"),
            pytest.param({"b": False}, "b=false", id="top-level-false"),
            pytest.param({"b": {"c": False}}, "b%5Bc%5D=false", id="nested-false"),
        ],
    )
    def test_encodes_boolean_values(self, data: t.Mapping[str, t.Any], expected: str) -> None:
        assert encode(data) == expected

    @pytest.mark.parametrize(
        "data, expected",
        [
            pytest.param({"a": b"test"}, "a=test", id="bytes-top-level"),
            pytest.param({"a": {"b": b"test"}}, "a%5Bb%5D=test", id="bytes-nested"),
        ],
    )
    def test_encodes_bytes_values(self, data: t.Mapping[str, t.Any], expected: str) -> None:
        assert encode(data) == expected

    def test_encodes_a_map_using_an_alternative_delimiter(self) -> None:
        assert encode({"a": "b", "c": "d"}, options=EncodeOptions(delimiter=";")) == "a=b;c=d"

    def test_does_not_crash_when_parsing_circular_references(self) -> None:
        a: t.Dict[str, t.Any] = dict()
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

    def test_circular_reference_at_different_position(self) -> None:
        # Create a structure where a circular reference is detected at a different position
        # than the current step, which should trigger lines 152-155 and 157 in encode.py
        a: t.Dict[str, t.Any] = {}
        b: t.Dict[str, t.Any] = {"a": a}
        c: t.Dict[str, t.Any] = {"b": b}
        a["c"] = c  # This creates a circular reference: a -> c -> b -> a

        # This should raise a ValueError with "Circular reference detected"
        with pytest.raises(ValueError, match="Circular reference detected"):
            encode({"root": a})

    def test_default_parameter_assignments(self) -> None:
        # Test default parameter assignments in _encode function (lines 133, 136, 139)
        # We need to call _encode directly with None values for prefix, comma_round_trip, and formatter
        from weakref import WeakKeyDictionary

        from qs_codec.encode import _encode

        # Create a simple value to encode
        value = {"test": "value"}

        # Call _encode with None values for prefix, comma_round_trip, and formatter
        # This should use the default values and not raise any exceptions
        result = _encode(
            value=value,
            is_undefined=False,
            side_channel=WeakKeyDictionary(),
            prefix=None,  # This will trigger line 133
            comma_round_trip=None,  # This will trigger line 136
            encoder=None,
            serialize_date=lambda dt: dt.isoformat(),
            sort=None,
            filter=None,
            formatter=None,  # This will trigger line 139
        )

        # Verify the result contains the expected key-value pair
        assert result == ["[test]=value"]

    def test_exception_in_getitem(self) -> None:
        # Test that the code handles exceptions when accessing object properties
        # This should trigger the try-except block in lines 242-246 of encode.py

        class BrokenObject:
            def __getitem__(self, key):
                # Always raise an exception
                raise Exception("Cannot access item")

            def keys(self):
                # Return a key that will trigger __getitem__
                return ["test"]

        # Create an instance of our broken object
        obj = BrokenObject()

        # Encode it - this should catch the exception and set _value_undefined = True
        result = encode({"broken": obj})

        # The result should be empty since the value is undefined
        assert result == "broken="

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

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param({"a": "b"}, EncodeOptions(filter=["a"]), "a=b", id="filter_single_key"),
            pytest.param({"a": 1}, EncodeOptions(filter=[]), "", id="filter_empty_list"),
            pytest.param(
                {"a": {"b": [1, 2, 3, 4], "c": "d"}, "c": "f"},
                EncodeOptions(filter=["a", "b", 0, 2], list_format=ListFormat.INDICES),
                "a%5Bb%5D%5B0%5D=1&a%5Bb%5D%5B2%5D=3",
                id="filter_list_indices",
            ),
            pytest.param(
                {"a": {"b": [1, 2, 3, 4], "c": "d"}, "c": "f"},
                EncodeOptions(filter=["a", "b", 0, 2], list_format=ListFormat.BRACKETS),
                "a%5Bb%5D%5B%5D=1&a%5Bb%5D%5B%5D=3",
                id="filter_list_brackets",
            ),
            pytest.param(
                {"a": {"b": [1, 2, 3, 4], "c": "d"}, "c": "f"},
                EncodeOptions(filter=["a", "b", 0, 2]),
                "a%5Bb%5D%5B0%5D=1&a%5Bb%5D%5B2%5D=3",
                id="filter_list_default",
            ),
        ],
    )
    def test_selects_properties_when_filter_is_list(
        self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str
    ) -> None:
        assert encode(data, options) == expected

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

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param({"a": "b"}, EncodeOptions(encode=False), "a=b", id="disable-encoding-simple"),
            pytest.param({"a": {"b": "c"}}, EncodeOptions(encode=False), "a[b]=c", id="disable-encoding-nested"),
            pytest.param(
                {"a": "b", "c": None},
                EncodeOptions(encode=False, strict_null_handling=True),
                "a=b&c",
                id="disable-encoding-strict-null",
            ),
        ],
    )
    def test_can_disable_uri_encoding(self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str) -> None:
        assert encode(data, options) == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": "c", "z": "y", "b": "f"},
                EncodeOptions(sort=lambda a, b: 1 if a > b else -1 if a < b else 0),
                "a=c&b=f&z=y",
                id="sort-simple",
            ),
            pytest.param(
                {"a": "c", "z": {"j": "a", "i": "b"}, "b": "f"},
                EncodeOptions(sort=lambda a, b: 1 if a > b else -1 if a < b else 0),
                "a=c&b=f&z%5Bi%5D=b&z%5Bj%5D=a",
                id="sort-nested",
            ),
        ],
    )
    def test_can_sort_the_keys(self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str) -> None:
        assert encode(data, options) == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": "a", "z": {"zj": {"zjb": "zjb", "zja": "zja"}, "zi": {"zib": "zib", "zia": "zia"}}, "b": "b"},
                EncodeOptions(sort=lambda a, b: 1 if a > b else -1 if a < b else 0, encode=False),
                "a=a&b=b&z[zi][zia]=zia&z[zi][zib]=zib&z[zj][zja]=zja&z[zj][zjb]=zjb",
                id="sort-at-depth-3-or-more",
            ),
            pytest.param(
                {"a": "a", "z": {"zj": {"zjb": "zjb", "zja": "zja"}, "zi": {"zib": "zib", "zia": "zia"}}, "b": "b"},
                EncodeOptions(encode=False),
                "a=a&z[zj][zjb]=zjb&z[zj][zja]=zja&z[zi][zib]=zib&z[zi][zia]=zia&b=b",
                id="default-order-without-sort",
            ),
        ],
    )
    def test_can_sort_the_keys_at_depth_3_or_more_too(
        self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str
    ) -> None:
        assert encode(data, options) == expected

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

    _DATE_NOW = datetime.now()
    _SPECIFIC_DATE = datetime.fromtimestamp(6)

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": _DATE_NOW},
                None,
                f'a={_DATE_NOW.isoformat().replace(":", "%3A")}',
                id="default-iso-encoding",
            ),
            pytest.param(
                {"a": _DATE_NOW},
                EncodeOptions(serialize_date=lambda d: str(int(d.timestamp()))),
                f"a={int(_DATE_NOW.timestamp())}",
                id="custom-serialize-root",
            ),
            pytest.param(
                {"a": _SPECIFIC_DATE},
                EncodeOptions(serialize_date=lambda d: str(int(d.timestamp()) * 7)),
                "a=42",
                id="custom-serialize-specific",
            ),
            pytest.param(
                {"a": [_DATE_NOW]},
                EncodeOptions(
                    serialize_date=lambda d: str(int(d.timestamp())),
                    list_format=ListFormat.COMMA,
                ),
                f"a={int(_DATE_NOW.timestamp())}",
                id="list-comma-no-roundtrip",
            ),
            pytest.param(
                {"a": [_DATE_NOW]},
                EncodeOptions(
                    serialize_date=lambda d: str(int(d.timestamp())),
                    list_format=ListFormat.COMMA,
                    comma_round_trip=True,
                ),
                f"a%5B%5D={int(_DATE_NOW.timestamp())}",
                id="list-comma-roundtrip",
            ),
        ],
    )
    def test_serialize_date_option(
        self, data: t.Mapping[str, t.Any], options: t.Optional[EncodeOptions], expected: str
    ) -> None:
        result = encode(data) if options is None else encode(data, options)
        assert result == expected

    @pytest.mark.parametrize(
        "data, expected",
        [
            pytest.param({"a": "b c"}, "a=b+c", id="space-in-value"),
            pytest.param({"a b": "c d"}, "a+b=c+d", id="space-in-key-and-value"),
            pytest.param({"a b": "a b"}, "a+b=a+b", id="space-in-key-and-value-same"),
            pytest.param({"foo(ref)": "bar"}, "foo(ref)=bar", id="parentheses-preserved"),
        ],
    )
    def test_rfc_1738_serialization(self, data: t.Mapping[str, t.Any], expected: str) -> None:
        result = encode(data, options=EncodeOptions(format=Format.RFC1738))
        assert result == expected

    @pytest.mark.parametrize(
        "data, expected",
        [
            pytest.param({"a": "b c"}, "a=b%20c", id="space-in-value"),
            pytest.param({"a b": "c d"}, "a%20b=c%20d", id="space-in-key-and-value"),
            pytest.param({"a b": "a b"}, "a%20b=a%20b", id="space-in-key-and-value-same"),
        ],
    )
    def test_rfc_3986_spaces_serialization(self, data: t.Mapping[str, t.Any], expected: str) -> None:
        result = encode(data, options=EncodeOptions(format=Format.RFC3986))
        assert result == expected

    @pytest.mark.parametrize(
        "data, expected",
        [
            pytest.param({"a": "b c"}, "a=b%20c", id="default-space-in-value"),
            pytest.param({"a b": "a b"}, "a%20b=a%20b", id="default-space-in-key-and-value"),
        ],
    )
    def test_backward_compatibility_to_rfc_3986(self, data: t.Mapping[str, t.Any], expected: str) -> None:
        assert encode(data) == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": "b", "c": ["d", "e=f"], "f": [["g"], ["h"]]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
                "a=b&c[0]=d&c[1]=e%3Df&f[0][0]=g&f[1][0]=h",
                id="values-only-indices",
            ),
            pytest.param(
                {"a": "b", "c": ["d", "e=f"], "f": [["g"], ["h"]]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a=b&c[]=d&c[]=e%3Df&f[][]=g&f[][]=h",
                id="values-only-brackets",
            ),
            pytest.param(
                {"a": "b", "c": ["d", "e=f"], "f": [["g"], ["h"]]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.REPEAT),
                "a=b&c=d&c=e%3Df&f=g&f=h",
                id="values-only-repeat",
            ),
            pytest.param(
                {"a": "b", "c": ["d", "e"], "f": [["g"], ["h"]]},
                EncodeOptions(list_format=ListFormat.INDICES),
                "a=b&c%5B0%5D=d&c%5B1%5D=e&f%5B0%5D%5B0%5D=g&f%5B1%5D%5B0%5D=h",
                id="list-format-indices",
            ),
            pytest.param(
                {"a": "b", "c": ["d", "e"], "f": [["g"], ["h"]]},
                EncodeOptions(list_format=ListFormat.BRACKETS),
                "a=b&c%5B%5D=d&c%5B%5D=e&f%5B%5D%5B%5D=g&f%5B%5D%5B%5D=h",
                id="list-format-brackets",
            ),
            pytest.param(
                {"a": "b", "c": ["d", "e"], "f": [["g"], ["h"]]},
                EncodeOptions(list_format=ListFormat.REPEAT),
                "a=b&c=d&c=e&f=g&f=h",
                id="list-format-repeat",
            ),
        ],
    )
    def test_encode_values_only_and_list_formats(
        self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str
    ) -> None:
        assert encode(data, options) == expected

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

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": "æ"},
                EncodeOptions(charset_sentinel=True, charset=Charset.UTF8),
                "utf8=%E2%9C%93&a=%C3%A6",
                id="sentinel-utf8",
            ),
            pytest.param(
                {"a": "æ"},
                EncodeOptions(charset_sentinel=True, charset=Charset.LATIN1),
                "utf8=%26%2310003%3B&a=%E6",
                id="sentinel-latin1",
            ),
        ],
    )
    def test_charset_sentinel_option(self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str) -> None:
        assert encode(data, options) == expected

    def test_charset_sentinel_with_invalid_charset(self) -> None:
        # Create a custom EncodeOptions with an invalid charset
        options = EncodeOptions(charset_sentinel=True)
        # Set the charset to an invalid value (not UTF8 or LATIN1)
        options.charset = None  # type: ignore

        # This should raise a ValueError
        with pytest.raises(ValueError, match="Invalid charset"):
            encode({"a": "test"}, options)

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

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            # object without list
            pytest.param(
                {"a": {"b": {"c": "d", "e": "f"}}}, EncodeOptions(encode=False), "a[b][c]=d&a[b][e]=f", id="obj-default"
            ),
            pytest.param(
                {"a": {"b": {"c": "d", "e": "f"}}},
                EncodeOptions(encode=False, list_format=ListFormat.BRACKETS),
                "a[b][c]=d&a[b][e]=f",
                id="obj-brackets",
            ),
            pytest.param(
                {"a": {"b": {"c": "d", "e": "f"}}},
                EncodeOptions(encode=False, list_format=ListFormat.INDICES),
                "a[b][c]=d&a[b][e]=f",
                id="obj-indices",
            ),
            pytest.param(
                {"a": {"b": {"c": "d", "e": "f"}}},
                EncodeOptions(encode=False, list_format=ListFormat.REPEAT),
                "a[b][c]=d&a[b][e]=f",
                id="obj-repeat",
            ),
            pytest.param(
                {"a": {"b": {"c": "d", "e": "f"}}},
                EncodeOptions(encode=False, list_format=ListFormat.COMMA),
                "a[b][c]=d&a[b][e]=f",
                id="obj-comma",
            ),
            # object with list
            pytest.param(
                {"a": {"b": [{"c": "d", "e": "f"}]}},
                EncodeOptions(encode=False),
                "a[b][0][c]=d&a[b][0][e]=f",
                id="with-list-default",
            ),
            pytest.param(
                {"a": {"b": [{"c": "d", "e": "f"}]}},
                EncodeOptions(encode=False, list_format=ListFormat.BRACKETS),
                "a[b][][c]=d&a[b][][e]=f",
                id="with-list-brackets",
            ),
            pytest.param(
                {"a": {"b": [{"c": "d", "e": "f"}]}},
                EncodeOptions(encode=False, list_format=ListFormat.INDICES),
                "a[b][0][c]=d&a[b][0][e]=f",
                id="with-list-indices",
            ),
            pytest.param(
                {"a": {"b": [{"c": "d", "e": "f"}]}},
                EncodeOptions(encode=False, list_format=ListFormat.REPEAT),
                "a[b][c]=d&a[b][e]=f",
                id="with-list-repeat",
            ),
        ],
    )
    def test_objects_inside_lists(self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str) -> None:
        assert encode(data, options) == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": [None, "2", None, None, "1"]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
                "a[0]=&a[1]=2&a[2]=&a[3]=&a[4]=1",
                id="nulls-indices",
            ),
            pytest.param(
                {"a": [None, "2", None, None, "1"]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a[]=&a[]=2&a[]=&a[]=&a[]=1",
                id="nulls-brackets",
            ),
            pytest.param(
                {"a": [None, "2", None, None, "1"]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.REPEAT),
                "a=&a=2&a=&a=&a=1",
                id="nulls-repeat",
            ),
            pytest.param(
                {"a": [None, {"b": [None, None, {"c": "1"}]}]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
                "a[0]=&a[1][b][0]=&a[1][b][1]=&a[1][b][2][c]=1",
                id="nested-b-null-indices",
            ),
            pytest.param(
                {"a": [None, {"b": [None, None, {"c": "1"}]}]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a[]=&a[][b][]=&a[][b][]=&a[][b][][c]=1",
                id="nested-b-null-brackets",
            ),
            pytest.param(
                {"a": [None, {"b": [None, None, {"c": "1"}]}]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.REPEAT),
                "a=&a[b]=&a[b]=&a[b][c]=1",
                id="nested-b-null-repeat",
            ),
            pytest.param(
                {"a": [None, [None, [None, None, {"c": "1"}]]]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
                "a[0]=&a[1][0]=&a[1][1][0]=&a[1][1][1]=&a[1][1][2][c]=1",
                id="deep-nested-indices",
            ),
            pytest.param(
                {"a": [None, [None, [None, None, {"c": "1"}]]]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a[]=&a[][]=&a[][][]=&a[][][]=&a[][][][c]=1",
                id="deep-nested-brackets",
            ),
            pytest.param(
                {"a": [None, [None, [None, None, {"c": "1"}]]]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.REPEAT),
                "a=&a=&a=&a=&a[c]=1",
                id="deep-nested-repeat",
            ),
        ],
    )
    def test_encodes_lists_with_nulls(self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str) -> None:
        assert encode(data, options) == expected

    def test_encodes_url(self) -> None:
        assert (
            encode(
                {"url": "https://example.com?foo=bar&baz=qux"},
                options=EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
            )
            == "url=https%3A%2F%2Fexample.com%3Ffoo%3Dbar%26baz%3Dqux"
        )

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {
                    "filters": {
                        r"$or": [
                            {"date": {r"$eq": "2020-01-01"}},
                            {"date": {r"$eq": "2020-01-02"}},
                        ],
                        "author": {"name": {r"$eq": "John doe"}},
                    },
                },
                EncodeOptions(encode=False, list_format=ListFormat.BRACKETS),
                r"filters[$or][][date][$eq]=2020-01-01&filters[$or][][date][$eq]=2020-01-02&filters[author][name][$eq]=John doe",
                id="spatie-dict-no-encode",
            ),
            pytest.param(
                {
                    "filters": {
                        r"$or": [
                            {"date": {r"$eq": "2020-01-01"}},
                            {"date": {r"$eq": "2020-01-02"}},
                        ],
                        "author": {"name": {r"$eq": "John doe"}},
                    },
                },
                EncodeOptions(list_format=ListFormat.BRACKETS),
                "filters%5B%24or%5D%5B%5D%5Bdate%5D%5B%24eq%5D=2020-01-01&filters%5B%24or%5D%5B%5D%5Bdate%5D%5B%24eq%5D=2020-01-02&filters%5Bauthor%5D%5Bname%5D%5B%24eq%5D=John%20doe",
                id="spatie-dict-encode",
            ),
        ],
    )
    def test_encodes_spatie_dict(self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str) -> None:
        assert encode(data, options) == expected


class TestEncodesAListValueWithOneItemVsMultipleItems:

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": "c"},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
                "a=c",
                id="values-only-indices",
            ),
            pytest.param(
                {"a": "c"},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a=c",
                id="values-only-brackets",
            ),
            pytest.param(
                {"a": "c"},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.COMMA),
                "a=c",
                id="values-only-comma",
            ),
            pytest.param({"a": "c"}, EncodeOptions(encode_values_only=True), "a=c", id="values-only-default"),
        ],
    )
    def test_non_list_item(self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str) -> None:
        assert encode(data, options) == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": ["c"]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
                "a[0]=c",
                id="single-item-indices",
            ),
            pytest.param(
                {"a": ["c"]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a[]=c",
                id="single-item-brackets",
            ),
            pytest.param(
                {"a": ["c"]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.COMMA),
                "a=c",
                id="single-item-comma",
            ),
            pytest.param(
                {"a": ["c"]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.COMMA, comma_round_trip=True),
                "a[]=c",
                id="single-item-comma-roundtrip",
            ),
            pytest.param({"a": ["c"]}, EncodeOptions(encode_values_only=True), "a[0]=c", id="single-item-default"),
        ],
    )
    def test_list_with_a_single_item(self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str) -> None:
        assert encode(data, options) == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": ["c", "d"]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.INDICES),
                "a[0]=c&a[1]=d",
                id="multiple-items-indices",
            ),
            pytest.param(
                {"a": ["c", "d"]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.BRACKETS),
                "a[]=c&a[]=d",
                id="multiple-items-brackets",
            ),
            pytest.param(
                {"a": ["c", "d"]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.COMMA),
                "a=c,d",
                id="multiple-items-comma",
            ),
            pytest.param(
                {"a": ["c", "d"]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.COMMA, comma_round_trip=True),
                "a=c,d",
                id="multiple-items-comma-roundtrip",
            ),
            pytest.param(
                {"a": ["c", "d"]}, EncodeOptions(encode_values_only=True), "a[0]=c&a[1]=d", id="multiple-items-default"
            ),
        ],
    )
    def test_list_with_multiple_items(self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str) -> None:
        assert encode(data, options) == expected

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param(
                {"a": ["c,d", "e"]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.COMMA),
                "a=c%2Cd,e",
                id="values-only-comma-no-roundtrip",
            ),
            pytest.param(
                {"a": ["c,d", "e"]},
                EncodeOptions(list_format=ListFormat.COMMA),
                "a=c%2Cd%2Ce",
                id="default-comma-no-roundtrip",
            ),
            pytest.param(
                {"a": ["c,d", "e"]},
                EncodeOptions(encode_values_only=True, list_format=ListFormat.COMMA, comma_round_trip=True),
                "a=c%2Cd,e",
                id="values-only-comma-roundtrip",
            ),
            pytest.param(
                {"a": ["c,d", "e"]},
                EncodeOptions(list_format=ListFormat.COMMA, comma_round_trip=True),
                "a=c%2Cd%2Ce",
                id="default-comma-roundtrip",
            ),
        ],
    )
    def test_list_with_multiple_items_with_a_comma_inside(
        self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str
    ) -> None:
        assert encode(data, options) == expected


class TestEncodesAListInDifferentListFormats:
    def test_default_parameters(self) -> None:
        assert encode({"a": [], "b": [None], "c": "c"}, options=EncodeOptions(encode=False)) == "b[0]=&c=c"

    @pytest.mark.parametrize(
        "options, expected",
        [
            pytest.param(EncodeOptions(encode=False), "b[0]=&c=c", id="default"),
            pytest.param(EncodeOptions(encode=False, list_format=ListFormat.INDICES), "b[0]=&c=c", id="indices"),
            pytest.param(EncodeOptions(encode=False, list_format=ListFormat.BRACKETS), "b[]=&c=c", id="brackets"),
            pytest.param(EncodeOptions(encode=False, list_format=ListFormat.REPEAT), "b=&c=c", id="repeat"),
            pytest.param(EncodeOptions(encode=False, list_format=ListFormat.COMMA), "b=&c=c", id="comma"),
            pytest.param(
                EncodeOptions(encode=False, list_format=ListFormat.COMMA, comma_round_trip=True),
                "b[]=&c=c",
                id="comma-roundtrip",
            ),
        ],
    )
    def test_list_format_default(self, options: EncodeOptions, expected: str) -> None:
        data: t.Mapping[str, t.Any] = {"a": [], "b": [None], "c": "c"}
        assert encode(data, options) == expected

    @pytest.mark.parametrize(
        "options, expected",
        [
            pytest.param(
                EncodeOptions(encode=False, list_format=ListFormat.BRACKETS, strict_null_handling=True),
                "b[]&c=c",
                id="brackets-strict-null",
            ),
            pytest.param(
                EncodeOptions(encode=False, list_format=ListFormat.REPEAT, strict_null_handling=True),
                "b&c=c",
                id="repeat-strict-null",
            ),
            pytest.param(
                EncodeOptions(encode=False, list_format=ListFormat.COMMA, strict_null_handling=True),
                "b&c=c",
                id="comma-strict-null",
            ),
            pytest.param(
                EncodeOptions(
                    encode=False, list_format=ListFormat.COMMA, strict_null_handling=True, comma_round_trip=True
                ),
                "b[]&c=c",
                id="comma-roundtrip-strict-null",
            ),
        ],
    )
    def test_with_strict_null_handling(self, options: EncodeOptions, expected: str) -> None:
        data: t.Mapping[str, t.Any] = {"a": [], "b": [None], "c": "c"}
        assert encode(data, options) == expected

    @pytest.mark.parametrize(
        "options, expected",
        [
            pytest.param(
                EncodeOptions(encode=False, list_format=ListFormat.INDICES, skip_nulls=True),
                "c=c",
                id="indices-skip-nulls",
            ),
            pytest.param(
                EncodeOptions(encode=False, list_format=ListFormat.BRACKETS, skip_nulls=True),
                "c=c",
                id="brackets-skip-nulls",
            ),
            pytest.param(
                EncodeOptions(encode=False, list_format=ListFormat.REPEAT, skip_nulls=True),
                "c=c",
                id="repeat-skip-nulls",
            ),
            pytest.param(
                EncodeOptions(encode=False, list_format=ListFormat.COMMA, skip_nulls=True), "c=c", id="comma-skip-nulls"
            ),
        ],
    )
    def test_with_skip_nulls(self, options: EncodeOptions, expected: str) -> None:
        data: t.Mapping[str, t.Any] = {"a": [], "b": [None], "c": "c"}
        assert encode(data, options) == expected


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

    @pytest.mark.parametrize(
        "data, options, expected",
        [
            pytest.param({"": {"": [2, 3]}}, EncodeOptions(encode=False), "[][0]=2&[][1]=3", id="default-empty-keys"),
            pytest.param(
                {"": {"": [2, 3], "a": 2}},
                EncodeOptions(encode=False),
                "[][0]=2&[][1]=3&[a]=2",
                id="default-empty-keys-with-extra",
            ),
            pytest.param(
                {"": {"": [2, 3]}},
                EncodeOptions(encode=False, list_format=ListFormat.INDICES),
                "[][0]=2&[][1]=3",
                id="indices-empty-keys",
            ),
            pytest.param(
                {"": {"": [2, 3], "a": 2}},
                EncodeOptions(encode=False, list_format=ListFormat.INDICES),
                "[][0]=2&[][1]=3&[a]=2",
                id="indices-empty-keys-with-extra",
            ),
        ],
    )
    def test_edge_case_with_map_lists(self, data: t.Mapping[str, t.Any], options: EncodeOptions, expected: str) -> None:
        assert encode(data, options) == expected


class TestEncodeNonStrings:
    def test_encodes_a_null_value(self) -> None:
        assert encode({"a": None}) == "a="

    @pytest.mark.parametrize(
        "data, expected",
        [
            pytest.param({"a": True}, "a=true", id="true-value"),
            pytest.param({"a": False}, "a=false", id="false-value"),
        ],
    )
    def test_encodes_a_boolean_value(self, data: t.Mapping[str, t.Any], expected: str) -> None:
        assert encode(data) == expected

    @pytest.mark.parametrize(
        "data, expected",
        [
            pytest.param({"a": 0}, "a=0", id="integer-zero"),
            pytest.param({"a": 1}, "a=1", id="integer-one"),
            pytest.param({"a": 1.1}, "a=1.1", id="float"),
        ],
    )
    def test_encodes_a_number_value(self, data: t.Mapping[str, t.Any], expected: str) -> None:
        assert encode(data) == expected

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
        obj: t.Mapping[str, t.Any] = {"a": {}}
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

    def test_encodes_non_string_keys(self) -> None:
        assert (
            encode(
                {"a": "b", False: {}},
                options=EncodeOptions(filter=["a", False, None], allow_dots=True, encode_dot_in_keys=True),
            )
            == "a=b"
        )
