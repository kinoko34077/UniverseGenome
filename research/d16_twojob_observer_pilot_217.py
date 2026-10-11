"""D16.2 TEST ONLY: two independently hosted Actions jobs, original seed0 full128 selected v7 handoff.

Test-only immutable completed-state transfer. NEVER runs D16 seed16384.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from tempfile import TemporaryDirectory
import time
from typing import Any

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from research.d15_selected_resume_213 import execute_selected_round
from research.d16_native_journal_observer_217 import observe_committed_round
from research.d8_genome_diversity_190 import digest
from search.evolution import SteadyStateOptimizer

EXPOSED_PERF_SEED = 0
EXPECTED_FULL_SELECTED = (
    "725d6481e0e1044848fbf38ff31a58657f977d4128b78e90b809ef3820d9ee63",
    "abe281245d5a45e78dcce3eab9e9f787b6260f365fa868da5ef13c2db3262112",
)
MAX_RSS_BYTES = 1536 * 1024 * 1024
MAX_ROUND_JOURNAL = 128 * 1024 * 1024
MAX_RETAINED_JOURNAL = 512 * 1024 * 1024
TRANSFER_SCHEMA = "d16-authentic-twojob-selected-v7-pilot.v1"


def canonical_bytes(data: Any) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(data) + b"\n")


def source_sha() -> str:
    value = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, timeout=10).strip()
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise AssertionError("source must have 40-char immutable git HEAD")
    return value


def checked_state(snapshot: dict[str, Any], *, expected_generation: int) -> None:
    opt = SteadyStateOptimizer.from_snapshot(snapshot)
    counts: dict[str, int] = {}
    for index, slot in enumerate(opt.slots):
        if slot.index != index:
            raise AssertionError("original slot identity not contiguous")
        counts[slot.category] = counts.get(slot.category, 0) + 1
    if (len(opt.slots) != 128 or sorted(counts.values()) != [32] * 4
            or opt.generation != expected_generation
            or opt.to_snapshot() != snapshot
            or opt.search_plan.scheduler_base_seed != EXPOSED_PERF_SEED
            or opt.experiment.to_dict() != ExperimentConfig().to_dict()
            or opt.base_config.to_dict() != PhysicsConfig().to_dict()):
        raise AssertionError("selected state shape/config/seed roundtrip changed")
    if digest(snapshot) != EXPECTED_FULL_SELECTED[expected_generation - 1]:
        raise AssertionError("original selected full-v7 SHA golden mismatch")


def validate_transfer(
    snapshot: dict[str, Any], manifest: dict[str, Any], *, actual_source: str,
) -> None:
    if manifest.get("schema") != TRANSFER_SCHEMA:
        raise AssertionError("handoff schema changed")
    if (manifest.get("source_sha") != actual_source
            or manifest.get("seed") != EXPOSED_PERF_SEED
            or manifest.get("selected_generation") != 1
            or manifest.get("last_selected_v7_sha256") != EXPECTED_FULL_SELECTED[0]
            or manifest.get("selected_snapshot_sha256") != hash_bytes(canonical_bytes(snapshot))
            or manifest.get("experiment") != ExperimentConfig().to_dict()
            or manifest.get("physics") != PhysicsConfig().to_dict()):
        raise AssertionError("handoff source/seed/config/generation/digest differs")
    checked_state(snapshot, expected_generation=1)


def run_native_round(
    index: int, source: str, base_snapshot: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    with TemporaryDirectory(prefix=f"perf230-p44-round-{index}-") as temp:
        started = time.monotonic()
        root = Path(temp) / "journal"
        result = execute_selected_round(
            root, source_commit=source, base_seed=EXPOSED_PERF_SEED,
            experiment=ExperimentConfig(), base_config=PhysicsConfig(),
            base_snapshot=base_snapshot, evaluation_batch_size=16,
            memory_mib=1536, workers=4,
        )
        wall = time.monotonic() - started
        snapshot = result["final_snapshot"]
        checked_state(snapshot, expected_generation=index)
        if (result["new_evaluations"] != 128
                or result["resumed_from"] != 0
                or result["checkpoint_writes"] != 8
                or not result["finalization_performed"]
                or not result["final_committed"]
                or result["final_digest"] != EXPECTED_FULL_SELECTED[index - 1]):
            raise AssertionError("original once-only selected128/journal parity failed")
        if (result.get("peak_aggregate_rss_bytes") is None
                or result["peak_aggregate_rss_bytes"] > MAX_RSS_BYTES
                or result["journal_bytes"] > MAX_ROUND_JOURNAL
                or result["journal_bytes"] > MAX_RETAINED_JOURNAL):
            raise AssertionError("memory/disk budget exceeded")
        originals = sorted(root.glob("batch-*.json"))
        if ([p.name for p in originals] != [f"batch-{n:05d}.json" for n in range(8)]
                or not (root / "final.json").exists()):
            raise AssertionError("original ordered D15 atomic patches incomplete")
        files = {p.name: hash_bytes(p.read_bytes()) for p in sorted(root.glob("*.json"))}
        evidence = observe_committed_round(root, source_commit=source)
        if (evidence["selected_post_v7_sha256"] != result["final_digest"]
                or evidence["evaluated_native_worlds"] != 128
                or evidence["selected_native_worlds"] != 128
                or evidence["selected_optimizer_generation"] != index
                or not evidence["d15_journal_chain_verified"]):
            raise AssertionError("authentic completed journal pre/post D16 observer mismatch")
        metrics = {
            "source_sha": source, "stage": index,
            "seed": EXPOSED_PERF_SEED,
            "selected_v7_sha256": result["final_digest"],
            "generation": index,
            "evaluations": 128,
            "patches": 8,
            "workers": 4,
            "journal_bytes": result["journal_bytes"],
            "journal_file_sha256": files,
            "peak_aggregate_rss_bytes": result["peak_aggregate_rss_bytes"],
            "wall_seconds": wall,
            "linux_python": platform.platform() + " / " + platform.python_version(),
            "D16_research_seed16384_executed": False,
            "native_readonly_observer_preselect_sha256": evidence["evaluated_preselect_v7_sha256"],
            "native_readonly_observer_selected_sha256": evidence["selected_post_v7_sha256"],
            "native_readonly_observer_retirements": evidence["actual_native_replacement_count"],
            "native_readonly_observer_source_chain_verified": True,
        }
        return snapshot, metrics


def stage_first(out: Path) -> None:
    source = source_sha()
    snapshot, metrics = run_native_round(1, source, None)
    meta = {
        "schema": TRANSFER_SCHEMA,
        "source_sha": source,
        "seed": EXPOSED_PERF_SEED,
        "experiment": ExperimentConfig().to_dict(),
        "physics": PhysicsConfig().to_dict(),
        "selected_generation": 1,
        "last_selected_v7_sha256": digest(snapshot),
        "selected_snapshot_sha256": hash_bytes(canonical_bytes(snapshot)),
    }
    validate_transfer(snapshot, meta, actual_source=source)
    write_json(out / "snapshot-v7.json", snapshot)
    write_json(out / "manifest.json", meta)
    write_json(out / "round-1-metrics.json", metrics)
    print(json.dumps({"stage": 1, "metrics": metrics}, sort_keys=True), flush=True)


def stage_second(inbound: Path, out: Path) -> None:
    source = source_sha()
    manifest = json.loads((inbound / "manifest.json").read_bytes())
    snapshot = json.loads((inbound / "snapshot-v7.json").read_bytes())
    previous_metrics = json.loads((inbound / "round-1-metrics.json").read_bytes())
    validate_transfer(snapshot, manifest, actual_source=source)
    if (previous_metrics.get("source_sha") != source
            or previous_metrics.get("generation") != 1
            or previous_metrics.get("native_readonly_observer_selected_sha256") != EXPECTED_FULL_SELECTED[0]
            or previous_metrics.get("native_readonly_observer_source_chain_verified") is not True
            or previous_metrics.get("selected_v7_sha256") != EXPECTED_FULL_SELECTED[0]
            or previous_metrics.get("evaluations") != 128
            or previous_metrics.get("patches") != 8
            or previous_metrics.get("journal_bytes", MAX_ROUND_JOURNAL + 1) > MAX_ROUND_JOURNAL):
        raise AssertionError("source-matched original stage1 journal provenance invalid")
    result, metrics = run_native_round(2, source, snapshot)
    write_json(out / "round-2-metrics.json", metrics)
    write_json(out / "continuity-verdict.json", {
        "source_sha": source,
        "seed": EXPOSED_PERF_SEED,
        "complete_selected_rounds": 2,
        "across_distinct_jobs": True,
        "full_selected_v7_sha256": [EXPECTED_FULL_SELECTED[0], digest(result)],
        "wall_selected_rounds_sum_s": previous_metrics["wall_seconds"] + metrics["wall_seconds"],
        "journal_bytes_sum": previous_metrics["journal_bytes"] + metrics["journal_bytes"],
        "result": "PASS",
        "D16_research_seed16384_executed": False,
        "real_37_rounds_budget_validated": False,
    })
    print(json.dumps({"stage": 2, "metrics": metrics}, sort_keys=True), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("first", "second"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--inbound", type=Path)
    args = parser.parse_args()
    if args.stage == "first":
        stage_first(args.out)
    else:
        if args.inbound is None:
            parser.error("--inbound required for second stage")
        stage_second(args.inbound, args.out)


if __name__ == "__main__":
    main()
