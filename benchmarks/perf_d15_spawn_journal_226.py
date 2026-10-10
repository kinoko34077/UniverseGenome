"""#226 source-locked true D15 journal serial/2/4 spawn selected128 A/B.

Evaluates only existing previously exposed seed0 short timeout2 science-free golden.
No default seed16384, no D16 actual long scientific trajectory.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import subprocess
from tempfile import TemporaryDirectory
import time
import argparse
import fcntl

from core.experiment import ExperimentConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d15_spawn_workers_226 import SpawnEvaluator
from research.d15_sparse_recovery_213 import ResourceBudget
from search.evolution import SteadyStateOptimizer, UniverseSlot
from research.d8_genome_diversity_190 import digest

GOLDEN = "0ad8268476bf79f3c9db02a91ebf92dba3250339571fb651913eaf845410b321"


DEFAULT16_GOLDEN = "dac756ecd34152d815e430a946fc996a5d2ad94301f6401d4ff6147e8b5de0f0"
DEFAULT16_INDICES = tuple(i + j for i in (0, 32, 64, 96) for j in range(4))


def run_default16() -> dict:
    """Exploratory original default1024 16-world evaluation, NO selection.

    Source-bound opt-in spawn worker handling under the same parent writer
    lock; this DOES NOT write a partial journal or run D16 science.
    """
    rows = []
    for worker_count in (1, 2, 4):
        opt = SteadyStateOptimizer.from_defaults(base_seed=0)
        with TemporaryDirectory(prefix=f"perf226-default16-{worker_count}-") as tmp:
            lock_path = Path(tmp) / "journal.writer.lock"
            with lock_path.open("a+b") as writer:
                fcntl.flock(writer.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                start = time.perf_counter()
                if worker_count == 1:
                    for index in DEFAULT16_INDICES:
                        opt._evaluate_slot(opt.slots[index])
                else:
                    with SpawnEvaluator(
                        opt.to_snapshot(), workers=worker_count,
                        budget=ResourceBudget(1536), lock_path=lock_path,
                    ) as pool:
                        # Parent authentication and native ordering, no
                        # partial selection or journal checkpoint yet.
                        records = pool.evaluate(DEFAULT16_INDICES)
                        for index in DEFAULT16_INDICES:
                            previous = opt.slots[index]
                            candidate = UniverseSlot.from_dict(
                                records[index], base_config=opt.base_config,
                            )
                            if (
                                candidate.index != index or
                                candidate.seed != previous.seed or
                                candidate.category != previous.category or
                                candidate.genome_key != previous.genome_key
                            ):
                                raise AssertionError("default16 worker native identity drift")
                            opt.slots[index] = candidate
                elapsed = time.perf_counter() - start
                fcntl.flock(writer.fileno(), fcntl.LOCK_UN)
        snapshot_hash = digest(opt.to_snapshot())
        if snapshot_hash != DEFAULT16_GOLDEN:
            raise AssertionError("default1024 mixed16 full optimizer state differs")
        rows.append({
            "workers": worker_count,
            "wall_seconds": elapsed,
            "selected_step_executed": False,
            "whole_optimizer_digest": snapshot_hash,
        })
    return {
        "type": "default1024_seed0_original_mixed_category_16_worlds",
        "no_partial_journal_committed": True,
        "results": rows,
        "speed_ratios": {
            "workers2": rows[0]["wall_seconds"] / rows[1]["wall_seconds"],
            "workers4": rows[0]["wall_seconds"] / rows[2]["wall_seconds"],
        },
    }


def run() -> dict:
    report = []
    for workers in (1, 2, 4):
        with TemporaryDirectory(prefix=f"perf226-journal-{workers}-") as d:
            source = subprocess.check_output(
                ["git","rev-parse","HEAD"],text=True,timeout=10,
            ).strip()
            started=time.perf_counter()
            result=execute_selected_round(
                Path(d)/"journal", source_commit=source, base_seed=0,
                experiment=ExperimentConfig(evaluation_timeout_generations=2),
                evaluation_batch_size=16, workers=workers, memory_mib=1536,
            )
            wall=time.perf_counter()-started
            if (result["final_digest"]!=GOLDEN or
                digest(result["final_snapshot"])!=GOLDEN or
                result["new_evaluations"]!=128 or
                not result["final_committed"]):
                raise AssertionError("real D15 selected result/golden mismatch")
            record={
                "workers":workers,
                "wall_total_including_journal_s":wall,
                "d15_internal_wall_s":result["elapsed_wall_seconds"],
                "parent_peak_rss_bytes":result["peak_rss_bytes"],
                "worker_peak_aggregate_rss_bytes":result.get("peak_aggregate_rss_bytes"),
                "worker_hard_virtual_cap_bytes":result.get("worker_hard_virtual_cap_bytes"),
                "journal_bytes":result["journal_bytes"],
                "checkpoints":result["checkpoint_writes"],
                "selected128_digest":result["final_digest"],
            }
            report.append(record)
    return {
        "kind":"PERF226_true_D15_journal_128_short_A_B",
        "source_sha":subprocess.check_output(
            ["git","rev-parse","HEAD"],text=True,timeout=10,
        ).strip(),
        "cpu_count":os.cpu_count(),
        "python":platform.python_version(),
        "platform":platform.platform(),
        "results":report,
        "same_run_speed_ratios":{
            "workers2":report[0]["wall_total_including_journal_s"]/
                       report[1]["wall_total_including_journal_s"],
            "workers4":report[0]["wall_total_including_journal_s"]/
                       report[2]["wall_total_including_journal_s"],
        },
        "default1024_16slot_under_parent_lock":run_default16(),
        "D16_seed16384_long_science":False,
        "learning_claim":False,
    }


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=run()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",
                        encoding="utf-8")
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
