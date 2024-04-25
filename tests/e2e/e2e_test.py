import typing as t

import pytest

from qs_codec import EncodeOptions, decode, encode


class TestE2E:
    @pytest.mark.parametrize(
        "data, encoded",
        [
            ({}, ""),
            ({"a": "b"}, "a=b"),
            ({"a": "b", "c": "d"}, "a=b&c=d"),
            ({"a": "b", "c": "d", "e": "f"}, "a=b&c=d&e=f"),
            ({"a": "b", "c": "d", "e": ["f", "g", "h"]}, "a=b&c=d&e[0]=f&e[1]=g&e[2]=h"),
            (
                {"a": "b", "c": "d", "e": ["f", "g", "h"], "i": {"j": "k", "l": "m"}},
                "a=b&c=d&e[0]=f&e[1]=g&e[2]=h&i[j]=k&i[l]=m",
            ),
            (
                {
                    "filters": {
                        r"$or": [
                            {
                                "date": {
                                    r"$eq": "2020-01-01",
                                }
                            },
                            {
                                "date": {
                                    r"$eq": "2020-01-02",
                                }
                            },
                        ],
                        "author": {
                            "name": {
                                r"$eq": "John Doe",
                            },
                        },
                    }
                },
                r"filters[$or][0][date][$eq]=2020-01-01&filters[$or][1][date][$eq]=2020-01-02&filters[author][name][$eq]=John Doe",
            ),
        ],
    )
    def test_e2e(self, data: t.Mapping, encoded: str):
        assert encode(data, EncodeOptions(encode=False)) == encoded
        assert decode(encoded) == data
