"""String utilities for UTF‑16 code unit operations.

This module mirrors the semantics used by the Dart `String.codeUnitAt` API:
it treats a Python `str` as a sequence of UTF‑16 *code units* (16‑bit
values), not Unicode scalar values. That matters for characters outside the
Basic Multilingual Plane (BMP), which are represented as surrogate pairs
(two code units).

Implementation notes:
- We encode with UTF‑16 little‑endian using the ``surrogatepass`` error
  handler to preserve lone surrogates exactly like Dart/JS engines do.
- The index passed to :func:`code_unit_at` is in **code units** (not
  Python `str` indices).
"""


def code_unit_at(string: str, index: int) -> int:
    """
    Return the 16‑bit UTF‑16 code unit at *index*.

    Parameters
    ----------
    string:
        Source Unicode string.
    index:
        Zero‑based position counted in **UTF‑16 code units**.

    Returns
    -------
    int
        An integer in the range 0..0xFFFF representing the code unit at
        the requested UTF‑16 position.

    Raises
    ------
    IndexError
        If *index* is negative or outside the number of UTF‑16 code units.

    Examples
    --------
    >>> code_unit_at("A", 0)
    65
    >>> # U+1F600 GRINNING FACE 😀 → surrogate pair D83D DE00 in UTF‑16
    >>> code_unit_at("😀", 0) == 0xD83D
    True
    >>> code_unit_at("😀", 1) == 0xDE00
    True
    """
    # Encode as UTF‑16 little‑endian and *preserve* surrogate halves.
    encoded = string.encode("utf-16-le", "surrogatepass")

    total_units = len(encoded) // 2
    if index < 0 or index >= total_units:
        raise IndexError(f"code_unit_at index out of range: {index} (total UTF-16 code units: {total_units})")

    start = index * 2
    # int.from_bytes reads exactly two bytes as a little‑endian 16‑bit value.
    return int.from_bytes(encoded[start : start + 2], byteorder="little")
