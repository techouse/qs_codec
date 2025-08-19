import typing as t

import pytest

from qs_codec import Charset, DecodeOptions
from qs_codec.enums.decode_kind import DecodeKind
from qs_codec.utils.decode_utils import DecodeUtils


class TestDecodeOptionsPostInitDefaults:
    def test_defaults_normalize(self) -> None:
        opts = DecodeOptions()
        assert opts.decode_dot_in_keys is False
        assert opts.allow_dots is False

    def test_decode_dot_implies_allow_dots(self) -> None:
        opts = DecodeOptions(decode_dot_in_keys=True)
        assert opts.allow_dots is True

    def test_invariant_violation_raises(self) -> None:
        with pytest.raises(ValueError):
            DecodeOptions(decode_dot_in_keys=True, allow_dots=False)


class TestDecodeOptionsDecoderDefault:
    def test_default_decoder_behaves_like_decodeutils(self) -> None:
        # The adapter may wrap the default, so compare behavior rather than identity.
        opts = DecodeOptions()
        s = "a+b%2E"
        out_key = opts.decoder(s, Charset.UTF8, kind=DecodeKind.KEY)
        out_val = opts.decoder(s, Charset.UTF8, kind=DecodeKind.VALUE)
        assert out_key == DecodeUtils.decode(s, charset=Charset.UTF8, kind=DecodeKind.KEY)
        assert out_val == DecodeUtils.decode(s, charset=Charset.UTF8, kind=DecodeKind.VALUE)


class TestDecoderAdapterSignatures:
    def test_legacy_single_arg(self) -> None:
        calls: t.List[t.Tuple[t.Optional[str]]] = []

        def dec(s: t.Optional[str]) -> t.Optional[str]:
            calls.append((s,))
            return None if s is None else s.upper()

        opts = DecodeOptions(decoder=dec)
        assert opts.decoder("x", Charset.UTF8, kind=DecodeKind.KEY) == "X"
        assert calls == [("x",)]

    def test_two_args_s_charset(self) -> None:
        seen: t.List[t.Tuple[t.Optional[str], t.Optional[Charset]]] = []

        def dec(s: t.Optional[str], charset: t.Optional[Charset]) -> t.Optional[str]:
            seen.append((s, charset))
            # Echo string and charset name to prove we passed it
            return None if s is None else f"{s}|{charset.name if charset else 'NONE'}"

        opts = DecodeOptions(decoder=dec)
        assert opts.decoder("hi", Charset.LATIN1, kind=DecodeKind.VALUE) == "hi|LATIN1"
        assert seen == [("hi", Charset.LATIN1)]

    def test_three_args_kind_enum_annotation(self) -> None:
        seen: t.List[t.Any] = []

        def dec(s: t.Optional[str], charset: t.Optional[Charset], kind: DecodeKind) -> t.Optional[str]:
            seen.append(kind)
            # return a marker showing what we received
            return None if s is None else f"K:{'E' if isinstance(kind, DecodeKind) else type(kind).__name__}"

        opts = DecodeOptions(decoder=dec)
        assert opts.decoder("z", Charset.UTF8, kind=DecodeKind.KEY) == "K:E"
        assert seen and isinstance(seen[0], DecodeKind) and seen[0] is DecodeKind.KEY

    def test_three_args_kind_str_annotation(self) -> None:
        seen: t.List[t.Any] = []

        def dec(s: t.Optional[str], charset: t.Optional[Charset], kind: str) -> t.Optional[str]:
            seen.append(kind)
            return None if s is None else kind  # echo back

        opts = DecodeOptions(decoder=dec)
        assert opts.decoder("z", Charset.UTF8, kind=DecodeKind.KEY) == "key"
        assert seen == ["key"]

    def test_kwonly_kind_str(self) -> None:
        seen: t.List[t.Any] = []

        def dec(s: t.Optional[str], charset: t.Optional[Charset], *, kind: str) -> t.Optional[str]:
            seen.append(kind)
            return None if s is None else kind

        opts = DecodeOptions(decoder=dec)
        assert opts.decoder("z", Charset.UTF8, kind=DecodeKind.VALUE) == "value"
        assert seen == ["value"]

    def test_varargs_kwargs_receives_kind_string(self) -> None:
        seen: t.List[t.Any] = []

        def dec(s: t.Optional[str], *args, **kwargs) -> t.Optional[str]:  # type: ignore[no-untyped-def]
            seen.append(kwargs.get("kind"))
            return s

        opts = DecodeOptions(decoder=dec)
        assert opts.decoder("ok", Charset.UTF8, kind=DecodeKind.KEY) == "ok"
        assert seen == ["key"]

    def test_user_decoder_typeerror_is_not_swallowed(self) -> None:
        def dec(s: t.Optional[str]) -> t.Optional[str]:
            raise TypeError("boom")

        opts = DecodeOptions(decoder=dec)
        with pytest.raises(TypeError):
            _ = opts.decoder("oops", Charset.UTF8, kind=DecodeKind.KEY)


class TestParserStateIsolation:
    def test_parse_lists_toggle_does_not_leak_across_calls(self) -> None:
        # Construct a query with many top-level params to trigger the internal optimization
        big_query = "&".join(f"k{i}=v{i}" for i in range(25))
        opts = DecodeOptions(list_limit=20)

        # First call may temporarily disable parse_lists internally
        from qs_codec import decode

        res1 = decode(big_query, opts)
        assert isinstance(res1, dict) and len(res1) == 25
        # The option should be restored on the options object
        assert opts.parse_lists is True

        # Second call should still parse lists as lists
        res2 = decode("a[]=1&a[]=2", opts)
        assert res2 == {"a": ["1", "2"]}
