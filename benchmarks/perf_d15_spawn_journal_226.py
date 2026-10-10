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

from core.experiment import ExperimentConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d8_genome_diversity_190 import digest

GOLDEN = "0ad8268476bf79f3c9db02a91ebf92dba3250339571fb651913eaf845410b321"


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
