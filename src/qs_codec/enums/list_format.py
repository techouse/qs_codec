"""List formatting strategies for query‑string arrays.

This module defines small generator functions and an enum that the encoder
uses to format list (array) keys, e.g., ``foo[]=1``, ``foo[0]=1``, ``foo=1,2``,
or repeated keys ``foo=1&foo=2``.
"""

import typing as t
from dataclasses import dataclass
from enum import Enum


class ListFormatGenerator:
    """Factory of tiny helpers that format a list element key segment.

    Each static method returns the string that should be appended to the
    current key ``prefix`` to represent *one* element in a list. The encoder
    selects the method based on the chosen :class:`ListFormat` variant.
    """

    @staticmethod
    def brackets(prefix: str, key: t.Optional[str] = None) -> str:  # pylint: disable=W0613
        """Return the key for a list element using empty brackets.

        Example:
            ``prefix='foo'`` → ``'foo[]'``

        Args:
            prefix: The current key prefix (e.g., ``'foo'``).
            key: Unused for this strategy.

        Returns:
            The formatted key segment.
        """
        return f"{prefix}[]"

    @staticmethod
    def comma(prefix: str, key: t.Optional[str] = None) -> str:  # pylint: disable=W0613
        """Return the key for comma‑separated lists (no change).

        The encoder will join values with commas instead of repeating the key.

        Args:
            prefix: Current key prefix.
            key: Unused for this strategy.

        Returns:
            The unchanged prefix.
        """
        return prefix

    @staticmethod
    def indices(prefix: str, key: t.Optional[str] = None) -> str:
        """Return the key for an indexed list element.

        Example:
            ``prefix='foo'``, ``key='0'`` → ``'foo[0]'``

        Args:
            prefix: Current key prefix.
            key: The numeric index string for this element.

        Returns:
            The formatted key.
        """
        return f"{prefix}[{key}]"

    @staticmethod
    def repeat(prefix: str, key: t.Optional[str] = None) -> str:  # pylint: disable=W0613
        """Return the key for “repeat key” lists (no change).

        Example:
            ``prefix='foo'`` → ``'foo'`` (the key is repeated per element)

        Args:
            prefix: Current key prefix.
            key: Unused for this strategy.

        Returns:
            The unchanged prefix.
        """
        return prefix


@dataclass(frozen=True)
class _ListFormatDataMixin:
    """Mixin carrying metadata for a list format option.

    Attributes:
        list_format_name: Stable string identifier (e.g., ``"BRACKETS"``).
        generator: Callable that formats a list element key given (prefix, index).
    """

    list_format_name: str
    generator: t.Callable[[str, t.Optional[str]], str]


class ListFormat(_ListFormatDataMixin, Enum):
    """Available list formatting options for the encoder.

    Each member pairs a stable name with a generator function from
    :class:`ListFormatGenerator`:

    - ``BRACKETS``: ``foo[]`` for each element.
    - ``INDICES``: ``foo[0]``, ``foo[1]``, …
    - ``REPEAT``: repeat the key per value (``foo=1&foo=2``).
    - ``COMMA``: single key with comma‑joined values (``foo=1,2``).

    These options control only how keys are produced; value encoding and
    delimiter handling are governed by other options.
    """

    BRACKETS = "BRACKETS", ListFormatGenerator.brackets
    """Use brackets to represent list items, for example ``foo[]=123&foo[]=456&foo[]=789``."""

    COMMA = "COMMA", ListFormatGenerator.comma
    """Use commas to represent list items, for example ``foo=123,456,789``."""

    REPEAT = "REPEAT", ListFormatGenerator.repeat
    """Use a repeat key to represent list items, for example ``foo=123&foo=456&foo=789``."""

    INDICES = "INDICES", ListFormatGenerator.indices
    """Use indices to represent list items, for example ``foo[0]=123&foo[1]=456&foo[2]=789``."""
