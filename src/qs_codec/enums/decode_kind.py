"""Decoding context used by the query string parser and utilities.

This enum indicates whether a given piece of text is being decoded as a *key*
(or key segment) or as a *value*. The distinction matters for encoded dots
(``%2E``/``%2e``) in keys: when decoding keys, the default behavior is to
*preserve* these so that higher‑level options like ``allow_dots`` and
``decode_dot_in_keys`` can be applied consistently later in the parse.
"""

from enum import Enum


class DecodeKind(str, Enum):
    """Decoding context for query string tokens.

    Attributes
    ----------
    KEY
        Decode a *key* (or key segment). Implementations typically preserve
        percent‑encoded dots (``%2E``/``%2e``) so that dot‑splitting semantics can
        be applied later according to parser options.
    VALUE
        Decode a *value*. Implementations typically perform full percent decoding.
    """

    KEY = "key"  # Key/segment decode; preserve encoded dots for later splitting logic
    VALUE = "value"  # Value decode; fully percent-decode


__all__ = ["DecodeKind"]
