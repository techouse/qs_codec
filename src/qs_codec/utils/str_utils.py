"""Utility functions for working with strings."""


def code_unit_at(string: str, index: int) -> int:
    """Returns the 16-bit UTF-16 code unit at the given index.

    This function first encodes the string in UTF-16 little endian format, then calculates the code unit at the
    given index. The code unit is calculated by taking the byte at the index and adding it to 256 times the next
    byte. This is because UTF-16 represents each code unit with two bytes, and in little endian format, the least
    significant byte comes first.

    Adapted from https://api.dart.dev/stable/3.3.3/dart-core/String/codeUnitAt.html
    """
    encoded_string: bytes = string.encode("utf-16-le", "surrogatepass")
    return int.from_bytes(encoded_string[index * 2 : index * 2 + 2], byteorder="little")
