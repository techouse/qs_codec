"""Decoding context used by the query string parser and utilities.

This enum indicates whether a given piece of text is being decoded as a *key*
(or key segment) or as a *value*. Note that the built-in scalar decoder
(`qs_codec.utils.decode_utils.decode`) ignores `kind` and fully percent-decodes
dots; preservation of encoded dots for splitting is applied later by parser
options (`allow_dots`, `decode_dot_in_keys`).
"""

from enum import Enum


class DecodeKind(str, Enum):
    """Decoding context for query string tokens.

    Attributes
    ----------
    KEY
        Decode a *key* (or key segment). Note that the default scalar decoder
        (``qs_codec.utils.decode_utils.decode``) ignores `kind` and fully
        decodes percent-encoded dots (``%2E``/``%2e``). Dot-splitting behavior is
        applied later by higher-level parser options.
    VALUE
        Decode a *value*. Implementations typically perform full percent decoding.
    """

    KEY = "key"  # Key/segment decode; preserve encoded dots for later splitting logic
    VALUE = "value"  # Value decode; fully percent-decode


__all__ = ["DecodeKind"]
