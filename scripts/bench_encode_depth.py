#!/usr/bin/env python3
"""Local deep-encode benchmark (not used by CI).

Usage:
    python scripts/bench_encode_depth.py
    python scripts/bench_encode_depth.py --runs 5 --depths 2000 5000 12000
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
import typing as t
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qs_codec import encode
from qs_codec.models.encode_options import EncodeOptions


def make_nested(depth: int) -> t.Dict[str, t.Any]:
    data: t.Dict[str, t.Any] = {"leaf": "x"}
    for _ in range(depth):
        data = {"a": data}
    return data


def run_once(depth: int) -> float:
    data = make_nested(depth)
    start = time.perf_counter()
    result = encode(data, options=EncodeOptions(encode=False))
    elapsed = time.perf_counter() - start
    if not result.endswith("=x"):
        raise RuntimeError(f"unexpected encoded output for depth={depth}")
    return elapsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark deep encode performance.")
    parser.add_argument("--runs", type=int, default=3, help="timed runs per depth")
    parser.add_argument("--warmups", type=int, default=1, help="warm-up runs per depth")
    parser.add_argument(
        "--depths",
        type=int,
        nargs="+",
        default=[2000, 5000, 12000],
        help="depth values to benchmark",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.runs <= 0:
        raise ValueError("--runs must be > 0")
    if args.warmups < 0:
        raise ValueError("--warmups must be >= 0")
    if not args.depths:
        raise ValueError("--depths must not be empty")

    print(f"python={sys.version.split()[0]} runs={args.runs} warmups={args.warmups}")
    for depth in args.depths:
        for _ in range(args.warmups):
            run_once(depth)

        times = [run_once(depth) for _ in range(args.runs)]
        median = statistics.median(times)
        print(f"depth={depth} median={median:.6f}s " f"runs=[{', '.join(f'{t_:.6f}' for t_ in times)}]")


if __name__ == "__main__":
    main()
