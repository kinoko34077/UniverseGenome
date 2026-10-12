"""D18 #294 dormant ORIGINAL new-seed49152 research runner, exactly two hosts.

NO implicit execution or GitHub dispatch. Explicit invocation only after a
separately reviewed, frozen, budget-limited workflow. Never rerun seed16384
or alter native physics, genetics, fitness, selection, RNG, or learner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import uuid
from typing import Any

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d16_twojob_run_control_217 import (
    D16BoundaryError, GlobalClock, canonical_bytes, hash_of, utc_now_ms,
)
from research.d18_native_journal_observer_294 import observe_completed_native_round
from research.d18_prospective_admission_294 import (
    SEARCH_SEED, MAX_AGGREGATE_RSS, MAX_JOURNAL_BYTES, MAX_RETAINED_BYTES,
    admit_completed_native_journal,
)
from research.d18_twohost_transcript_294 import OriginalD18Transcript
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

REPORT_KIND = "D18_ORIGINAL_SOURCE_NATIVE_SELECTED128_E1_E2_ROUND_V1"
MAX_ROUND_FILE = 32 * 1024 * 1024
STAGE1_LAST = 20
MAX_ROUNDS = 40


def need(value: bool, message: str) -> None:
    if not value:
        raise D16BoundaryError(message)


def source_sha() -> str:
    # Do not claim source parity when the checked-out commit is unknown.
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=10
    ).strip()
    need(len(sha) == 40 and all(c in "0123456789abcdef" for c in sha),
         "D18 source must be a real checked-out commit")
    return sha


def native_genesis() -> dict[str, Any]:
    """Construct immutable source defaults; no world simulation."""
    return SteadyStateOptimizer.from_defaults(
        base_seed=SEARCH_SEED,
        experiment=ExperimentConfig(),
        base_config=PhysicsConfig(),
    ).to_snapshot()


def durable_json(path: Path, value: dict[str, Any]) -> Path:
    """Atomic NO-REPLACE publication of one evidence record."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(value) + b"\n"
    need(len(data) <= MAX_ROUND_FILE, "D18 evidence record exceeds32MiB")
    staged = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with staged.open("xb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        # Do not silently overwrite successful evidence after a crash.
        os.link(staged, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        staged.unlink(missing_ok=True)
    return path


def load_json(path: Path) -> dict[str, Any]:
    path = Path(path)
    need(path.is_file() and not path.is_symlink()
         and path.stat().st_size <= MAX_ROUND_FILE,
         "missing or oversized source-original evidence")
    return json.loads(path.read_bytes())


def total_bytes(folder: Path) -> int:
    return sum(p.stat().st_size for p in Path(folder).iterdir() if p.is_file())


def validate_saved(
    folder: Path, *,
    source: str,
    ordinal: int,
    previous_sha: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Revalidate selected-v7, source identity, lineage, D15 witness receipt."""
    path = folder / f"selected-round-{ordinal:02d}.json"
    receipt = load_json(folder / f"selected-receipt-{ordinal:02d}.json")
    record = load_json(path)
    raw = path.read_bytes()
    need(record.get("kind") == REPORT_KIND and
         record.get("source_sha") == source and
         record.get("seed") == SEARCH_SEED and
         record.get("ordinal") == ordinal and
         record.get("job") == (1 if ordinal <= STAGE1_LAST else 2) and
         record.get("learning_claim") is False,
         "source-native selected evidence fields changed")
    need(receipt.get("source_sha") == source and
         receipt.get("seed") == SEARCH_SEED and
         receipt.get("ordinal") == ordinal and
         receipt.get("selected_file_sha256") == hashlib.sha256(raw).hexdigest(),
         "D18 immutable completed record receipt mismatched")
    selected = record.get("selected_snapshot")
    need(isinstance(selected, dict), "original complete selected-v7 snapshot absent")
    opt = SteadyStateOptimizer.from_snapshot(selected)
    observed_digest = digest(opt.to_snapshot())
    need(record.get("selected_v7_sha256") == observed_digest and
         receipt.get("selected_v7_sha256") == observed_digest and
         record.get("previous_selected_v7_sha256") == previous_sha and
         opt.generation == ordinal and
         opt.search_plan.scheduler_base_seed == SEARCH_SEED and
         len(opt.slots) == 128 and
         sorted(opt._category_counts().values()) == [32, 32, 32, 32] and
         opt.experiment.to_dict() == ExperimentConfig().to_dict() and
         opt.base_config.to_dict() == PhysicsConfig().to_dict(),
         "original source-native selected-v7/lineage/default physics mismatch")
    admission = record.get("admission")
    witness = record.get("d18_verified_observer")
    need(isinstance(admission, dict) and isinstance(witness, dict) and
         admission.get("selected_post_v7_sha256") == observed_digest and
         admission.get("source_sha") == source and
         admission.get("seed") == SEARCH_SEED and
         admission.get("ordinal") == ordinal and
         admission.get("E1_count") == witness.get("E1_growth_only_candidate_count") and
         admission.get("E2_count") == witness.get("E2_actual_growth_pruned_count") and
         receipt.get("d18_observer_sha256") == hash_of(witness),
         "D18 original preselection E1/actual E2 witness diverged")
    return selected, admission


def authenticate_stage1(folder: Path, source: str, *,
                        current_global_elapsed_ms: int,
                        stage1_manifest: dict[str, Any] | None = None
                        ) -> tuple[OriginalD18Transcript, dict[str, Any]]:
    """Independently replay EVERY original completed first20 row before host2."""
    manifest = stage1_manifest or load_json(folder / "stage1-manifest.json")
    need(manifest.get("source_sha") == source and
         manifest.get("seed") == SEARCH_SEED and
         manifest.get("job") == 1,
         "original new-seed first host source/seed changed")
    started = manifest.get("study_started_unix_ms")
    need(type(started) is int and started > 1600000000000,
         "D18 original study UTC start absent")
    clock = GlobalClock(started, manifest.get("last_global_elapsed_ms", -1))
    clock.check(now_unix_ms=started + current_global_elapsed_ms,
                local_elapsed_ms=0)
    state = OriginalD18Transcript.begin(source)
    prior = digest(native_genesis())
    for ordinal in range(1, 21):
        snapshot, admission = validate_saved(
            folder, source=source, ordinal=ordinal, previous_sha=prior
        )
        prior = digest(snapshot)
        state = state.append(admission)
    need(state.result == "HANDOFF_READY" and
         manifest.get("transcript") == state.stage1_manifest() and
         manifest["transcript"]["selected_v7_sha256"] == prior and
         manifest["last_global_elapsed_ms"] == state.rows[-1]["global_elapsed_ms"],
         "original full20 stage1 receipts/handoff not authenticated")
    return state, manifest


def single_original_round(
    *,
    source: str,
    ordinal: int,
    job: int,
    previous: dict[str, Any],
    study_started_unix_ms: int,
    prior_elapsed_ms: int,
    job_monotonic_start: float,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """ONE exact native D15 original selected128 from unchanged source."""
    need(type(job) is int and job in (1, 2) and
         (1 if ordinal <= STAGE1_LAST else 2) == job,
         "new-seed two-host stage invalid")
    monotonic_ms = lambda: int((time.monotonic() - job_monotonic_start) * 1000)
    GlobalClock(study_started_unix_ms, prior_elapsed_ms).check(
        now_unix_ms=utc_now_ms(), local_elapsed_ms=monotonic_ms()
    )
    with TemporaryDirectory(prefix="d18-real-original-D15-") as tmp:
        journal = Path(tmp) / "original-128"
        selected = execute_selected_round(
            journal,
            source_commit=source,
            base_seed=SEARCH_SEED,
            experiment=ExperimentConfig(),
            base_config=PhysicsConfig(),
            base_snapshot=previous,
            evaluation_batch_size=16,
            memory_mib=1536,
            max_journal_bytes=MAX_JOURNAL_BYTES,
            workers=4,
        )
        need(selected.get("new_evaluations") == 128 and
             selected.get("resumed_from") == 0 and
             selected.get("checkpoint_writes") == 8 and
             selected.get("final_committed") is True and
             selected.get("finalization_performed") is True and
             selected.get("journal_bytes", 2**64) <= MAX_JOURNAL_BYTES and
             type(selected.get("peak_aggregate_rss_bytes")) is int and
             selected["peak_aggregate_rss_bytes"] <= MAX_AGGREGATE_RSS and
             selected.get("final_digest") == digest(selected["final_snapshot"]),
             "actual original128 D15 evaluation, snapshot or RSS cap mismatch")
        observer = observe_completed_native_round(
            journal, source_commit=source
        )
        admission = admit_completed_native_journal(
            journal, source_sha=source, ordinal=ordinal, job=job,
            study_started_unix_ms=study_started_unix_ms,
            prior_elapsed_ms=prior_elapsed_ms,
            now_unix_ms=utc_now_ms(),
            local_elapsed_ms=monotonic_ms(),
        )
    return selected["final_snapshot"], admission, observer


def run_stage(*, job: int, out: Path, inbound: Path | None = None) -> dict[str, Any]:
    """Explicit CLI only; no scheduled invocation or automatic retry."""
    need(type(job) is int and job in (1, 2), "only two original D18 jobs")
    need((job == 1) == (inbound is None), "stage2 requires authentic inbound20")
    need(sys.implementation.name == "cpython" and
         sys.version_info[:2] == (3, 12),
         "D18 native science predeclared CPython3.12 (PyPy not accepted)")
    source = source_sha()
    out = Path(out)
    need(not out.exists() or not any(out.iterdir()),
         "original D18 source study destination must be empty")
    job_monotonic_start = time.monotonic()

    if job == 1:
        out.mkdir(parents=True, exist_ok=True)
        started = utc_now_ms()
        state = OriginalD18Transcript.begin(source)
        previous = native_genesis()
    else:
        inbound = Path(inbound)
        need(inbound.is_dir() and inbound.resolve() != out.resolve(),
             "missing independent original stage1 artifact")
        need(not any(x.is_symlink() or not x.is_file() for x in inbound.iterdir()),
             "original stage1 must contain only flat regular evidence")
        shutil.copytree(inbound, out, dirs_exist_ok=False)
        temporary_manifest = load_json(out / "stage1-manifest.json")
        started = temporary_manifest["study_started_unix_ms"]
        now_elapsed = utc_now_ms() - started
        first, source_manifest = authenticate_stage1(
            out, source, current_global_elapsed_ms=now_elapsed,
            stage1_manifest=temporary_manifest,
        )
        state = first.accept_second_host(
            source_manifest["transcript"], copied_rows=first.rows,
            current_global_elapsed_ms=now_elapsed,
        )
        previous, _ = validate_saved(
            out, source=source, ordinal=STAGE1_LAST,
            previous_sha=state.rows[-2]["selected_post_v7_sha256"],
        )

    while state.result == "IN_PROGRESS":
        ordinal = state.selected_round + 1
        prior_elapsed = state.rows[-1]["global_elapsed_ms"] if state.rows else 0
        prior_sha = digest(previous)
        snapshot, admission, witness = single_original_round(
            source=source, ordinal=ordinal, job=job,
            previous=previous, study_started_unix_ms=started,
            prior_elapsed_ms=prior_elapsed, job_monotonic_start=job_monotonic_start,
        )
        proposed = state.append(admission)
        record = {
            "kind":REPORT_KIND, "source_sha":source, "seed":SEARCH_SEED,
            "ordinal":ordinal, "job":job,
            "previous_selected_v7_sha256":prior_sha,
            "selected_snapshot":snapshot,
            "selected_v7_sha256":digest(snapshot),
            "admission":admission,
            "d18_verified_observer":witness,
            "learning_claim":False,
        }
        saved = durable_json(out / f"selected-round-{ordinal:02d}.json", record)
        durable_json(out / f"selected-receipt-{ordinal:02d}.json", {
            "source_sha":source, "seed":SEARCH_SEED,
            "ordinal":ordinal, "job":job,
            "selected_v7_sha256":digest(snapshot),
            "selected_file_sha256":hashlib.sha256(saved.read_bytes()).hexdigest(),
            "d18_observer_sha256":hash_of(witness),
        })
        verified_selected, verified_admission = validate_saved(
            out, source=source, ordinal=ordinal, previous_sha=prior_sha
        )
        need(verified_admission == admission and
             digest(verified_selected) == digest(snapshot),
             "D18 committed native selected evidence not replayable")
        need(total_bytes(out) <= MAX_RETAINED_BYTES,
             "whole original study retained evidence exceeds512MiB")
        previous = verified_selected
        state = proposed
        print(json.dumps({
            "original_selected_round":ordinal,
            "job":job,"status":state.result,
            "E1":admission["E1_count"],"E2":admission["E2_count"],
            "global_elapsed_ms":admission["global_elapsed_ms"],
            "source":source,
        },sort_keys=True),flush=True)

    if job == 1:
        need(state.result == "HANDOFF_READY" and state.selected_round == STAGE1_LAST,
             "D18 first hosted job must end only after complete native20")
        durable_json(out / "stage1-manifest.json", {
            "source_sha":source, "seed":SEARCH_SEED, "job":1,
            "study_started_unix_ms":started,
            "last_global_elapsed_ms":state.rows[-1]["global_elapsed_ms"],
            "transcript":state.stage1_manifest(),
        })
        return {"status":"HANDOFF_READY", "rounds":20, "source_sha":source}

    need(state.result in ("OBSERVED_E2_FINAL","E2_NOT_OBSERVED_FINAL") and
         37 <= state.selected_round <= MAX_ROUNDS,
         "D18 science cannot be terminal before original native maturity")
    terminal = state.verdict()
    terminal["original_verified_completed_rows"] = state.selected_round
    terminal["actual_original_native_E1_E2"] = True
    terminal["admission_rows_are_from_original_journal"] = True
    terminal["engine_changed"] = False
    durable_json(out / "science-verdict.json",terminal)
    return terminal


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job",type=int,choices=(1,2),required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--inbound",type=Path)
    args=parser.parse_args()
    try:
        result=run_stage(job=args.job,out=args.out,inbound=args.inbound)
        print(json.dumps(result,sort_keys=True),flush=True)
    except Exception as exc:
        # Fail-closed: preserve earlier published complete prefix, never invent
        # a third job or relaunch the source seed on another host.
        args.out.mkdir(parents=True,exist_ok=True)
        failure=args.out / "incomplete-failure.json"
        if not failure.exists():
            durable_json(failure,{
                "schema":"D18_ORIGINAL_TWOHOST_INCOMPLETE_V1",
                "job":args.job,"seed":SEARCH_SEED,
                "status":"BUDGET_OR_INTEGRITY_BOUND_INCOMPLETE",
                "failure_type":type(exc).__name__,
                "learning_claim":False,
                "source_science_terminal":False,
            })
        raise


if __name__ == "__main__":
    main()
