"""PERF230 P4.1: source-bound original native default128 multi-round speed trend.

Four consecutive genuine original selected128 D15 rounds on *benchmark seed0*.
No D16 seed16384, reserved cohort, held-out, physics or search change.
This is performance evidence, not a completed-growth, prune or learning study.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import time
from typing import Any

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

EXPECTED_DEFAULT_FIRST = "725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63"
EXPECTED_SHORT_FIRST = "0ad8268476bf79f3c9db02a91ebf92dba3250339571fb651913eaf845410b321"
MAX_SOFT_WALL_SECONDS = 900.0
MAX_JOURNAL_PER_ROUND = 128 * 1024 * 1024
MAX_ALL_JOURNAL_BYTES = 512 * 1024 * 1024
MAX_RSS_BYTES = 1536 * 1024 * 1024


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run(output: Path, *, short_smoke: bool = False) -> dict[str, Any]:
    source = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=10,
    ).strip()
    if len(source) != 40:
        raise ValueError("source-bound SHA is required")
    # Fixed non-study, outcome-exposed benchmark seed. Do not add a --seed CLI.
    base_seed = 0
    protocol = (
        ExperimentConfig(evaluation_timeout_generations=2)
        if short_smoke else ExperimentConfig()
    )
    physics = PhysicsConfig()
    target_rounds = 2 if short_smoke else 4
    started = time.monotonic()
    previous: dict[str, Any] | None = None
    report: dict[str, Any] = {
        "kind": "PERF230_P4.1_TEST_ONLY_CONSECUTIVE_NATIVE128_DEFAULT_ROUNDS",
        "source_sha": source,
        "seed": base_seed,
        "default1024": not short_smoke,
        "evaluation_timeout_generations": protocol.evaluation_timeout_generations,
        "workers": 4,
        "original_world_count": 128,
        "max_complete_rounds": target_rounds,
        "wall_budget_soft_seconds": MAX_SOFT_WALL_SECONDS,
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "rounds": [],
        "aggregate_journal_bytes": 0,
        "completion": "INCOMPLETE",
        "D16_research_seed16384_executed": False,
        "learning_claim": False,
    }
    _write_report(output, report)
    with TemporaryDirectory(prefix="perf230-p41-native-selected-") as temp:
        for round_index in range(target_rounds):
            if time.monotonic() - started >= MAX_SOFT_WALL_SECONDS:
                report["completion"] = "BUDGET_BOUND"
                break
            begin = time.monotonic()
            parent_cpu_before = time.process_time()
            result = execute_selected_round(
                Path(temp) / f"journal-round-{round_index:02d}",
                source_commit=source,
                base_seed=base_seed,
                experiment=protocol,
                base_config=physics,
                base_snapshot=previous,
                evaluation_batch_size=16,
                memory_mib=1536,
                workers=4,
            )
            completed_wall = time.monotonic() - begin
            parent_cpu = time.process_time() - parent_cpu_before
            snapshot = result["final_snapshot"]
            original = SteadyStateOptimizer.from_snapshot(snapshot)
            if original.to_snapshot() != snapshot:
                raise AssertionError("completed selected v7 state import drift")
            category_counts: dict[str, int] = {}
            for slot in original.slots:
                category_counts[slot.category] = category_counts.get(slot.category, 0) + 1
            if sorted(category_counts.values()) != [32, 32, 32, 32]:
                raise AssertionError("not original category-local 4x32 selection")
            if (
                original.generation != round_index + 1
                or result["final_digest"] != digest(snapshot)
                or result["new_evaluations"] != 128
                or result["resumed_from"] != 0
                or not result["final_committed"]
                or not result["finalization_performed"]
                or result["checkpoint_writes"] != 8
                or result["journal_bytes"] > MAX_JOURNAL_PER_ROUND
            ):
                raise AssertionError("original native128 generation/selection/journal mismatch")
            first_gold = EXPECTED_SHORT_FIRST if short_smoke else EXPECTED_DEFAULT_FIRST
            if round_index == 0 and result["final_digest"] != first_gold:
                raise AssertionError("original first completed native selected128 source oracle drift")
            if (
                result.get("peak_aggregate_rss_bytes") is None
                or result["peak_aggregate_rss_bytes"] > MAX_RSS_BYTES
            ):
                raise AssertionError("original aggregate worker budget changed")
            report["aggregate_journal_bytes"] += result["journal_bytes"]
            if report["aggregate_journal_bytes"] > MAX_ALL_JOURNAL_BYTES:
                raise AssertionError("cross-round retained journal capacity exceeded")
            row = {
                "ordinal": round_index + 1,
                "optimizer_generation": original.generation,
                "selected_v7_sha256": result["final_digest"],
                "source_commit": source,
                "original_world_evaluations": result["new_evaluations"],
                "checkpoint_writes": result["checkpoint_writes"],
                "journal_bytes": result["journal_bytes"],
                "elapsed_wall_seconds": completed_wall,
                "elapsed_parent_cpu_seconds": parent_cpu,
                "sampled_peak_parent_rss_bytes": result["peak_rss_bytes"],
                "sampled_peak_aggregate_rss_bytes": result["peak_aggregate_rss_bytes"],
                "child_hard_virtual_cap_bytes": result["worker_hard_virtual_cap_bytes"],
            }
            report["rounds"].append(row)
            report["cumulative_wall_seconds"] = time.monotonic() - started
            report["completion"] = (
                "COMPLETE" if len(report["rounds"]) == target_rounds else "INCOMPLETE"
            )
            _write_report(output, report)
            print(json.dumps({"round": row, "cumulative_wall_seconds": report["cumulative_wall_seconds"]},
                             sort_keys=True), flush=True)
            previous = snapshot
            if report["cumulative_wall_seconds"] >= MAX_SOFT_WALL_SECONDS:
                report["completion"] = "BUDGET_BOUND"
                _write_report(output, report)
                break
    _write_report(output, report)
    if report["completion"] != "COMPLETE":
        raise RuntimeError(f"bounded benchmark incomplete: {report['completion']}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--short-smoke", action="store_true")
    args = parser.parse_args()
    result = run(args.output, short_smoke=args.short_smoke)
    print(json.dumps({"completion": result["completion"],
                      "round_walls": [r["elapsed_wall_seconds"] for r in result["rounds"]],
                      "total_s": result["cumulative_wall_seconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
