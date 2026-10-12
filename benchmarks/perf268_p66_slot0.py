"""P6.6 accepted-source one original native default1024 seed0 slot0 witness.

Original science seed16384 is never run here. Requires exact immutable source SHA.
"""
import argparse
import json
from pathlib import Path
import platform
import resource
import subprocess
import time

from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

GOLDEN = "e146bebe695dec14fc978e47d4a1e189d1e30bdaa83f9d6e69eec3c4d201f4c1"
BASE = "e7f2efd0c9ec49afc53b9265ec4b17e936798160"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--expected-source", required=True)
    args = p.parse_args()
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if source != args.expected_source or len(source) != 40:
        raise AssertionError("run original exact caller-frozen source, no drift")
    t = time.perf_counter()
    opt = SteadyStateOptimizer.from_defaults(base_seed=0)
    opt._evaluate_slot(opt.slots[0])
    wall = time.perf_counter() - t
    checksum = digest(opt.to_snapshot())
    if checksum != GOLDEN:
        raise AssertionError("source original native default1024 full-v7 changed: " + checksum)
    result = {
        "kind": "PERF268_P66_ORIGINAL_NATIVE_SLOT0_SEED0_ONLY",
        "source_sha": source, "seed": 0, "worlds": 1,
        "original_default1024": True, "wall_seconds": wall,
        "v7_sha256": checksum, "interpreter": platform.python_implementation(),
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "real_original_seed16384": False, "learning_claim": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
