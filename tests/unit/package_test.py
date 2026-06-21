import qs_codec
import qs_codec.enums.sentinel as sentinel_module
import qs_codec.models.undefined as undefined_module


def test_sentinel_is_part_of_the_public_api():
    assert "Sentinel" in qs_codec.__all__
    assert qs_codec.Sentinel is sentinel_module.Sentinel


def test_undefined_is_not_part_of_the_public_api():
    assert "Undefined" not in qs_codec.__all__
    assert not hasattr(qs_codec, "Undefined")


def test_sentinel_modules_define_their_intended_exports():
    assert sentinel_module.__all__ == ("Sentinel",)
    assert undefined_module.__all__ == ()
