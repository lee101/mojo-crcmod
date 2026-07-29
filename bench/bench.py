"""Benchmark Mojo CRC kernels against the crcmod C extension."""

from __future__ import annotations

import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

import crcmod.predefined as upstream  # noqa: E402
from mojo_crcmod import predefined as mojo  # noqa: E402


def best_time(function, iterations: int, repeats: int = 5) -> float:
    best = float("inf")
    for _ in range(repeats):
        start = time.perf_counter()
        for _ in range(iterations):
            function()
        best = min(best, (time.perf_counter() - start) / iterations)
    return best


def cpu_name() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def rate(size: int, seconds: float) -> str:
    if size < 1024:
        return f"{seconds * 1e6:.2f} us"
    return f"{size / seconds / 1e9:.2f} GB/s"


def main() -> None:
    cases = (
        ("64 B", bytes(range(64)), 50_000),
        ("4 KiB", os.urandom(4 * 1024), 5_000),
        ("1 MiB", os.urandom(1024 * 1024), 40),
        ("16 MiB", os.urandom(16 * 1024 * 1024), 3),
    )
    print(
        f"Machine: {cpu_name()}; {platform.system()} {platform.machine()}; "
        f"Python {platform.python_version()}"
    )
    print()
    print("| Algorithm | Input | Mojo | Upstream crcmod | Mojo / upstream |")
    print("|---|---:|---:|---:|---:|")
    for name in ("crc-8", "xmodem", "crc-32", "crc-64"):
        mojo_function = mojo.mkCrcFun(name)
        upstream_function = upstream.mkCrcFun(name)
        for label, data, iterations in cases:
            assert mojo_function(data) == upstream_function(data)
            mojo_seconds = best_time(
                lambda: mojo_function(data), iterations
            )
            upstream_seconds = best_time(
                lambda: upstream_function(data), iterations
            )
            ratio = upstream_seconds / mojo_seconds
            print(
                f"| {name} | {label} | {rate(len(data), mojo_seconds)} | "
                f"{rate(len(data), upstream_seconds)} | {ratio:.2f}x |"
            )


if __name__ == "__main__":
    main()
