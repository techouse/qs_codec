import typing as t

import pytest

from qs_codec.enums.list_format import ListFormatGenerator


@pytest.mark.parametrize(
    "generator, prefix, key, expected",
    [
        (ListFormatGenerator.brackets, "a", None, "a[]"),
        (ListFormatGenerator.comma, "a", "0", "a"),
        (ListFormatGenerator.indices, "a", "0", "a[0]"),
        (ListFormatGenerator.repeat, "a", "0", "a"),
    ],
)
def test_list_format_generators(
    generator: t.Callable[[str, t.Optional[str]], str], prefix: str, key: t.Optional[str], expected: str
) -> None:
    assert generator(prefix, key) == expected
