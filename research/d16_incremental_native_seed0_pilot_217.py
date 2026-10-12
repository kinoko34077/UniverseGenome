"""D16.10 PR-only REAL native128 incremental-stage integration, exposed seed0.

Two DIFFERENT GitHub-hosted jobs execute source-native D15 selection exactly
once each, with source-locked D16 completed native ledger and immutable receipt.
No original reserved D16 seed16384 evolution or scientific outcome is run here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d16_complete_round_checkpoint_217 import (
    one_authentic_selected_round, read_completed,
)
from research.d16_incremental_stage_executor_217 import DormantIncrementalStage
from research.d16_twojob_run_control_217 import (
    D16BoundaryError, canonical_bytes, utc_now_ms,
)
from search.evolution import SteadyStateOptimizer

FIXTURE_SEED = 0
FROZEN_V7 = (
    "725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63",
    "abe281245d5a45e78dcce3eab9e9f787b6260f365fa868da5ef13c2db3262112",
)


def source_sha() -> str:
    value = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=10,
    ).strip()
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise D16BoundaryError("pinned exact science-source checkout required")
    return value


def genesis() -> dict:
    return SteadyStateOptimizer.from_defaults(
        base_seed=FIXTURE_SEED,
        experiment=ExperimentConfig(),
        base_config=PhysicsConfig(),
    ).to_snapshot()


def report_file(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(report) + b"\n")


def execute(stage_number: int, *, inbound: Path | None, out: Path) -> dict:
    if stage_number not in (1, 2):
        raise D16BoundaryError("fixture has strictly two hosted stages")
    if (stage_number == 1 and inbound is not None
            or stage_number == 2 and inbound is None):
        raise D16BoundaryError("immutable preceding hosted stage required only for job2")
    monotonic_start = time.monotonic()
    source = source_sha()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if stage_number == 1:
        source_folder = out
        anchor = utc_now_ms()
        manifest = None
    else:
        source_folder = Path(inbound)
        manifest = json.loads((source_folder/"stage1-manifest.json").read_bytes())
        anchor = manifest["first_job_start_unix_ms"]

    def native(ordinal, previous, clock):
        return one_authentic_selected_round(
            source_sha=source, seed=FIXTURE_SEED,
            ordinal=ordinal, predecessor=previous,
            experiment=ExperimentConfig(), physics=PhysicsConfig(),
            clock=clock, job_started_monotonic=monotonic_start, workers=4,
        )

    stage = DormantIncrementalStage.open(
        folder=source_folder, source_sha=source,
        seed=FIXTURE_SEED, job=stage_number,
        original_genesis=genesis(), study_started_unix_ms=anchor,
        now_unix_ms=utc_now_ms,
        local_elapsed_ms=lambda: int((time.monotonic()-monotonic_start)*1000),
        native_completed_evaluator=native,
        source_bound_inbound_manifest=manifest,
    )
    result = stage.run_to_stage_end()
    target = 1 if stage_number == 1 else 2
    accepted = read_completed(
        source_folder/f"selected-round-{target:02d}.json",
        source_sha=source, seed=FIXTURE_SEED, ordinal=target,
    )
    if accepted["selected_v7_sha256"] != FROZEN_V7[target-1]:
        raise D16BoundaryError("exposed seed0 native selected-v7 golden changed")
    if accepted["d15_verified_observer"]["d15_journal_chain_verified"] is not True:
        raise D16BoundaryError("original native D15 ledger missing")
    if stage_number == 1:
        if result.result != "HANDOFF_READY":
            raise D16BoundaryError("one authentic native round required before job2")
        report_file(source_folder/"stage1-manifest.json", stage.verified_handoff())
        status = "EXPOSED_SEED0_HOST1_TRANSFER"
    else:
        if result.result != "FIXTURE_COMPLETE_NO_SCIENCE":
            raise D16BoundaryError("seed0 native fixture must never report science")
        for kind in ("round", "receipt"):
            source_path=source_folder/f"selected-{kind}-02.json"
            shutil.copyfile(source_path, out/source_path.name)
        status = "EXPOSED_SEED0_2_HOSTED_JOBS_PASS"
    report={
        "status": status, "source_sha":source,
        "selected_round":result.selected_round,
        "native_v7_sha256":accepted["selected_v7_sha256"],
        "global_elapsed_ms":result.last_global_elapsed_ms,
        "original_native128_and_D15_journal_verified":True,
        "learning_claim":False, "real_original_seed16384_executed":False,
    }
    report_file(out/"seed0-incremental-verdict.json",report)
    print(json.dumps(report,sort_keys=True),flush=True)
    return report


def main():
    p=argparse.ArgumentParser(description="D16.10 TEST-ONLY fixed seed0 genuine native128")
    p.add_argument("--stage",type=int,choices=(1,2),required=True)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--inbound",type=Path)
    a=p.parse_args()
    execute(a.stage,inbound=a.inbound,out=a.out)


if __name__ == "__main__":
    main()
