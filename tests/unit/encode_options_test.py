from qs_codec import EncodeOptions
from qs_codec.utils.encode_utils import EncodeUtils


class TestEncodeOptions:
    def test_post_init_restores_default_encoder(self) -> None:
        opts = EncodeOptions()
        assert opts._encoder.__func__ is EncodeUtils.encode.__func__

    def test_post_init_recovers_when_encoder_missing(self) -> None:
        opts = EncodeOptions()
        delattr(opts, "_encoder")
        EncodeOptions.__post_init__(opts)
        assert opts._encoder.__func__ is EncodeUtils.encode.__func__

    def test_equality_with_other_type_returns_false(self) -> None:
        opts = EncodeOptions()
        assert opts != object()

    def test_equality_detects_field_difference(self) -> None:
        lhs = EncodeOptions()
        rhs = EncodeOptions(allow_dots=True)
        assert lhs != rhs
