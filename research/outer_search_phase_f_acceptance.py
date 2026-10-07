"""Phase F full legacy-equivalence and matched-performance acceptance harness.

This module never regenerates the Phase A oracle. It compares the current
generalized Legacy SearchPlan execution against the immutable frozen artifacts,
then measures accepted pre-generalization source and the current checkout under
the same Python executable / runner / benchmark protocol.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from typing import Any, Mapping

from core.experiment import ExperimentConfig
from research.legacy_outer_search_oracle import (
    ACCEPTED_SOURCE_SHA,
    build_decision_oracle,
    build_dynamic_oracle,
    build_static_oracle,
    canonical_digest,
    load_legacy_base_config,
)
from search.evolution import SteadyStateOptimizer


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "research" / "artifacts" / "legacy_outer_search_oracle_v1"
MANIFEST_PATH = ARTIFACT_DIR / "manifest.json"
FROZEN_V6_PATH = ARTIFACT_DIR / "initial_optimizer_v6.json"
FROZEN_ORACLE_PATH = ARTIFACT_DIR / "oracle.json"
FROZEN_PERFORMANCE_PATH = ARTIFACT_DIR / "performance_baseline.json"
PERFORMANCE_REGRESSION_LIMIT_PERCENT = 5.0


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_v7_to_legacy_v6(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(payload))
    result["format_version"] = 6
    result.pop("outer_search", None)
    return result


def _artifact_integrity() -> dict[str, Any]:
    manifest = _read_json(MANIFEST_PATH)
    names = {
        "initial_optimizer_v6": FROZEN_V6_PATH,
        "oracle": FROZEN_ORACLE_PATH,
        "performance": FROZEN_PERFORMANCE_PATH,
    }
    actual = {name: _sha256(path) for name, path in names.items()}
    expected = {
        name: str(manifest["artifacts"][name]["sha256"])
        for name in names
    }
    bundle = canonical_digest(
        {name: actual[name] for name in sorted(actual)}
    )
    return {
        "source_sha": manifest.get("source_sha"),
        "expected_file_digests": expected,
        "actual_file_digests": actual,
        "file_digests_match": actual == expected,
        "expected_bundle_digest": manifest.get("bundle_digest"),
        "actual_bundle_digest": bundle,
        "bundle_digest_match": bundle == manifest.get("bundle_digest"),
    }


def _continuation_report(
    *,
    frozen: Mapping[str, Any],
) -> dict[str, Any]:
    protocol = ExperimentConfig(
        byte_hold_generations=0,
        byte_gap_generations=0,
        teacher_delay_generations=0,
        teacher_repetitions=1,
        evaluation_timeout_generations=0,
    )
    base_config = load_legacy_base_config()
    uninterrupted = SteadyStateOptimizer.from_defaults(
        base_seed=0,
        base_config=base_config,
        experiment=protocol,
    )
    uninterrupted.step()
    snapshot_v6 = project_v7_to_legacy_v6(uninterrupted.to_snapshot())
    restored = SteadyStateOptimizer.from_snapshot(copy.deepcopy(snapshot_v6))

    uninterrupted.step()
    restored.step()

    uninterrupted_v6 = project_v7_to_legacy_v6(uninterrupted.to_snapshot())
    restored_v6 = project_v7_to_legacy_v6(restored.to_snapshot())
    return {
        "snapshot_digest": canonical_digest(snapshot_v6),
        "expected_snapshot_digest": frozen["snapshot_digest"],
        "snapshot_match": (
            canonical_digest(snapshot_v6) == frozen["snapshot_digest"]
        ),
        "uninterrupted_continuation_digest": canonical_digest(uninterrupted_v6),
        "expected_uninterrupted_continuation_digest": (
            frozen["uninterrupted_continuation_digest"]
        ),
        "uninterrupted_match": (
            canonical_digest(uninterrupted_v6)
            == frozen["uninterrupted_continuation_digest"]
        ),
        "restored_continuation_digest": canonical_digest(restored_v6),
        "expected_restored_continuation_digest": (
            frozen["restored_continuation_digest"]
        ),
        "restored_match": (
            canonical_digest(restored_v6)
            == frozen["restored_continuation_digest"]
        ),
        "restored_equals_uninterrupted": restored_v6 == uninterrupted_v6,
        "scheduler_match": (
            uninterrupted.scheduler == frozen["scheduler_after_continuation"]
            and restored.scheduler == frozen["scheduler_after_continuation"]
        ),
    }


def deterministic_report() -> dict[str, Any]:
    integrity = _artifact_integrity()
    if integrity["source_sha"] != ACCEPTED_SOURCE_SHA:
        raise RuntimeError("frozen manifest source SHA does not match accepted oracle SHA")

    frozen_v6 = _read_json(FROZEN_V6_PATH)
    frozen = _read_json(FROZEN_ORACLE_PATH)
    base_config = load_legacy_base_config()

    current_static = build_static_oracle(
        source_sha=ACCEPTED_SOURCE_SHA,
        base_seed=0,
        base_config=base_config,
    )
    current_initial_v7 = current_static.pop("optimizer_snapshot")
    current_initial_v6 = project_v7_to_legacy_v6(current_initial_v7)

    current_dynamic = build_dynamic_oracle(
        source_sha=ACCEPTED_SOURCE_SHA,
        base_seed=0,
        base_config=base_config,
        terminal_generation=1024,
    )
    current_decisions = build_decision_oracle(
        source_sha=ACCEPTED_SOURCE_SHA,
        base_seed=0,
        base_config=base_config,
    )
    continuation = _continuation_report(frozen=frozen["continuation"])

    checks = {
        "artifact_file_digests": bool(integrity["file_digests_match"]),
        "artifact_bundle_digest": bool(integrity["bundle_digest_match"]),
        "initial_optimizer_v6": current_initial_v6 == frozen_v6,
        "static_128_slots": current_static == frozen["static"],
        "dynamic_16_128_512_1024": current_dynamic == frozen["dynamic"],
        "optimizer_decisions": current_decisions == frozen["decisions"],
        "continuation_snapshot": bool(continuation["snapshot_match"]),
        "continuation_uninterrupted": bool(continuation["uninterrupted_match"]),
        "continuation_restored": bool(continuation["restored_match"]),
        "continuation_exact": bool(continuation["restored_equals_uninterrupted"]),
        "continuation_scheduler": bool(continuation["scheduler_match"]),
    }
    return {
        "kind": "UniverseGenomeOuterSearchPhaseFDeterministicAcceptance",
        "accepted_oracle_source_sha": ACCEPTED_SOURCE_SHA,
        "current_head": _git_head(ROOT),
        "oracle_bundle_digest": integrity["expected_bundle_digest"],
        "checks": checks,
        "continuation": continuation,
        "passed": all(checks.values()),
    }


def _git_head(cwd: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _benchmark_subprocess(
    cwd: Path,
    *,
    generations: int,
    warmup: int,
    repeats: int,
) -> dict[str, Any]:
    code = (
        "import json,platform;"
        "from benchmarks.slow_trace_acceptance import _benchmark_density;"
        f"g={int(generations)};w={int(warmup)};r={int(repeats)};"
        "print(json.dumps({"
        "'environment':{'python':platform.python_version(),"
        "'implementation':platform.python_implementation(),"
        "'platform':platform.platform(),'machine':platform.machine()},"
        "'density4':_benchmark_density(density=4,generations=g,warmup=w,repeats=r),"
        "'density32':_benchmark_density(density=32,generations=g,warmup=w,repeats=r)"
        "},sort_keys=True))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "PYTHONHASHSEED": "0"},
    )
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("benchmark subprocess did not return an object")
    return payload


def _regression_percent(baseline: float, current: float) -> float:
    if baseline <= 0:
        raise ValueError("baseline throughput must be positive")
    return ((baseline - current) / baseline) * 100.0


def performance_report() -> dict[str, Any]:
    frozen = _read_json(FROZEN_PERFORMANCE_PATH)
    conditions = frozen["conditions"]
    generations = int(conditions["generations_per_repeat"])
    warmup = int(conditions["warmup_generations"])
    repeats = int(conditions["repeats"])

    with tempfile.TemporaryDirectory(prefix="universegenome-phase-f-") as temp:
        baseline_root = Path(temp) / "accepted-main"
        subprocess.run(
            [
                "git",
                "worktree",
                "add",
                "--detach",
                str(baseline_root),
                ACCEPTED_SOURCE_SHA,
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        try:
            baseline = _benchmark_subprocess(
                baseline_root,
                generations=generations,
                warmup=warmup,
                repeats=repeats,
            )
            current = _benchmark_subprocess(
                ROOT,
                generations=generations,
                warmup=warmup,
                repeats=repeats,
            )
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(baseline_root)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

    environment_match = baseline["environment"] == current["environment"]
    densities: dict[str, Any] = {}
    for key in ("density4", "density32"):
        baseline_median = float(baseline[key]["median_generations_per_second"])
        current_median = float(current[key]["median_generations_per_second"])
        regression = _regression_percent(baseline_median, current_median)
        densities[key] = {
            "accepted_source": baseline[key],
            "generalized_current": current[key],
            "frozen_phase_a_median_generations_per_second": float(
                frozen[key]["median_generations_per_second"]
            ),
            "regression_percent": regression,
            "limit_percent": PERFORMANCE_REGRESSION_LIMIT_PERCENT,
            "passed": regression <= PERFORMANCE_REGRESSION_LIMIT_PERCENT,
        }

    return {
        "kind": "UniverseGenomeOuterSearchPhaseFPerformanceAcceptance",
        "accepted_source_sha": ACCEPTED_SOURCE_SHA,
        "current_head": _git_head(ROOT),
        "conditions": conditions,
        "matched_environment": environment_match,
        "environment": current["environment"],
        "frozen_phase_a_environment": frozen["environment"],
        "densities": densities,
        "passed": environment_match and all(
            item["passed"] for item in densities.values()
        ),
    }


def full_report() -> dict[str, Any]:
    deterministic = deterministic_report()
    performance = performance_report()
    return {
        "kind": "UniverseGenomeOuterSearchPhaseFAcceptance",
        "schema_version": 1,
        "current_head": _git_head(ROOT),
        "deterministic": deterministic,
        "performance": performance,
        "passed": bool(deterministic["passed"] and performance["passed"]),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument(
        "mode",
        choices=("deterministic", "performance", "all"),
        nargs="?",
        default="all",
    )
    result.add_argument("--output", type=Path)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.mode == "deterministic":
        report = deterministic_report()
    elif args.mode == "performance":
        report = performance_report()
    else:
        report = full_report()

    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
