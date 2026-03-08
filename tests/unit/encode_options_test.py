import pytest

from qs_codec import Charset, EncodeOptions, Format, ListFormat
from qs_codec.utils.encode_utils import EncodeUtils


class TestEncodeOptions:
    def test_post_init_restores_default_encoder(self) -> None:
        opts = EncodeOptions()
        left = getattr(opts._encoder, "__func__", None)
        right = getattr(EncodeUtils.encode, "__func__", None)
        assert left is not None and right is not None
        assert left is right

    def test_post_init_recovers_when_encoder_missing(self) -> None:
        opts = EncodeOptions()
        _ = opts.encoder
        delattr(opts, "_encoder")
        EncodeOptions.__post_init__(opts)
        left = getattr(opts._encoder, "__func__", None)
        right = getattr(EncodeUtils.encode, "__func__", None)
        assert left is not None and right is not None
        assert left is right

    def test_encoder_getter_does_not_persist_runtime_cache_on_options(self) -> None:
        opts = EncodeOptions()
        first = opts.encoder
        second = opts.encoder

        assert first is not second
        assert "_bound_encoder" not in vars(opts)
        assert "_bound_encoder_cache_key" not in vars(opts)

    def test_encoder_getter_reflects_charset_or_format_change(self) -> None:
        def custom_encoder(value, charset=None, format=None):  # type: ignore[no-untyped-def]
            charset_name = charset.name if charset is not None else "none"
            format_name = format.format_name if format is not None else "none"
            return f"{value}|{charset_name}|{format_name}"

        opts = EncodeOptions()
        opts.encoder = custom_encoder

        first = opts.encoder
        assert first("x") == "x|UTF8|RFC3986"

        opts.charset = Charset.LATIN1
        second = opts.encoder
        assert second("x") == "x|LATIN1|RFC3986"

        opts.format = Format.RFC1738
        third = opts.encoder
        assert third("x") == "x|LATIN1|RFC1738"

    def test_encoder_getter_reflects_raw_encoder_change(self) -> None:
        def left_encoder(value, charset=None, format=None):  # type: ignore[no-untyped-def]
            _ = charset
            _ = format
            return f"left:{value}"

        def right_encoder(value, charset=None, format=None):  # type: ignore[no-untyped-def]
            _ = charset
            _ = format
            return f"right:{value}"

        opts = EncodeOptions()
        opts.encoder = left_encoder
        first = opts.encoder

        opts.encoder = right_encoder
        second = opts.encoder

        assert first("x") == "left:x"
        assert second("x") == "right:x"

    def test_equality_with_other_type_returns_false(self) -> None:
        opts = EncodeOptions()
        assert opts != object()

    def test_equality_treats_equivalent_options_as_equal(self) -> None:
        assert EncodeOptions() == EncodeOptions()

    def test_equality_ignores_encoder_property_access(self) -> None:
        lhs = EncodeOptions()
        rhs = EncodeOptions()

        _ = lhs.encoder
        assert lhs == rhs

        _ = rhs.encoder
        assert lhs == rhs

    def test_equality_detects_field_difference(self) -> None:
        lhs = EncodeOptions()
        rhs = EncodeOptions(allow_dots=True)
        assert lhs != rhs

    @pytest.mark.parametrize(
        "indices, expected",
        [
            pytest.param(True, ListFormat.INDICES, id="indices-true"),
            pytest.param(False, ListFormat.REPEAT, id="indices-false"),
        ],
    )
    def test_indices_normalizes_to_list_format(self, indices: bool, expected: ListFormat) -> None:
        assert EncodeOptions(indices=indices).list_format is expected

    def test_max_depth_must_be_positive(self) -> None:
        for value in (0, -1, True, 1.5):
            with pytest.raises(ValueError, match="max_depth must be a positive integer or None"):
                EncodeOptions(max_depth=value)  # type: ignore[arg-type]

        assert EncodeOptions(max_depth=5).max_depth == 5
