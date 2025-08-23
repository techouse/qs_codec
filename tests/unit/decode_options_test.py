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


class TestAllowDotsDecodeDotInKeysInterplay:
    def test_constructor_invalid_combination_throws(self) -> None:
        import pytest

        with pytest.raises((ValueError, AssertionError, TypeError)):
            DecodeOptions(decode_dot_in_keys=True, allow_dots=False)


class TestDefaultDecodeKeyEncodedDots:
    def test_key_maps_2e_inside_brackets_allowdots_true(self) -> None:
        for cs in (Charset.UTF8, Charset.LATIN1):
            opts = DecodeOptions(allow_dots=True, charset=cs)
            assert opts.decoder("a[%2E]", cs, kind=DecodeKind.KEY) == "a[.]"
            assert opts.decoder("a[%2e]", cs, kind=DecodeKind.KEY) == "a[.]"

    def test_key_maps_2e_outside_brackets_allowdots_true_independent_of_decodeopt(self) -> None:
        for cs in (Charset.UTF8, Charset.LATIN1):
            opts1 = DecodeOptions(allow_dots=True, decode_dot_in_keys=False, charset=cs)
            opts2 = DecodeOptions(allow_dots=True, decode_dot_in_keys=True, charset=cs)
            assert opts1.decoder("a%2Eb", cs, kind=DecodeKind.KEY) == "a.b"
            assert opts2.decoder("a%2Eb", cs, kind=DecodeKind.KEY) == "a.b"

    def test_non_key_decodes_2e_to_dot_control(self) -> None:
        for cs in (Charset.UTF8, Charset.LATIN1):
            opts = DecodeOptions(allow_dots=True, charset=cs)
            assert opts.decoder("a%2Eb", cs, kind=DecodeKind.VALUE) == "a.b"

    def test_key_maps_2e_inside_brackets_allowdots_false(self) -> None:
        for cs in (Charset.UTF8, Charset.LATIN1):
            opts = DecodeOptions(allow_dots=False, charset=cs)
            assert opts.decoder("a[%2E]", cs, kind=DecodeKind.KEY) == "a[.]"
            assert opts.decoder("a[%2e]", cs, kind=DecodeKind.KEY) == "a[.]"

    def test_key_outside_2e_decodes_to_dot_allowdots_false(self) -> None:
        for cs in (Charset.UTF8, Charset.LATIN1):
            opts = DecodeOptions(allow_dots=False, charset=cs)
            assert opts.decoder("a%2Eb", cs, kind=DecodeKind.KEY) == "a.b"
            assert opts.decoder("a%2eb", cs, kind=DecodeKind.KEY) == "a.b"


class TestCustomDecoderBehavior:
    def test_decode_key_decodes_percent_sequences_like_values_when_decode_dot_in_keys_false(self) -> None:
        opts = DecodeOptions(allow_dots=True, decode_dot_in_keys=False)
        assert opts.decoder("a%2Eb", Charset.UTF8, kind=DecodeKind.KEY) == "a.b"
        assert opts.decoder("a%2eb", Charset.UTF8, kind=DecodeKind.KEY) == "a.b"

    def test_decode_value_decodes_percent_sequences_normally(self) -> None:
        opts = DecodeOptions()
        assert opts.decoder("%2E", Charset.UTF8, kind=DecodeKind.VALUE) == "."

    def test_decoder_is_used_for_key_and_value(self) -> None:
        calls: t.List[t.Tuple[t.Optional[str], DecodeKind]] = []

        def dec(s: t.Optional[str], charset: t.Optional[Charset], kind: DecodeKind) -> t.Optional[str]:  # type: ignore[override]
            calls.append((s, kind))
            return s

        opts = DecodeOptions(decoder=dec)
        assert opts.decoder("x", Charset.UTF8, kind=DecodeKind.KEY) == "x"
        assert opts.decoder("y", Charset.UTF8, kind=DecodeKind.VALUE) == "y"

        assert len(calls) == 2
        assert calls[0][1] is DecodeKind.KEY and calls[0][0] == "x"
        assert calls[1][1] is DecodeKind.VALUE and calls[1][0] == "y"

    def test_decoder_null_return_is_honored(self) -> None:
        def dec(s: t.Optional[str], charset: t.Optional[Charset], kind: DecodeKind) -> t.Optional[str]:  # type: ignore[override]
            return None

        opts = DecodeOptions(decoder=dec)
        assert opts.decoder("foo", Charset.UTF8, kind=DecodeKind.VALUE) is None
        assert opts.decoder("bar", Charset.UTF8, kind=DecodeKind.KEY) is None

    def test_single_decoder_acts_like_legacy_when_ignoring_kind(self) -> None:
        def dec(s: t.Optional[str], *args, **kwargs):  # type: ignore[no-untyped-def]
            return None if s is None else s.upper()

        opts = DecodeOptions(decoder=dec)
        assert opts.decoder("abc", Charset.UTF8, kind=DecodeKind.VALUE) == "ABC"
        # For keys, custom decoder gets the raw token; no default percent-decoding happens first.
        assert opts.decoder("a%2Eb", Charset.UTF8, kind=DecodeKind.KEY) == "A%2EB"

    def test_decoder_wins_over_legacy_decoder_when_both_provided(self) -> None:
        # decoder must take precedence over legacy_decoder (parity with Kotlin/C#)
        def legacy(v: t.Optional[str], charset: t.Optional[Charset] = None) -> t.Optional[str]:
            return f"L:{'null' if v is None else v}"

        def dec(
            v: t.Optional[str],
            charset: t.Optional[Charset] = None,
            *,
            kind: DecodeKind = DecodeKind.VALUE,
        ) -> t.Optional[str]:
            return f"K:{kind.name}:{'null' if v is None else v}"

        opts = DecodeOptions(decoder=dec, legacy_decoder=legacy)
        assert opts.decode_key("x") == "K:KEY:x"
        assert opts.decode_value("y") == "K:VALUE:y"

    def test_decode_key_coerces_non_string_decoder_result(self) -> None:
        # When the decoder returns a non-string scalar, decode_key coerces it via str()
        def dec(
            v: t.Optional[str],
            charset: t.Optional[Charset] = None,
            *,
            kind: DecodeKind = DecodeKind.VALUE,
        ) -> t.Any:
            return 42 if v is not None else None

        opts = DecodeOptions(decoder=dec)
        assert opts.decode_key("anything") == "42"
