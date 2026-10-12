"""D16 #217 source-native ORIGINAL seed16384 128-world / two-job study program.

Not a workflow/dispatcher. This CLI has no implicit invocation on push/PR and
must only be attached to a separately authorized, source-frozen and reviewed
two-job public Actions launch. It must not run at module import.

Stage 1: original selections 1..20; stage 2: original 21..37..40, stopping
on verified same-category mature native replacement or negative at40. Never
alter physics, genetic fitness/selection/RNG, population, seed or horizon.
An interrupted hosted job is terminal INCOMPLETE; no third hosted job.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import uuid
from typing import Any

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d16_complete_round_checkpoint_217 import (
    one_authentic_selected_round, read_completed,
)
from research.d16_incremental_stage_executor_217 import (
    DormantIncrementalStage, retained_bytes, MAX_RETAINED_STUDY_BYTES,
)
from research.d16_twojob_run_control_217 import (
    D16BoundaryError, canonical_bytes, hash_of, utc_now_ms,
)
from search.evolution import SteadyStateOptimizer

ORIGINAL_SEED = 16384
STAGE1_END = 20
MAX_ROUNDS = 40
REPORT_SCHEMA = "D16_ORIGINAL_SOURCE_NATIVE_TWO_HOST_SCIENCE_V1"


def source_sha() -> str:
    value = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=10,
    ).strip()
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise D16BoundaryError("exact frozen original research source SHA required")
    return value


def original_genesis() -> dict[str, Any]:
    return SteadyStateOptimizer.from_defaults(
        base_seed=ORIGINAL_SEED,
        experiment=ExperimentConfig(),
        base_config=PhysicsConfig(),
    ).to_snapshot()


def persist_json(path: Path, value: dict[str, Any]) -> None:
    """Atomically replace summary; unlike immutable native selected receipts."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name("." + path.name + "-" + uuid.uuid4().hex)
    try:
        with temp.open("xb") as stream:
            stream.write(canonical_bytes(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def original_observation(complete: dict[str, Any]) -> dict[str, Any]:
    """Per-round native observation: source physics evidence, not learning."""
    observer = complete["d15_verified_observer"]
    categories = observer["categories"]
    return {
        "ordinal": complete["ordinal"],
        "selected_v7_sha256": complete["selected_v7_sha256"],
        "original_d15_observer_sha256": hash_of(observer),
        "source_sha": complete["source_sha"],
        "seed": complete["seed"],
        "evaluated_native_worlds": observer["evaluated_native_worlds"],
        "selected_once_native": observer["original_selected_once_proven_by_D15_final"],
        "original_actual_native_replacements":
            observer["actual_native_replacement_count"],
        "native_retirements": observer["native_retirements"],
        "categories": categories,
        "before_diversity": observer["before_diversity"],
        "after_diversity": observer["after_diversity"],
        "journal_bytes": complete["d15_journal_bytes"],
        "sampled_aggregate_rss_bytes": complete["rss_sampled_bytes"],
        "global_elapsed_ms": complete["global_wall_ms"],
    }


def check_inbound_rows(folder: Path, *, source: str, report: dict) -> None:
    """Round1..20 reports must describe the SAME authentic selected receipts."""
    rows = report.get("rounds")
    if (report.get("schema") != REPORT_SCHEMA
            or report.get("seed") != ORIGINAL_SEED
            or report.get("source_sha") != source
            or report.get("status") != "HANDOFF_READY"
            or not isinstance(rows, list) or len(rows) != STAGE1_END):
        raise D16BoundaryError("original first-host scientific progress report invalid")
    for ordinal, row in enumerate(rows, 1):
        complete = read_completed(
            folder/f"selected-round-{ordinal:02d}.json",
            source_sha=source,seed=ORIGINAL_SEED,ordinal=ordinal,
        )
        if row != original_observation(complete):
            raise D16BoundaryError("original first-host category/prune/diversity report drift")


def execute(*, job: int, out: Path, inbound: Path | None = None) -> dict:
    """Explicit caller-only ORIGINAL science. No auto-trigger or retry."""
    if type(job) is not int or job not in (1,2):
        raise D16BoundaryError("D16 science exactly two hosted jobs, never third")
    if (job == 1 and inbound is not None
            or job == 2 and inbound is None):
        raise D16BoundaryError("source-locked previous complete first-host stage required")
    out = Path(out)
    out.mkdir(parents=True,exist_ok=True)
    local_start = time.monotonic()
    source = source_sha()
    if job == 1:
        folder=out
        started=utc_now_ms()
        manifest=None
        rows=[]
    else:
        folder=Path(inbound)
        manifest=json.loads((folder/"stage1-manifest.json").read_bytes())
        started=manifest["first_job_start_unix_ms"]
        previous=json.loads((folder/"partial-report.json").read_bytes())
        check_inbound_rows(folder, source=source, report=previous)
        rows=list(previous["rounds"])

    def actual_native_selected(ordinal, previous, clock):
        return one_authentic_selected_round(
            source_sha=source, seed=ORIGINAL_SEED, ordinal=ordinal,
            predecessor=previous, experiment=ExperimentConfig(),
            physics=PhysicsConfig(), clock=clock,
            job_started_monotonic=local_start, workers=4,
        )

    stage = DormantIncrementalStage.open(
        folder=folder, source_sha=source, seed=ORIGINAL_SEED, job=job,
        original_genesis=original_genesis(),
        study_started_unix_ms=started,
        now_unix_ms=utc_now_ms,
        local_elapsed_ms=lambda: int((time.monotonic()-local_start)*1000),
        native_completed_evaluator=actual_native_selected,
        source_bound_inbound_manifest=manifest,
    )
    if (job == 1 and stage.stage.selected_round > STAGE1_END
            or job == 2 and stage.stage.selected_round < STAGE1_END):
        raise D16BoundaryError("original 20+20 launch boundary corrupt")

    report={
        "schema":REPORT_SCHEMA,
        "source_sha":source, "seed":ORIGINAL_SEED, "job":job,
        "first_job_start_unix_ms":started,
        "native_worlds_per_selected_round":128, "categories":4,
        "experiment_sha256":hash_of(ExperimentConfig().to_dict()),
        "physics_sha256":hash_of(PhysicsConfig().to_dict()),
        "learning_claim":False, "independent_generalization_claim":False,
        "original_completed_selected_seed16384_rounds":len(rows), "rounds":rows,
        "status":"IN_PROGRESS",
    }
    report_path=folder/"partial-report.json"
    persist_json(report_path,report)
    while stage.stage.result == "IN_PROGRESS":
        accepted=stage.advance()
        complete=read_completed(
            accepted.selected_file, source_sha=source,seed=ORIGINAL_SEED,
            ordinal=accepted.last_completed_selected_round,
        )
        row=original_observation(complete)
        if row["ordinal"] != len(rows)+1:
            raise D16BoundaryError("original selected scientific report ordinal drift")
        rows.append(row)
        report["last_completed_selected_round"]=row["ordinal"]
        report["original_completed_selected_seed16384_rounds"]=len(rows)
        report["global_elapsed_ms"]=stage.stage.last_global_elapsed_ms
        report["original_native_replacements_total"]=sum(
            r["original_actual_native_replacements"] for r in rows
        )
        report["retained_bytes"]=retained_bytes(folder)
        persist_json(report_path,report)
        print(json.dumps({
            "selected_round":row["ordinal"],
            "global_seconds":report["global_elapsed_ms"]/1000,
            "original_replacements_this_round":
                row["original_actual_native_replacements"],
        },sort_keys=True),flush=True)

    status = stage.stage.result
    report["status"] = status
    report["last_completed_selected_round"] = stage.stage.selected_round
    report["global_elapsed_ms"] = stage.stage.last_global_elapsed_ms
    report["completed_37_rounds_by_1200"] = (
        len(rows)>=37 and rows[36]["global_elapsed_ms"]<=1200000
    )
    report["science_terminal"] = status in ("OBSERVED_FINAL","NOT_OBSERVED_FINAL")
    report["science_1200_target_met"] = (
        report["science_terminal"] and report["global_elapsed_ms"]<=1200000
    )
    report["stretch_900_met"] = (
        report["science_terminal"] and report["global_elapsed_ms"]<=900000
    )
    report["timing_classification"] = (
        "TARGET_1200_MET" if report["science_1200_target_met"] else
        "TARGET_1200_MISSED" if report["science_terminal"] else
        "NO_TERMINAL_SCIENCE_RESULT"
    )
    report["retained_bytes"]=retained_bytes(folder)
    if report["retained_bytes"] > MAX_RETAINED_STUDY_BYTES:
        raise D16BoundaryError("whole-study retained evidence exceeded512MiB")
    persist_json(report_path,report)
    if job == 1:
        if status!="HANDOFF_READY" or len(rows)!=STAGE1_END:
            raise D16BoundaryError("first hosted job must stop only at original20")
        persist_json(folder/"stage1-manifest.json",stage.verified_handoff())
    elif not report["science_terminal"] or not 37<=len(rows)<=MAX_ROUNDS:
        raise D16BoundaryError("no authentic terminal original science result")
    if job==2:
        persist_json(out/"science-verdict.json",report)
    print(json.dumps({
        "status":status,"rounds":len(rows),"source_sha":source,
        "global_seconds":report["global_elapsed_ms"]/1000,
        "learning_claim":False,"science_terminal":report["science_terminal"],
    },sort_keys=True),flush=True)
    return report


def main() -> None:
    p=argparse.ArgumentParser(description="D16 original native selected128 two hosted jobs")
    p.add_argument("--job",type=int,choices=(1,2),required=True)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--inbound",type=Path)
    a=p.parse_args()
    try:
        execute(job=a.job,out=a.out,inbound=a.inbound)
    except Exception as exc:
        # Even if complete selected-prefix evidence is present after an
        # interrupted/error stage, this is not a scientific terminal result.
        persist_json(a.out/"incomplete-failure.json",{
            "schema":REPORT_SCHEMA,"seed":ORIGINAL_SEED,
            "job":a.job,"status":"BUDGET_OR_INTEGRITY_BOUND_INCOMPLETE",
            "failure_type":type(exc).__name__,
            "learning_claim":False,"science_terminal":False,
        })
        raise


if __name__ == "__main__":
    main()
