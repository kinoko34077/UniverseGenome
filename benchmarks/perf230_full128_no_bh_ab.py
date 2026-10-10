"""PERF230: genuine default1024 full128 selected original journal A/B witness.

This is performance-only test tooling for original seed0, exactly one
authoritative original selection. No D16 seed16384 or long growth study.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
from tempfile import TemporaryDirectory
import time

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d8_genome_diversity_190 import digest

PRE_PATCH_SOURCE_FULL_DEFAULT_SEED0_GOLDEN = (
    "725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=10,
    ).strip()
    if len(source) != 40:
        raise ValueError("exact source SHA required")
    started = time.perf_counter()
    with TemporaryDirectory(prefix="perf230-full-default-bh-") as temp:
        result = execute_selected_round(
            Path(temp) / "original_native",
            source_commit=source,
            base_seed=0,
            experiment=ExperimentConfig(),
            base_config=PhysicsConfig(),
            evaluation_batch_size=16,
            memory_mib=1536,
            workers=4,
        )
        wall = time.perf_counter() - started
    if (
        not result["final_committed"]
        or not result["finalization_performed"]
        or result["resumed_from"] != 0
        or result["new_evaluations"] != 128
        or result["checkpoint_writes"] != 8
        or result["final_digest"] != PRE_PATCH_SOURCE_FULL_DEFAULT_SEED0_GOLDEN
        or digest(result["final_snapshot"]) != PRE_PATCH_SOURCE_FULL_DEFAULT_SEED0_GOLDEN
    ):
        raise AssertionError("source-bound original selected128 default state drift")
    report = {
        "kind": "PERF230_bh_fastpath_same_host_native_default128",
        "source_sha": source,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "seed": 0,
        "workers": 4,
        "world_count": 128,
        "original_default_timeout_generations": 1024,
        "wall_seconds": wall,
        "original_native_full_optimizer_digest": result["final_digest"],
        "evaluated_worlds": result["new_evaluations"],
        "original_selected_once": result["finalization_performed"],
        "journal_bytes": result["journal_bytes"],
        "checkpoint_writes": result["checkpoint_writes"],
        "parent_peak_rss_bytes": result["peak_rss_bytes"],
        "sampled_aggregate_peak_rss_bytes": result.get(
            "peak_aggregate_rss_bytes"
        ),
        "child_hard_virtual_cap_bytes": result.get(
            "worker_hard_virtual_cap_bytes"
        ),
        "D16_seed16384_outcomes": False,
        "learning_claim": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
