"""An enum for all available list format options."""

import typing as t
from dataclasses import dataclass
from enum import Enum


class ListFormatGenerator:
    """A class for formatting list items."""

    @staticmethod
    def brackets(prefix: str, key: t.Optional[str] = None) -> str:  # pylint: disable=W0613
        """Format a list item using brackets."""
        return f"{prefix}[]"

    @staticmethod
    def comma(prefix: str, key: t.Optional[str] = None) -> str:  # pylint: disable=W0613
        """Format a list item using commas."""
        return prefix

    @staticmethod
    def indices(prefix: str, key: t.Optional[str] = None) -> str:
        """Format a list item using indices."""
        return f"{prefix}[{key}]"

    @staticmethod
    def repeat(prefix: str, key: t.Optional[str] = None) -> str:  # pylint: disable=W0613
        """Format a list item using repeats."""
        return prefix


@dataclass(frozen=True)
class _ListFormatDataMixin:
    """List format data mixin."""

    list_format_name: str
    generator: t.Callable[[str, t.Optional[str]], str]


class ListFormat(_ListFormatDataMixin, Enum):
    """An enum of all available list format options."""

    BRACKETS = "BRACKETS", ListFormatGenerator.brackets
    """Use brackets to represent list items, for example ``foo[]=123&foo[]=456&foo[]=789``"""

    COMMA = "COMMA", ListFormatGenerator.comma
    """Use commas to represent list items, for example ``foo=123,456,789``"""

    REPEAT = "REPEAT", ListFormatGenerator.repeat
    """Use a repeat key to represent list items, for example ``foo=123&foo=456&foo=789``"""

    INDICES = "INDICES", ListFormatGenerator.indices
    """Use indices to represent list items, for example ``foo[0]=123&foo[1]=456&foo[2]=789``"""
