#!/usr/bin/env python3
"""Local decode benchmark snapshot (not used by CI).

Usage:
    python scripts/bench_decode_snapshot.py
    python scripts/bench_decode_snapshot.py --warmups 3 --samples 5
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qs_codec import DecodeOptions, decode


@dataclass(frozen=True)
class DecodeCase:
    name: str
    count: int
    comma: bool
    utf8_sentinel: bool
    value_len: int
    iterations: int


CASES = (
    DecodeCase(name="C1", count=100, comma=False, utf8_sentinel=False, value_len=8, iterations=120),
    DecodeCase(name="C2", count=1000, comma=False, utf8_sentinel=False, value_len=40, iterations=16),
    DecodeCase(name="C3", count=1000, comma=True, utf8_sentinel=True, value_len=40, iterations=16),
)


def make_value(length: int, seed: int) -> str:
    out: list[str] = []
    state = ((seed * 2654435761) + 1013904223) & 0xFFFFFFFF
    for _ in range(length):
        state ^= (state << 13) & 0xFFFFFFFF
        state ^= (state >> 17) & 0xFFFFFFFF
        state ^= (state << 5) & 0xFFFFFFFF

        x = state % 62
        if x < 10:
            ch = chr(0x30 + x)
        elif x < 36:
            ch = chr(0x41 + (x - 10))
        else:
            ch = chr(0x61 + (x - 36))
        out.append(ch)

    return "".join(out)


def build_query(count: int, comma_lists: bool, utf8_sentinel: bool, value_len: int) -> str:
    parts: list[str] = []
    if utf8_sentinel:
        parts.append("utf8=%E2%9C%93")

    for i in range(count):
        key = f"k{i}"
        value = "a,b,c" if comma_lists and i % 10 == 0 else make_value(value_len, i)
        parts.append(f"{key}={value}")

    return "&".join(parts)


def measure_case(case: DecodeCase, warmups: int, samples: int) -> tuple[float, int]:
    query = build_query(case.count, case.comma, case.utf8_sentinel, case.value_len)
    options = DecodeOptions(
        comma=case.comma,
        parse_lists=True,
        parameter_limit=float("inf"),
        raise_on_limit_exceeded=False,
        interpret_numeric_entities=False,
        charset_sentinel=case.utf8_sentinel,
        ignore_query_prefix=False,
    )

    for _ in range(warmups):
        decode(query, options=options)

    measurements: list[float] = []
    key_count = 0
    for _ in range(samples):
        start = time.perf_counter()
        parsed: dict[str, object] = {}
        for _ in range(case.iterations):
            parsed = decode(query, options=options)
        elapsed = (time.perf_counter() - start) * 1000.0 / case.iterations
        measurements.append(elapsed)
        key_count = len(parsed)

    return statistics.median(measurements), key_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark decode performance snapshot cases (C1/C2/C3).")
    parser.add_argument("--warmups", type=int, default=5, help="warm-up runs per case")
    parser.add_argument("--samples", type=int, default=7, help="timed samples per case")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.warmups < 0:
        raise ValueError("--warmups must be >= 0")
    if args.samples <= 0:
        raise ValueError("--samples must be > 0")

    print(f"qs.py decode perf snapshot (median of {args.samples} samples)")
    print("Decode (public API):")
    for case in CASES:
        median_ms, key_count = measure_case(case, warmups=args.warmups, samples=args.samples)
        print(
            "  "
            f"{case.name}: count={str(case.count).rjust(4)}, "
            f"comma={str(case.comma).ljust(5)}, "
            f"utf8={str(case.utf8_sentinel).ljust(5)}, "
            f"len={str(case.value_len).rjust(2)}: "
            f"{median_ms:7.3f} ms/op | keys={key_count}"
        )


if __name__ == "__main__":
    main()
