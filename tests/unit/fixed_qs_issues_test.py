import typing as t

from qs_codec import EncodeOptions, decode, encode


class TestFixedQsIssues:
    """Test cases for fixed issues."""

    def test_qs_issue_493(self) -> None:
        """Test case for https://github.com/ljharb/qs/issues/493"""
        original: t.Dict[str, t.Any] = {"search": {"withbracket[]": "foobar"}}
        encoded: str = "search[withbracket[]]=foobar"
        assert encode(original, options=EncodeOptions(encode=False)) == encoded
        assert decode(encoded) == original
