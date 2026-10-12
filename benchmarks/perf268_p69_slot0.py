"""One original native default1024 seed0 slot0, exact immutable source & full-v7."""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import subprocess
import time

from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

GOLDEN = "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--out", type=Path, required=True)
    opts = parser.parse_args()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, timeout=10).strip()
    if head != opts.expected_sha or len(head) != 40:
        raise AssertionError("not the frozen original source")
    started = time.perf_counter()
    obj = SteadyStateOptimizer.from_defaults(base_seed=0)
    obj._evaluate_slot(obj.slots[0])
    wall = time.perf_counter() - started
    v7 = digest(obj.to_snapshot())
    if v7 != GOLDEN:
        raise AssertionError(f"full optimizer v7 mismatched {v7}")
    row = {
        "source_sha": head, "seed": 0, "native_slots_evaluated": 1,
        "native_default1024": True, "runtime": platform.python_version(),
        "original_full_optimizer_v7": v7, "wall_seconds": wall,
        "original_seed16384_executed": False,
    }
    opts.out.parent.mkdir(parents=True, exist_ok=True)
    opts.out.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n")
    print(json.dumps(row, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
