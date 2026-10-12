"""PERF230 P5.4: actual 37 native selected128 DEFAULT1024 rounds, TWO hosted jobs.

PR-ONLY PERFORMANCE FIXTURE. Fixed already-exposed benchmark seed0 and genuine
D15 physics/selection, no reserved D16 original study seed16384, no learning.
20 full original selected128 rounds in hosted job1, then17 in job2; source
commit/first-job clock/completed full-v7 states are transferred immutably.
Do not merge this performance-only harness as the original science runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d16_complete_round_checkpoint_217 import (
    one_authentic_selected_round, read_completed, write_completed_atomic,
)
from research.d16_twojob_run_control_217 import (
    D16BoundaryError, GlobalClock, canonical_bytes, utc_now_ms,
)
from search.evolution import SteadyStateOptimizer

SEED = 0
FINAL_ROUND = 37
SPLIT = 20
MAX_RETAINED = 512 * 1024 * 1024
FROZEN_FIRST_FOUR = (
    "725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63",
    "abe281245d5a45e78dcce3eab9e9f787b6260f365fa868da5ef13c2db3262112",
    "0ac1086caa69775a630165c2dab161513b240a63993e4f53a1be9b33688251f2",
    "b06e987f5dffbb114362be88bac56da7a1a00d1e1e60f18368c0fc78a3a7cc10",
)
KIND = "PERF230_P54_EXPOSED_SEED0_37_FULL_NATIVE128_2JOBS_900S_CHECK"


def sha() -> str:
    a = subprocess.check_output(["git","rev-parse","HEAD"], text=True,
                                timeout=10).strip()
    if len(a) != 40 or any(c not in "0123456789abcdef" for c in a):
        raise D16BoundaryError("pinned checkout SHA required")
    return a


def write_json(path: Path, x: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp=path.with_name(path.name+".tmp")
    temp.write_bytes(canonical_bytes(x)+b"\n")
    os.replace(temp,path)


def genesis() -> dict:
    return SteadyStateOptimizer.from_defaults(
        base_seed=SEED,experiment=ExperimentConfig(),base_config=PhysicsConfig(),
    ).to_snapshot()


def used_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in path.glob("*") if p.is_file())


def prefix_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(*, stage: int, out: Path, incoming: Path | None = None) -> dict[str, Any]:
    if stage not in (1,2):
        raise D16BoundaryError("exactly two immutable perf-only stages")
    out=Path(out)
    start_mono=time.monotonic()
    source=sha()
    if stage==1:
        if incoming is not None:
            raise D16BoundaryError("stage1 may not import old experiment")
        clock=GlobalClock(utc_now_ms())
        prior=None
        rows=[]
        begin,end=1,SPLIT
    else:
        if incoming is None:
            raise D16BoundaryError("stage2 requires fully committed stage1 artifacts")
        incoming=Path(incoming)
        manifest=json.loads((incoming/"stage1-manifest.json").read_bytes())
        if (manifest.get("kind") != KIND
                or manifest.get("source_sha") != source or manifest.get("seed") != SEED
                or manifest.get("first_last_round") != SPLIT
                or not isinstance(manifest.get("rounds"),list)
                or len(manifest["rounds"]) != SPLIT):
            raise D16BoundaryError("stage1 source/seed/round count mismatch")
        # Audit every original completed-selected checkpoint and exact
        # canonical file digest before treating job1 result as transferable.
        for index, meta in enumerate(manifest["rounds"],start=1):
            path=incoming/f"selected-round-{index:02d}.json"
            if (meta.get("ordinal") != index
                    or meta.get("selected_file_sha256") != prefix_sha(path)):
                raise D16BoundaryError("missing/nonconsecutive or changed stage1 evidence")
            verified=read_completed(path,source_sha=source,seed=SEED,ordinal=index)
            if (verified["selected_v7_sha256"] != meta.get("selected_v7_sha256")
                    or verified["d15_verified_observer"].get("selected_post_v7_sha256")
                    != meta.get("selected_v7_sha256")):
                raise D16BoundaryError("stage1 original source D15 native evidence mismatch")
        prior=read_completed(
            incoming/f"selected-round-{SPLIT:02d}.json",
            source_sha=source,seed=SEED,ordinal=SPLIT,
        )["selected_snapshot"]
        clock=GlobalClock(manifest["study_started_unix_ms"],
                          manifest["elapsed_global_ms"])
        clock.check(now_unix_ms=utc_now_ms(),local_elapsed_ms=0)
        rows=list(manifest["rounds"])
        begin,end=SPLIT+1,FINAL_ROUND
    out.mkdir(parents=True,exist_ok=True)
    report={
        "kind":KIND,"source_sha":source,"seed":SEED,"original_native128":True,
        "original_default1024":True,"original_jobs":2,"split":SPLIT,
        "study_started_unix_ms":clock.study_started_unix_ms,
        "completion":"IN_PROGRESS","learning_claim":False,
        "real_original_seed16384_executed":False,
        "rounds":rows,
    }
    write_json(out/"partial-report.json",report)
    for number in range(begin,end+1):
        local=int((time.monotonic()-start_mono)*1000)
        clock.check(now_unix_ms=utc_now_ms(),local_elapsed_ms=local)
        t0=time.monotonic()
        complete=one_authentic_selected_round(
            source_sha=source,seed=SEED,ordinal=number,predecessor=prior,
            experiment=ExperimentConfig(),physics=PhysicsConfig(),
            clock=clock,job_started_monotonic=start_mono,workers=4,
        )
        if number <=4 and complete["selected_v7_sha256"] != FROZEN_FIRST_FOUR[number-1]:
            raise D16BoundaryError("original frozen native selected SHA drift")
        file=write_completed_atomic(out,complete)
        # Full completed and sha-verified original selected native state,
        # never store a partial D15 evaluated-world patch as selected.
        restored=read_completed(file,source_sha=source,seed=SEED,ordinal=number)
        if restored["selected_v7_sha256"] != complete["selected_v7_sha256"]:
            raise D16BoundaryError("completed immutable selected state changed")
        row={
            "ordinal":number,"source_sha":source,
            "selected_v7_sha256":complete["selected_v7_sha256"],
            "selected_file_sha256":prefix_sha(file),
            "full_native_worlds":128,
            "journal_bytes":complete["d15_journal_bytes"],
            "sampled_aggregate_rss_bytes":complete["rss_sampled_bytes"],
            "real_original_selection_count":1,
            "actual_native_retirements_perf_only":
                complete["d15_verified_observer"]["actual_native_replacement_count"],
            "round_wall_seconds":time.monotonic()-t0,
        }
        rows.append(row)
        prior=complete["selected_snapshot"]
        report["global_elapsed_ms"] = clock.check(
            now_unix_ms=utc_now_ms(),
            local_elapsed_ms=int((time.monotonic()-start_mono)*1000),
        )
        report["retained_bytes_current_job"]=used_bytes(out)
        aggregate_retained = report["retained_bytes_current_job"] + (
            used_bytes(incoming) if stage == 2 and incoming is not None else 0
        )
        report["retained_bytes_whole_twojob_study"] = aggregate_retained
        if aggregate_retained > MAX_RETAINED:
            raise D16BoundaryError("whole two-job retained original evidence exceeded 512MiB")
        write_json(out/"partial-report.json",report)
        print(json.dumps({"number":number,
                          "round_wall_seconds":row["round_wall_seconds"],
                          "global_seconds":report["global_elapsed_ms"]/1000},
                         sort_keys=True),flush=True)

    clock_ms=clock.check(now_unix_ms=utc_now_ms(),
                         local_elapsed_ms=int((time.monotonic()-start_mono)*1000))
    if stage==1:
        manifest={
            "kind":KIND,"source_sha":source,"seed":SEED,
            "first_last_round":SPLIT,
            "study_started_unix_ms":clock.study_started_unix_ms,
            "elapsed_global_ms":clock_ms,"rounds":rows,
            "learning_claim":False,
            "real_original_seed16384_executed":False,
        }
        write_json(out/"stage1-manifest.json",manifest)
        report["completion"]="STAGE1_COMPLETE_TRANSFER_READY"
    else:
        report["completion"]="COMPLETE_37_ORIGINAL_SELECTED128_PERFORMANCE_ONLY"
        report["global_elapsed_ms"]=clock_ms
        report["global_seconds"]=clock_ms/1000
        report["stretch_900_met"]=clock_ms<=900*1000
        report["remaining_to_900_ms"]=max(0,clock_ms-900*1000)
        report["preferred_1200_met"]=clock_ms<=1200*1000
        report["hard_1800_met"]=clock_ms<=1800*1000
        report["learning_claim"]=False
        report["real_original_seed16384_executed"]=False
    write_json(out/"partial-report.json",report)
    print(json.dumps({
        "status":report["completion"],
        "source_sha":source,"rounds":len(rows),
        "global_seconds":clock_ms/1000,"target_900_met":
            clock_ms<=900*1000 if stage==2 else None,
        "target_1200_met":
            clock_ms<=1200*1000 if stage==2 else None,
        "real_original_seed16384_executed":False,
    },sort_keys=True),flush=True)
    return report


def main() -> None:
    p=argparse.ArgumentParser(description="PERF-only fixed seed0 original37 selected128")
    p.add_argument("--stage",type=int,choices=(1,2),required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--inbound",type=Path)
    a=p.parse_args()
    execute(stage=a.stage,out=a.out,incoming=a.inbound)


if __name__=="__main__":
    main()
