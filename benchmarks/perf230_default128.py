"""#230: source-bound native128 full-default one-round wall/RSS/journal probe.

PERFORMANCE ONLY. Exposed seed0, exactly one original native selected
generation; never D16 seed16384, reserved cohorts or long outcome science.
No patch to physics, fitness, RNG, journal, or optimizer selection code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
from tempfile import TemporaryDirectory
import time

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d8_genome_diversity_190 import digest


def _write_json(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".writing")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def run_mode(*, workers: int, output: Path) -> dict:
    if type(workers) is not int or workers not in (1, 2, 4):
        raise ValueError("workers must be 1, 2 or 4")
    source = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=10,
    ).strip()
    if len(source) != 40:
        raise ValueError("full source commit required")
    config = {
        "experiment": ExperimentConfig().to_dict(),
        "physics": PhysicsConfig().to_dict(),
        "seed": 0,
        "workers": workers,
        "batch": 16,
        "memory_mib": 1536,
        "worlds": 128,
    }
    config_sha = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    started = time.perf_counter()
    cpu_start = time.process_time()
    child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    trace: list[dict] = []
    stages: list[dict] = []
    report = {
        "kind": "PERF230_default1024_full128_one_native_selected_round",
        "study_status": "INCOMPLETE",
        "source_sha": source,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "config": config,
        "config_sha256": config_sha,
        "checkpoint_trace": trace,
        "stage_trace": stages,
        "D16_seed16384_outcomes": False,
        "learning_claim": False,
    }
    _write_json(output, report)

    def checkpoint(index: int) -> None:
        trace.append({
            "evaluated_to": index,
            "wall_since_beginning_s": time.perf_counter() - started,
        })
        # Crash/timeout leaves a durable INCOMPLETE progress witness.
        _write_json(output, report)

    def stage(label: str) -> None:
        stages.append({
            "stage": label,
            "wall_since_beginning_s": time.perf_counter() - started,
        })
        _write_json(output, report)

    with TemporaryDirectory(prefix="perf230-default128-") as tempdir:
        result = execute_selected_round(
            Path(tempdir) / "one_original_round",
            source_commit=source,
            base_seed=0,
            experiment=ExperimentConfig(),
            base_config=PhysicsConfig(),
            evaluation_batch_size=16,
            memory_mib=1536,
            workers=workers,
            on_checkpoint=checkpoint,
            on_stage=stage,
        )
    cpu_end = time.process_time()
    child_end = resource.getrusage(resource.RUSAGE_CHILDREN)
    if not (
        result["final_committed"]
        and result["finalization_performed"]
        and result["new_evaluations"] == 128
        and result["resumed_from"] == 0
        and result["final_digest"] == digest(result["final_snapshot"])
    ):
        raise AssertionError("original full128 native one-round integrity failure")
    report.update({
        "study_status": "COMPLETE",
        "actual_wall_seconds": time.perf_counter() - started,
        "parent_cpu_seconds": cpu_end - cpu_start,
        "child_user_cpu_seconds": child_end.ru_utime - child_start.ru_utime,
        "child_system_cpu_seconds": child_end.ru_stime - child_start.ru_stime,
        "final_digest": result["final_digest"],
        "evaluated_worlds": result["new_evaluations"],
        "native_selection_performed": result["finalization_performed"],
        "journal_bytes": result["journal_bytes"],
        "checkpoint_writes": result["checkpoint_writes"],
        "parent_peak_rss_bytes": result["peak_rss_bytes"],
        "observed_aggregate_peak_rss_bytes": result.get(
            "peak_aggregate_rss_bytes"),
        "worker_hard_virtual_cap_bytes": result.get(
            "worker_hard_virtual_cap_bytes"),
    })
    _write_json(output, report)
    print(json.dumps(report, sort_keys=True), flush=True)
    return report


def compare_reports(folder: Path, output: Path) -> dict:
    reports = []
    for workers in (1, 2, 4):
        path = folder / f"perf230-default128-{workers}.json"
        reports.append(json.loads(path.read_text(encoding="utf-8")))
    if any(row["study_status"] != "COMPLETE" for row in reports):
        raise AssertionError("at least one default128 mode did not finish")
    for key in ("source_sha", "final_digest"):
        if len({r[key] for r in reports}) != 1:
            raise AssertionError(f"native selected full-state {key} diverges")
    control = dict(reports[0]["config"])
    for row in reports:
        config = dict(row["config"])
        workers = config.pop("workers")
        if workers not in (1, 2, 4) or config != {
            k: v for k, v in control.items() if k != "workers"
        }:
            raise AssertionError("nonworker experimental condition diverges")
        if row["evaluated_worlds"] != 128 or not row["native_selection_performed"]:
            raise AssertionError("missing original native selected round")
    timing = {r["config"]["workers"]: r["actual_wall_seconds"] for r in reports}
    result = {
        "kind": "PERF230_source_equal_native_default128_comparison",
        "source_sha": reports[0]["source_sha"],
        "identical_full_v7_digest": reports[0]["final_digest"],
        "same_host_comparison": False,
        "measurement_repetitions": 1,
        "actual_wall_by_workers": timing,
        "ratios_vs_serial_independent_host": {
            str(w): timing[1] / timing[w] for w in (2, 4)
        },
        "note": "3 separate hosted jobs; ratios are exploratory; no 37-round D16 extrapolation",
        "D16_seed16384_outcomes": False,
        "learning_claim": False,
    }
    _write_json(output, result)
    print(json.dumps(result, sort_keys=True), flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workers", type=int, choices=(1, 2, 4))
    group.add_argument("--compare-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.compare_dir is not None:
        compare_reports(args.compare_dir, args.output)
    else:
        run_mode(workers=args.workers, output=args.output)


if __name__ == "__main__":
    main()
