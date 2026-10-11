"""D16.6 PR-only TWO-hosted-job integration fixture (EXPOSED PERFORMANCE SEED 0).

This executable has NO seed flag and MUST NOT run original D16 seed16384.
Stage 1/2 each evaluate exactly one genuine default1024 native128 selected
round with accepted source-native D15 and authenticated read-only D16 observer.
The actual 20+20 seed16384 research remains unlaunched/unauthorized here.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import time

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d16_complete_round_checkpoint_217 import (
    one_authentic_selected_round, write_completed_atomic, read_completed,
)
from research.d16_twojob_run_control_217 import (
    D16BoundaryError, GlobalClock, make_transfer, accept_transfer,
    hash_of, utc_now_ms, canonical_bytes,
)
from research.d16_twojob_stage_fsm_217 import StageState
from search.evolution import SteadyStateOptimizer

FIXTURE_SEED = 0
FROZEN_NATIVE_V7 = (
    "725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63",
    "abe281245d5a45e78dcce3eab9e9f787b6260f365fa868da5ef13c2db3262112",
)


def source_sha() -> str:
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True,
                                  timeout=10).strip()
    if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise D16BoundaryError("immutable checked-out source SHA required")
    return sha


def original_genesis() -> dict:
    return SteadyStateOptimizer.from_defaults(
        base_seed=FIXTURE_SEED, experiment=ExperimentConfig(),
        base_config=PhysicsConfig(),
    ).to_snapshot()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def check_stage1_evidence(complete: dict, manifest: dict, *, source: str) -> None:
    """Read actual selected journal observation, not just a plausible SHA."""
    ledger = complete.get("d15_verified_observer")
    if (
        complete.get("ordinal") != 1
        or complete.get("seed") != FIXTURE_SEED
        or complete.get("source_sha") != source
        or complete.get("selected_v7_sha256") != FROZEN_NATIVE_V7[0]
        or not isinstance(ledger, dict)
        or ledger.get("selected_post_v7_sha256") != FROZEN_NATIVE_V7[0]
        or ledger.get("evaluated_native_worlds") != 128
        or ledger.get("selected_native_worlds") != 128
        or ledger.get("d15_journal_chain_verified") is not True
        or ledger.get("original_selected_once_proven_by_D15_final") is not True
        or manifest.get("observer_ledger_sha256") != hash_of(ledger)
        or manifest.get("elapsed_global_ms", -1) < complete.get("global_wall_ms", 10**20)
    ):
        raise D16BoundaryError("actual D15 stage1 observed ledger not verified")


def run_first(destination: Path) -> dict:
    source = source_sha()
    job_start = time.monotonic()
    clock = GlobalClock(utc_now_ms())
    genesis = original_genesis()
    stage = StageState.start(source_sha=source, seed=FIXTURE_SEED,
                             original_genesis=genesis,
                             job1_start_unix_ms=clock.study_started_unix_ms)
    complete = one_authentic_selected_round(
        source_sha=source, seed=FIXTURE_SEED,
        ordinal=1, predecessor=genesis,
        experiment=ExperimentConfig(), physics=PhysicsConfig(),
        clock=clock, job_started_monotonic=job_start, workers=4,
    )
    if complete["selected_v7_sha256"] != FROZEN_NATIVE_V7[0]:
        raise D16BoundaryError("original seed0 selected round1 v7 golden diverged")
    stage = stage.append(
        complete=complete, now_unix_ms=utc_now_ms(),
        local_elapsed_ms=int((time.monotonic()-job_start)*1000),
    )
    if stage.result != "HANDOFF_READY":
        raise D16BoundaryError("source-native round1 stage must be handoff ready")
    destination.mkdir(parents=True, exist_ok=True)
    checkpoint_file = write_completed_atomic(destination, complete)
    restored = read_completed(checkpoint_file, source_sha=source,
                              seed=FIXTURE_SEED, ordinal=1)
    manifest = make_transfer(
        source_sha=source, selected_snapshot=restored["selected_snapshot"],
        seed=FIXTURE_SEED, selected_round=1, clock=clock,
        now_unix_ms=utc_now_ms(),
        local_elapsed_ms=int((time.monotonic()-job_start)*1000),
        observer_selected_digest=restored["selected_v7_sha256"],
        ledger_sha=hash_of(restored["d15_verified_observer"]),
    )
    check_stage1_evidence(restored, manifest, source=source)
    write_json(destination/"stage1-manifest.json", manifest)
    return {"status": "FIXTURE_JOB1_HANDOFF_READY", "source": source,
            "native_v7": FROZEN_NATIVE_V7[0], "learning_claim": False,
            "real_original_seed16384_executed": False}


def run_second(inbound: Path, destination: Path) -> dict:
    source = source_sha()
    job_start = time.monotonic()
    original = json.loads((inbound/"stage1-manifest.json").read_bytes())
    previous = read_completed(
        inbound/"selected-round-01.json", source_sha=source,
        seed=FIXTURE_SEED, ordinal=1,
    )
    check_stage1_evidence(previous, original, source=source)
    clock = accept_transfer(
        manifest=original, snapshot=previous["selected_snapshot"],
        actual_source=source, expected_seed=FIXTURE_SEED,
        expected_selected_round=1, now_unix_ms=utc_now_ms(),
    )
    state = StageState.start(
        source_sha=source, seed=FIXTURE_SEED,
        original_genesis=original_genesis(),
        job1_start_unix_ms=clock.study_started_unix_ms,
    )
    state = state.append(
        complete=previous,
        now_unix_ms=clock.study_started_unix_ms+original["elapsed_global_ms"],
        local_elapsed_ms=0,
    )
    state = state.accept_second_job(
        verified_selected20_v7=previous["selected_v7_sha256"],
        clock_from_immutable_manifest=clock,
        now_unix_ms=utc_now_ms(),
    )
    complete = one_authentic_selected_round(
        source_sha=source, seed=FIXTURE_SEED,
        ordinal=2, predecessor=previous["selected_snapshot"],
        experiment=ExperimentConfig(), physics=PhysicsConfig(),
        clock=clock, job_started_monotonic=job_start, workers=4,
    )
    if complete["selected_v7_sha256"] != FROZEN_NATIVE_V7[1]:
        raise D16BoundaryError("original seed0 selected round2 v7 golden diverged")
    state = state.append(
        complete=complete, now_unix_ms=utc_now_ms(),
        local_elapsed_ms=int((time.monotonic()-job_start)*1000),
    )
    if state.result != "FIXTURE_COMPLETE_NO_SCIENCE":
        raise D16BoundaryError("two real original seed0 rounds are only a test fixture")
    destination.mkdir(parents=True, exist_ok=True)
    path = write_completed_atomic(destination, complete)
    reloaded = read_completed(path,source_sha=source,seed=FIXTURE_SEED,ordinal=2)
    if reloaded["selected_v7_sha256"] != FROZEN_NATIVE_V7[1]:
        raise D16BoundaryError("persisted selected2 checksum mismatch")
    report = {
        "status": state.result, "source": source,
        "last_original_selected_round": 2,
        "original_selected_native128_each_round": True,
        "selected_v7_round1": FROZEN_NATIVE_V7[0],
        "selected_v7_round2": FROZEN_NATIVE_V7[1],
        "global_elapsed_ms_includes_hosted_handoff": state.last_global_elapsed_ms,
        "learning_claim": False,
        "real_original_seed16384_executed": False,
    }
    write_json(destination/"fixture-verdict.json", report)
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="TEST ONLY original seed0 full native128")
    p.add_argument("--stage", choices=("first", "second"), required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--inbound", type=Path)
    args = p.parse_args()
    if args.stage == "first":
        if args.inbound is not None:
            p.error("stage1 cannot import prior artifacts")
        output = run_first(args.out)
    else:
        if args.inbound is None:
            p.error("stage2 needs completed stage1 artifacts")
        output = run_second(args.inbound,args.out)
    print(json.dumps(output, sort_keys=True),flush=True)


if __name__ == "__main__":
    main()
