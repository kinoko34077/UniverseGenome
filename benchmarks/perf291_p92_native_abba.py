"""P9.2 one genuine original native128 selected, source-frozen old vs diagonal.

The same-host ABBA comparison is hosted in a separate pull_request-only
workflow. Original performance seed0, never reserved science seed16384.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import time

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d8_genome_diversity_190 import digest

BASE_SHA = "a592a284436e02fe820ad2cf73130e7f2062a452"
GOLDEN = "725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63"
RSS_LIMIT = 1536 * 1024 * 1024
JOURNAL_LIMIT = 128 * 1024 * 1024


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected-sha", required=True)
    ap.add_argument("--variant", choices=("old", "diagonal"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, timeout=10).strip()
    if head != args.expected_sha or len(head) != 40:
        raise AssertionError("incorrect original pinned source")
    if args.variant == "old" and head != BASE_SHA:
        raise AssertionError("original source baseline moved")
    with TemporaryDirectory(prefix="perf291-native128-diagonal-") as td:
        journal = Path(td) / "original"
        started = time.perf_counter()
        result = execute_selected_round(
            journal, source_commit=head, base_seed=0,
            experiment=ExperimentConfig(), base_config=PhysicsConfig(),
            evaluation_batch_size=16, memory_mib=1536, workers=4,
        )
        wall = time.perf_counter() - started
        if (not result["final_committed"]
                or not result["finalization_performed"]
                or result["new_evaluations"] != 128
                or result["resumed_from"] != 0
                or result["checkpoint_writes"] != 8
                or result["final_digest"] != GOLDEN
                or digest(result["final_snapshot"]) != GOLDEN):
            raise AssertionError("original optimizer-v7 selected128 diverged")
        peak_rss = result.get("peak_aggregate_rss_bytes")
        if peak_rss is None or peak_rss > RSS_LIMIT:
            raise AssertionError("original full native aggregate RSS exceeded")
        journal_bytes = result["journal_bytes"]
        if journal_bytes > JOURNAL_LIMIT:
            raise AssertionError("original per-round journal budget exceeded")
        snapshots = {
            x.name: hashlib.sha256(x.read_bytes()).hexdigest()
            for x in sorted(journal.glob("*.json"))
            if x.name != "manifest.json"
        }
        expected = {"base.json", "final.json"} | {
            f"batch-{i:05d}.json" for i in range(8)
        }
        if set(snapshots) != expected:
            raise AssertionError("original journal files missing")
        payload = {
            "kind": "PERF291_P92_NATIVE128_DIAGONAL_ABBA",
            "source_sha": head, "variant": args.variant,
            "seed": 0, "timeout_generations": 1024,
            "worlds": 128, "workers": 4, "spawn_batch_size": 16,
            "selected_once": True, "journal_patches": 8,
            "original_full_optimizer_v7": GOLDEN,
            "journal_bytes": journal_bytes,
            "journal_sha256": snapshots,
            "sampled_aggregate_rss_bytes": peak_rss,
            "selected_wall_seconds": wall,
            "science_seed16384_executed": False,
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, sort_keys=True, indent=2)+"\n")
        print(json.dumps({k:v for k,v in payload.items() if k!="journal_sha256"},
                         sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
