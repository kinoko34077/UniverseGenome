"""P9 diagnostic: read-only parent-side D15 worker CPU-load skew on true native128.

Fixed accepted source, original default1024 four-category selected128 seed0 only.
Never changes D15 worker requests, physics, selection, journal or science seed16384.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
from tempfile import TemporaryDirectory
import time

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d15_spawn_workers_226 import SpawnEvaluator
from research.d8_genome_diversity_190 import digest

SOURCE = "a592a284436e02fe820ad2cf73130e7f2062a452"
GOLDEN = "725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63"
RSS_CAP = 1536 * 1024 * 1024
JOURNAL_CAP = 128 * 1024 * 1024


def cpu_ticks(pid: int) -> int:
    """Read utime+stime from /proc/pid/stat, not a process lifetime estimate."""
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    fields = raw.rsplit(")", 1)[1].split()
    return int(fields[11]) + int(fields[12])


def evidence_root_files(path: Path) -> dict[str, str]:
    return {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.glob("*.json"))
        if item.name != "manifest.json"
    }


def run(tag: str, outfile: Path) -> None:
    source = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=10
    ).strip()
    if source != SOURCE:
        raise AssertionError("source mismatch")
    if tag not in ("baseline", "observed"):
        raise ValueError("unknown variant")

    traces: list[dict] = []
    original = SpawnEvaluator.evaluate

    def observed_evaluate(self, indices):
        before = {int(proc.pid): cpu_ticks(int(proc.pid)) for proc in self.processes}
        started = time.perf_counter()
        answer = original(self, indices)
        elapsed = time.perf_counter() - started
        after = {int(proc.pid): cpu_ticks(int(proc.pid)) for proc in self.processes}
        clock_ticks = __import__("os").sysconf("SC_CLK_TCK")
        cpu_by_worker = [
            (after[int(proc.pid)] - before[int(proc.pid)]) / clock_ticks
            for proc in self.processes
        ]
        traces.append({
            "ordinal": len(traces) + 1,
            "first_index": indices[0], "last_index": indices[-1],
            "slot_count": len(indices),
            "wall_seconds": elapsed,
            "worker_cpu_seconds": cpu_by_worker,
        })
        return answer

    if tag == "observed":
        SpawnEvaluator.evaluate = observed_evaluate
    try:
        with TemporaryDirectory(prefix="p9-original-native-") as td:
            root = Path(td) / "journal"
            started = time.perf_counter()
            result = execute_selected_round(
                root, source_commit=SOURCE, base_seed=0,
                experiment=ExperimentConfig(), base_config=PhysicsConfig(),
                evaluation_batch_size=16, memory_mib=1536, workers=4,
            )
            wall = time.perf_counter() - started
            if (not result["final_committed"]
                    or not result["finalization_performed"]
                    or result["resumed_from"] != 0
                    or result["new_evaluations"] != 128
                    or result["checkpoint_writes"] != 8
                    or result["final_digest"] != GOLDEN
                    or digest(result["final_snapshot"]) != GOLDEN):
                raise AssertionError("authentic original selected128 v7 drift")
            aggregate_rss = result.get("peak_aggregate_rss_bytes")
            if (aggregate_rss is None or aggregate_rss > RSS_CAP
                    or result["journal_bytes"] > JOURNAL_CAP):
                raise AssertionError("native original memory or journal resource cap exceeded")
            original_journal = evidence_root_files(root)
            if len(original_journal) < 10:
                raise AssertionError("not all native parent journal patches present")
            payload = {
                "kind": "PERF291_UNMODIFIED_D15_NATIVE128_WORKER_SKEW",
                "source_sha": SOURCE, "tag": tag, "seed": 0,
                "default_timeout_generations": 1024,
                "world_count": 128, "workers": 4,
                "full_optimizer_v7": result["final_digest"],
                "new_evaluations": result["new_evaluations"],
                "checkpoint_writes": result["checkpoint_writes"],
                "journal_bytes": result["journal_bytes"],
                "journal_file_sha256": original_journal,
                "sampled_aggregate_rss_bytes": aggregate_rss,
                "selected_wall_seconds": wall,
                "batches": traces,
                "science_seed16384_executed": False,
                "learning_claim": False,
            }
            if tag == "observed":
                if len(traces) != 8 or any(t["slot_count"] != 16 for t in traces):
                    raise AssertionError("expected exactly original 8 native batches")
                for t in traces:
                    cpu = t["worker_cpu_seconds"]
                    if len(cpu) != 4 or any(v < 0 for v in cpu):
                        raise AssertionError("invalid per-worker cpu sample")
                    t["cpu_skew_ratio"] = (max(cpu) / min(cpu) if min(cpu) else None)
                    t["theoretical_max_vs_avg_cpu_seconds"] = max(cpu) - statistics.mean(cpu)
            outfile.parent.mkdir(parents=True, exist_ok=True)
            outfile.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
            print(json.dumps({
                "tag": tag, "selected_wall_seconds": wall,
                "full_optimizer_v7": result["final_digest"],
                "batches": traces, "rss_bytes": aggregate_rss,
                "journal_bytes": result["journal_bytes"],
            }, sort_keys=True), flush=True)
    finally:
        SpawnEvaluator.evaluate = original


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("baseline", "observed"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.variant, args.out)
