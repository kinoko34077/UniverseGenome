"""Freeze the accepted pre-generalization Phase 5 Outer Search as a machine-readable oracle.

This module is research/test infrastructure only. It observes the accepted legacy
implementation and refuses artifact generation when production search/physics
paths have drifted from the pinned source SHA.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from typing import Any, Mapping

from benchmarks.slow_trace_acceptance import _benchmark_density
from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from search.evolution import (
    CATEGORY_OPERATORS,
    OPTIMIZER_POPULATION_SIZE,
    SteadyStateOptimizer,
    UniverseSlot,
    seed_escalation,
)


ACCEPTED_SOURCE_SHA = "211d84b18fe68e70f89c8921d156e1b7c0592895"
ORACLE_SCHEMA_VERSION = 1
ORACLE_KIND = "UniverseGenomeLegacyOuterSearchOracle"
MANIFEST_KIND = "UniverseGenomeLegacyOuterSearchOracleManifest"
DEFAULT_OUTPUT_DIR = Path("research/artifacts/legacy_outer_search_oracle_v1")
PROTECTED_SOURCE_PATHS = (
    "core",
    "search",
    "persistence",
    "config/default.json",
    "benchmarks/slow_trace_acceptance.py",
)
AUTHORITATIVE_STATE_FIELDS = (
    "lifecycle",
    "x",
    "y",
    "structure",
    "latent",
    "hp",
    "bond_strength",
    "direction",
    "speed_code",
    "age",
    "black_hole_timer",
    "slow_trace",
)
DYNAMIC_BOUNDARIES = (16, 128, 512, 1024)


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_digest(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _file_bytes(payload: Any) -> bytes:
    return canonical_json_bytes(payload) + b"\n"


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_legacy_base_config(path: str | Path = "config/default.json") -> PhysicsConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("legacy config must be an object")
    return PhysicsConfig.from_mapping(payload)


def assert_source_tree_compatible(source_sha: str = ACCEPTED_SOURCE_SHA) -> None:
    if source_sha != ACCEPTED_SOURCE_SHA:
        raise ValueError(
            f"oracle source SHA is pinned to {ACCEPTED_SOURCE_SHA}; got {source_sha}"
        )
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_sha, "HEAD"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if ancestor.returncode != 0:
        raise RuntimeError("accepted source SHA is not an ancestor of the current checkout")
    diff = subprocess.run(
        ["git", "diff", "--quiet", source_sha, "--", *PROTECTED_SOURCE_PATHS],
        check=False,
    )
    if diff.returncode != 0:
        raise RuntimeError(
            "refusing to regenerate legacy oracle after production search/physics drift"
        )


def _state_observation(slot: UniverseSlot) -> dict[str, Any]:
    state = slot.state
    snapshot = state.to_snapshot()
    field_digests = {
        name: canonical_digest(list(getattr(state, name)))
        for name in AUTHORITATIVE_STATE_FIELDS
    }
    return {
        "seed": int(state.seed),
        "generation": int(state.generation),
        "format_version": int(snapshot["format_version"]),
        "config": (state.config or PhysicsConfig()).to_dict(),
        "authoritative_field_digests": field_digests,
        "state_digest": canonical_digest(snapshot),
    }


def _slot_observation(slot: UniverseSlot) -> dict[str, Any]:
    return {
        "index": int(slot.index),
        "category": slot.category,
        "genome": slot.genome.to_dict(),
        "genome_key": slot.genome_key,
        "seed": int(slot.seed),
        "state": _state_observation(slot),
        "fitness": slot.fitness.to_dict(),
        "growth_windows": list(slot.growth_windows),
        "growth_reference": (
            None if slot.growth_reference is None else slot.growth_reference.to_dict()
        ),
        "short_health_windows": list(slot.short_health_windows),
        "short_health_activity_cost": int(slot.short_health_activity_cost),
        "response_windows": list(slot.response_windows),
        "absolute_failure": bool(slot.absolute_failure),
        "absolute_failure_reason": slot.absolute_failure_reason,
        "parent_index": slot.parent_index,
        "parent_genome_key": slot.parent_genome_key,
        "last_mutation_field": slot.last_mutation_field,
        "allocation_reason": slot.allocation_reason,
        "evidence_mature": bool(slot.evidence_mature),
    }


def build_static_oracle(
    *,
    source_sha: str,
    base_seed: int,
    base_config: PhysicsConfig,
) -> dict[str, Any]:
    optimizer = SteadyStateOptimizer.from_defaults(
        base_seed=base_seed,
        base_config=base_config,
        experiment=ExperimentConfig(),
    )
    counts = {
        category: sum(slot.category == category for slot in optimizer.slots)
        for category in CATEGORY_OPERATORS
    }
    distinct_genomes = {
        category: len({slot.genome_key for slot in optimizer.slots if slot.category == category})
        for category in CATEGORY_OPERATORS
    }
    per_group_counts: dict[tuple[str, str], int] = {}
    for slot in optimizer.slots:
        per_group_counts[slot.evidence_group] = per_group_counts.get(slot.evidence_group, 0) + 1
    return {
        "schema_version": ORACLE_SCHEMA_VERSION,
        "kind": f"{ORACLE_KIND}.static",
        "source_sha": source_sha,
        "base_seed": int(base_seed),
        "category_order": list(CATEGORY_OPERATORS),
        "category_counts": counts,
        "distinct_genomes_per_category": min(distinct_genomes.values()),
        "seeds_per_genome_per_category": min(per_group_counts.values()),
        "distinct_seed_count": len({slot.seed for slot in optimizer.slots}),
        "initial_scheduler": dict(optimizer.scheduler),
        "slots": [_slot_observation(slot) for slot in optimizer.slots],
        "optimizer_snapshot": optimizer.to_snapshot(),
    }


class _BoundaryCaptureOptimizer(SteadyStateOptimizer):
    _oracle_captures: dict[str, dict[str, Any]]

    def _capture_slot(self, slot: UniverseSlot, boundary: int) -> None:
        bucket = self._oracle_captures.setdefault(str(boundary), {})
        key = str(slot.index)
        if key in bucket:
            raise RuntimeError(
                f"duplicate oracle capture for slot {slot.index} at generation {boundary}"
            )
        bucket[key] = _slot_observation(slot)

    def _record_short_health_step(self, slot, generation, metrics):
        super()._record_short_health_step(slot, generation, metrics)
        if generation == 16:
            self._capture_slot(slot, generation)

    def _observe_growth_boundary(self, slot):
        super()._observe_growth_boundary(slot)
        generation = int(slot.physical_generations)
        if generation in (128, 512, 1024):
            self._capture_slot(slot, generation)


def _boundary_protocol(terminal_generation: int) -> ExperimentConfig:
    terminal = int(terminal_generation)
    if terminal < 128 or terminal > 1024 or terminal % 2:
        raise ValueError("terminal_generation must be an even value in 128..1024")
    return ExperimentConfig(
        byte_hold_generations=0,
        byte_gap_generations=0,
        teacher_delay_generations=0,
        teacher_repetitions=terminal // 2,
        evaluation_timeout_generations=0,
    )


def _sanitize_step_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(summary))
    result.pop("generations_per_second", None)
    return result


def build_dynamic_oracle(
    *,
    source_sha: str,
    base_seed: int,
    base_config: PhysicsConfig,
    terminal_generation: int = 1024,
) -> dict[str, Any]:
    protocol = _boundary_protocol(terminal_generation)
    optimizer = _BoundaryCaptureOptimizer.from_defaults(
        base_seed=base_seed,
        base_config=base_config,
        experiment=protocol,
    )
    optimizer._oracle_captures = {}
    summary = _sanitize_step_summary(optimizer.step())

    required = [16] + [
        boundary
        for boundary in (128, 512, 1024)
        if boundary <= terminal_generation
    ]
    checkpoints: dict[str, list[dict[str, Any]]] = {}
    for boundary in required:
        raw = optimizer._oracle_captures.get(str(boundary), {})
        if len(raw) != OPTIMIZER_POPULATION_SIZE:
            raise RuntimeError(
                f"boundary {boundary} captured {len(raw)} slots, expected "
                f"{OPTIMIZER_POPULATION_SIZE}"
            )
        checkpoints[str(boundary)] = [
            raw[str(index)] for index in range(OPTIMIZER_POPULATION_SIZE)
        ]

    return {
        "schema_version": ORACLE_SCHEMA_VERSION,
        "kind": f"{ORACLE_KIND}.dynamic",
        "source_sha": source_sha,
        "base_seed": int(base_seed),
        "protocol": protocol.to_dict(),
        "terminal_generation": int(terminal_generation),
        "checkpoints": checkpoints,
        "integrated_step": summary,
        "post_step_scheduler": dict(optimizer.scheduler),
        "prune_history": [dict(item) for item in optimizer.prune_history],
        "post_step_slots": [_slot_observation(slot) for slot in optimizer.slots],
    }


def _mutation_probe(
    *,
    category: str,
    base_seed: int,
    base_config: PhysicsConfig,
) -> dict[str, Any]:
    optimizer = SteadyStateOptimizer.from_defaults(
        base_seed=base_seed,
        base_config=base_config,
    )
    parent = next(slot for slot in optimizer.slots if slot.category == category)
    free_index = (CATEGORY_OPERATORS.index(category) + 1) * 32 - 1
    scheduler_before = dict(optimizer.scheduler)
    child = optimizer.replace_free_slot(free_index=free_index, parent=parent)
    field = child.last_mutation_field
    if field is None:
        raise RuntimeError("legacy mutation probe produced no mutation field")
    before = int(getattr(parent.genome, field))
    after = int(getattr(child.genome, field))
    direction = 1 if after > before else -1
    return {
        "category": category,
        "parent": _slot_observation(parent),
        "scheduler_before": scheduler_before,
        "scheduler_after": dict(optimizer.scheduler),
        "mutation_field": field,
        "mutation_direction": direction,
        "mutation_before": before,
        "mutation_after": after,
        "child": _slot_observation(child),
    }


def _seed_evidence_probe(
    *,
    category: str,
    base_seed: int,
    base_config: PhysicsConfig,
) -> dict[str, Any]:
    optimizer = SteadyStateOptimizer.from_defaults(
        base_seed=base_seed,
        base_config=base_config,
    )
    parent = next(slot for slot in optimizer.slots if slot.category == category)
    free_index = (CATEGORY_OPERATORS.index(category) + 1) * 32 - 1
    scheduler_before = dict(optimizer.scheduler)
    child = optimizer.allocate_seed_slot(free_index=free_index, parent=parent)
    return {
        "category": category,
        "parent": _slot_observation(parent),
        "scheduler_before": scheduler_before,
        "scheduler_after": dict(optimizer.scheduler),
        "child": _slot_observation(child),
    }


def build_decision_oracle(
    *,
    source_sha: str,
    base_seed: int,
    base_config: PhysicsConfig,
) -> dict[str, Any]:
    mode_optimizer = SteadyStateOptimizer.from_defaults(
        base_seed=base_seed,
        base_config=base_config,
    )
    allocation_modes = {
        category: [
            mode_optimizer._next_allocation_mode(category, promising_available=True),
            mode_optimizer._next_allocation_mode(category, promising_available=True),
        ]
        for category in CATEGORY_OPERATORS
    }
    return {
        "schema_version": ORACLE_SCHEMA_VERSION,
        "kind": f"{ORACLE_KIND}.decisions",
        "source_sha": source_sha,
        "seed_escalation": {
            str(count): seed_escalation(count) for count in (4, 8, 16, 32)
        },
        "allocation_mode_sequence": allocation_modes,
        "mutation_probes": [
            _mutation_probe(
                category=category,
                base_seed=base_seed,
                base_config=base_config,
            )
            for category in CATEGORY_OPERATORS
        ],
        "seed_evidence_probes": [
            _seed_evidence_probe(
                category=category,
                base_seed=base_seed,
                base_config=base_config,
            )
            for category in CATEGORY_OPERATORS
        ],
    }


def build_continuation_oracle(
    *,
    source_sha: str,
    base_seed: int,
    base_config: PhysicsConfig,
) -> dict[str, Any]:
    protocol = ExperimentConfig(
        byte_hold_generations=0,
        byte_gap_generations=0,
        teacher_delay_generations=0,
        teacher_repetitions=1,
        evaluation_timeout_generations=0,
    )
    uninterrupted = SteadyStateOptimizer.from_defaults(
        base_seed=base_seed,
        base_config=base_config,
        experiment=protocol,
    )
    uninterrupted.step()
    snapshot = uninterrupted.to_snapshot()
    restored = SteadyStateOptimizer.from_snapshot(copy.deepcopy(snapshot))
    uninterrupted.step()
    restored.step()
    uninterrupted_payload = uninterrupted.to_snapshot()
    restored_payload = restored.to_snapshot()
    return {
        "schema_version": ORACLE_SCHEMA_VERSION,
        "kind": f"{ORACLE_KIND}.continuation",
        "source_sha": source_sha,
        "snapshot_format_version": int(snapshot["format_version"]),
        "snapshot_digest": canonical_digest(snapshot),
        "uninterrupted_continuation_digest": canonical_digest(uninterrupted_payload),
        "restored_continuation_digest": canonical_digest(restored_payload),
        "exact_match": uninterrupted_payload == restored_payload,
        "scheduler_after_continuation": dict(uninterrupted.scheduler),
    }


def build_deterministic_oracle(
    *,
    source_sha: str,
    base_seed: int,
    base_config: PhysicsConfig,
    terminal_generation: int = 1024,
) -> tuple[dict[str, Any], dict[str, Any]]:
    static = build_static_oracle(
        source_sha=source_sha,
        base_seed=base_seed,
        base_config=base_config,
    )
    initial_snapshot = static.pop("optimizer_snapshot")
    oracle = {
        "schema_version": ORACLE_SCHEMA_VERSION,
        "kind": ORACLE_KIND,
        "source_sha": source_sha,
        "static": static,
        "dynamic": build_dynamic_oracle(
            source_sha=source_sha,
            base_seed=base_seed,
            base_config=base_config,
            terminal_generation=terminal_generation,
        ),
        "decisions": build_decision_oracle(
            source_sha=source_sha,
            base_seed=base_seed,
            base_config=base_config,
        ),
        "continuation": build_continuation_oracle(
            source_sha=source_sha,
            base_seed=base_seed,
            base_config=base_config,
        ),
    }
    if not oracle["continuation"]["exact_match"]:
        raise RuntimeError("snapshot restore continuation diverged from uninterrupted run")
    return initial_snapshot, oracle


def build_performance_baseline(source_sha: str) -> dict[str, Any]:
    return {
        "schema_version": ORACLE_SCHEMA_VERSION,
        "kind": f"{ORACLE_KIND}.performance",
        "source_sha": source_sha,
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "conditions": {
            "generations_per_repeat": 512,
            "warmup_generations": 32,
            "repeats": 3,
            "seed_formula": "1000 + repeat",
        },
        "density4": _benchmark_density(
            density=4,
            generations=512,
            warmup=32,
            repeats=3,
        ),
        "density32": _benchmark_density(
            density=32,
            generations=512,
            warmup=32,
            repeats=3,
        ),
    }


def _write_payload(path: Path, payload: Any) -> dict[str, Any]:
    data = _file_bytes(payload)
    path.write_bytes(data)
    return {
        "path": path.as_posix(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def generate_bundle(
    *,
    output_dir: Path,
    source_sha: str = ACCEPTED_SOURCE_SHA,
    base_seed: int = 0,
) -> dict[str, Any]:
    assert_source_tree_compatible(source_sha)
    base_config = load_legacy_base_config()
    initial_snapshot, oracle = build_deterministic_oracle(
        source_sha=source_sha,
        base_seed=base_seed,
        base_config=base_config,
        terminal_generation=1024,
    )
    performance = build_performance_baseline(source_sha)

    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "initial_optimizer_v6": _write_payload(
            output_dir / "initial_optimizer_v6.json",
            initial_snapshot,
        ),
        "oracle": _write_payload(output_dir / "oracle.json", oracle),
        "performance": _write_payload(
            output_dir / "performance_baseline.json",
            performance,
        ),
    }
    bundle_digest = canonical_digest(
        {name: item["sha256"] for name, item in sorted(artifacts.items())}
    )
    manifest = {
        "schema_version": ORACLE_SCHEMA_VERSION,
        "kind": MANIFEST_KIND,
        "source_sha": source_sha,
        "generator": "research/legacy_outer_search_oracle.py",
        "generation_command": (
            "python -m research.legacy_outer_search_oracle generate "
            "--output-dir research/artifacts/legacy_outer_search_oracle_v1 "
            f"--source-sha {source_sha} --base-seed {base_seed}"
        ),
        "config": {
            "path": "config/default.json",
            "base_seed": int(base_seed),
            "dynamic_boundaries": list(DYNAMIC_BOUNDARIES),
            "boundary_protocol": _boundary_protocol(1024).to_dict(),
            "performance_conditions": performance["conditions"],
        },
        "deterministic_artifacts": [
            "initial_optimizer_v6",
            "oracle",
        ],
        "artifacts": artifacts,
        "bundle_digest": bundle_digest,
    }
    _write_payload(output_dir / "manifest.json", manifest)
    return manifest


def verify_bundle(
    *,
    output_dir: Path,
    source_sha: str = ACCEPTED_SOURCE_SHA,
    base_seed: int = 0,
) -> dict[str, Any]:
    assert_source_tree_compatible(source_sha)
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_config = load_legacy_base_config()
    initial_snapshot, oracle = build_deterministic_oracle(
        source_sha=source_sha,
        base_seed=base_seed,
        base_config=base_config,
        terminal_generation=1024,
    )
    regenerated = {
        "initial_optimizer_v6": hashlib.sha256(_file_bytes(initial_snapshot)).hexdigest(),
        "oracle": hashlib.sha256(_file_bytes(oracle)).hexdigest(),
    }
    expected = {
        name: manifest["artifacts"][name]["sha256"]
        for name in manifest["deterministic_artifacts"]
    }
    actual_files = {
        name: _file_digest(Path(manifest["artifacts"][name]["path"]))
        for name in manifest["artifacts"]
    }
    all_file_digests_match = all(
        actual_files[name] == manifest["artifacts"][name]["sha256"]
        for name in manifest["artifacts"]
    )
    result = {
        "schema_version": ORACLE_SCHEMA_VERSION,
        "source_sha": source_sha,
        "regenerated_digests": regenerated,
        "expected_digests": expected,
        "deterministic_match": regenerated == expected,
        "all_file_digests_match": all_file_digests_match,
        "continuation_exact_match": bool(oracle["continuation"]["exact_match"]),
    }
    if not (
        result["deterministic_match"]
        and result["all_file_digests_match"]
        and result["continuation_exact_match"]
    ):
        raise RuntimeError(f"legacy oracle verification failed: {result}")
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Freeze/verify the accepted Phase 5 Outer Search legacy oracle"
    )
    sub = result.add_subparsers(dest="command", required=True)
    for name in ("generate", "verify"):
        command = sub.add_parser(name)
        command.add_argument(
            "--output-dir",
            type=Path,
            default=DEFAULT_OUTPUT_DIR,
        )
        command.add_argument("--source-sha", default=ACCEPTED_SOURCE_SHA)
        command.add_argument("--base-seed", type=int, default=0)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "generate":
        payload = generate_bundle(
            output_dir=args.output_dir,
            source_sha=args.source_sha,
            base_seed=args.base_seed,
        )
    else:
        payload = verify_bundle(
            output_dir=args.output_dir,
            source_sha=args.source_sha,
            base_seed=args.base_seed,
        )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
