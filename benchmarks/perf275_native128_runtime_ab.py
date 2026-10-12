"""PERF275 P7.1: genuine original default1024 native selected128, runtime only.

This is a TEST-ONLY same-source Python runtime comparison using exposed seed0.
No true original seed16384 science, changed physics, reseed or extra D16 study job.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import platform
import resource
import subprocess
from tempfile import TemporaryDirectory
import time

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d16_native_journal_observer_217 import observe_committed_round
from research.d8_genome_diversity_190 import digest

SOURCE = "65e1d78576026b0214a0184bd6028e01dc3cc7e1"
GOLDEN = "725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, timeout=10).strip()
    if source != SOURCE:
        raise AssertionError("not frozen accepted main original native source")
    start = time.perf_counter()
    with TemporaryDirectory(prefix="perf275-original-native128-interpreter-") as tmp:
        root = Path(tmp) / "journal"
        original = execute_selected_round(
            root, source_commit=source, base_seed=0,
            experiment=ExperimentConfig(), base_config=PhysicsConfig(),
            workers=4, evaluation_batch_size=16, memory_mib=1536,
        )
        selected_wall = time.perf_counter() - start
        observation = observe_committed_round(root, source_commit=source)
        total_wall = time.perf_counter() - start
        if (
            original["final_digest"] != GOLDEN
            or digest(original["final_snapshot"]) != GOLDEN
            or original["new_evaluations"] != 128
            or original["checkpoint_writes"] != 8
            or original["resumed_from"] != 0
            or not original["final_committed"]
            or not original["finalization_performed"]
            or observation["selected_post_v7_sha256"] != GOLDEN
            or observation["d15_journal_chain_verified"] is not True
            or observation["evaluated_native_worlds"] != 128
            or observation["original_selected_once_proven_by_D15_final"] is not True
            or observation["learning_claim"] is not False
            or original["journal_bytes"] > 128*1024*1024
            or original.get("peak_aggregate_rss_bytes", 2**64) > 1536*1024*1024
        ):
            raise AssertionError("native original selected state/D15 writer/observer/resource drift")
        result = {
            "kind": "PERF275_P71_TRUE_DEFAULT1024_NATIVE128_SEED0_ONLY",
            "source_sha": source, "interpreter": platform.python_implementation(),
            "python_version": platform.python_version(), "os_platform": platform.platform(),
            "seed": 0, "workers": 4, "evaluated_native_worlds": 128,
            "original_selected_native_v7_sha256": original["final_digest"],
            "original_observer_readonly": observation["read_only"],
            "d15_journal_bytes": original["journal_bytes"],
            "parent_d15_patches": original["checkpoint_writes"],
            "selected_wall_seconds": selected_wall,
            "selected_plus_observer_wall_seconds": total_wall,
            "sampled_aggregate_peak_rss_bytes": original["peak_aggregate_rss_bytes"],
            "parent_rss_peak_bytes": original["peak_rss_bytes"],
            "child_hard_virtual_cap_bytes": original.get("worker_hard_virtual_cap_bytes"),
            "current_process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "real_d16_science_seed16384_executed": False, "learning_claim": False,
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
