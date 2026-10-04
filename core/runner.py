"""Headless runner and bounded performance reporting through Phase 5."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import Any

from .physics import PhysicsConfig, create_universe, step
from .population import run_population_headless
from .experiment import ExperimentConfig, compare_baseline_trained, load_experiment_config
from search.evolution import run_optimizer_headless
from .state import DEFAULT_MAX_CELLS, HP_BITS, LATENT_BITS, STRUCTURE_BITS


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema_version") != 1:
        raise ValueError("unsupported config schema_version")
    return data


def _current_state(config: dict[str, Any]) -> dict[str, Any]:
    """Return explicit acceptance/readiness state, failing closed when absent."""
    configured = config.get("current_state", {})
    if not isinstance(configured, dict):
        raise ValueError("current_state must be an object")
    owners = configured.get("blocking_owners", ["#63"])
    if not isinstance(owners, list) or not all(isinstance(owner, str) for owner in owners):
        raise ValueError("current_state.blocking_owners must be a list of strings")
    return {
        "acceptance_state": str(configured.get("acceptance_state", "remediation_in_progress")),
        "phase6_ready": bool(configured.get("phase6_ready", False)),
        "blocking_owners": list(owners),
        "readiness_owner": str(configured.get("readiness_owner", "#60")),
        "next_phase": str(
            configured.get("next_phase", "GUI/search integration remediation (#63; Phase 6+ blocked)")
        ),
    }


def build_status(config: dict[str, Any]) -> dict[str, Any]:
    current_state = _current_state(config)
    phase1 = bool(config.get("features", {}).get("phase1_physics", False))
    phase2a = bool(config.get("features", {}).get("phase2a_bond_physics", False))
    phase2b = bool(config.get("features", {}).get("phase2b_latent_operators", False))
    phase2c = bool(config.get("features", {}).get("fusion", False))
    phase2d = bool(config.get("features", {}).get("fragmentation", False))
    phase2e = bool(config.get("features", {}).get("aging", False))
    phase3 = bool(config.get("features", {}).get("multi_universe_runtime", False))
    phase4 = bool(config.get("features", {}).get("io_learning", False))
    phase5 = bool(config.get("features", {}).get("evolution", False))
    return {
        "project": "UniverseGenome",
        "phase": (
            5
            if phase5 and phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1
            else 4
            if phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1
            else 3
            if phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1
            else 2
            if phase2a and phase1
            else 1
            if phase1
            else 0
        ),
        "phase0_scaffold": not phase1,
        "phase1_physics_implemented": phase1,
        "phase2a_bond_physics_implemented": phase2a and phase1,
        "phase2b_latent_operators_implemented": phase2b and phase2a and phase1,
        "phase2c_fusion_implemented": phase2c and phase2b and phase2a and phase1,
        "phase2d_fragmentation_implemented": phase2d and phase2c and phase2b and phase2a and phase1,
        "phase2e_aging_implemented": phase2e and phase2d and phase2c and phase2b and phase2a and phase1,
        "phase3_runtime_implemented": phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1,
        "phase4_io_learning_implemented": phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1,
        "phase5_optimizer_implemented": phase5 and phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1,
        "acceptance_state": current_state["acceptance_state"],
        "phase6_ready": current_state["phase6_ready"],
        "phase6_blocked": not current_state["phase6_ready"],
        "blocking_owners": current_state["blocking_owners"],
        "readiness_owner": current_state["readiness_owner"],
        "logical_size": config["world"]["logical_size"],
        "subdivisions_per_tile": config["world"]["subdivisions_per_tile"],
        "fixed_point_size": config["world"]["fixed_point_size"],
        "max_cells": config["world"]["max_cells"],
        "state_bits": {
            "structure": STRUCTURE_BITS,
            "latent": LATENT_BITS,
            "hp": HP_BITS,
        },
        "next_phase": (
            current_state["next_phase"]
            if phase5 and phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1
            else "Phase 5 UniverseGenome optimizer"
            if phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1
            else "Phase 4 I/O learning"
            if phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1
            else "Phase 3 128-universe runtime and observation GUI"
            if phase2e and phase2d and phase2c and phase2b and phase2a and phase1
            else "Phase 2E aging"
            if phase2d and phase2c and phase2b and phase2a and phase1
            else "Phase 2D fragmentation"
            if phase2c and phase2b and phase2a and phase1
            else "Phase 2C fusion"
            if phase2b and phase2a and phase1
            else "Phase 2B latent operators"
            if phase2a and phase1
            else "Phase 2A bond/contact physics"
            if phase1
            else "Phase 1 minimal deterministic single-universe physics"
        ),
    }


def run_headless(seed: int, generations: int, config: PhysicsConfig) -> dict[str, Any]:
    if generations < 0:
        raise ValueError("generations must be non-negative")
    state = create_universe(seed=seed, config=config)
    started = time.perf_counter()
    collision_count = 0
    bond_contact_count = 0
    latent_transmission_count = 0
    fusion_count = 0
    fragmentation_count = 0
    noise_spawn_count = 0
    last_metrics = None
    for _ in range(generations):
        last_metrics = step(state)
        collision_count += last_metrics.collision_count
        bond_contact_count += last_metrics.bond_contact_count
        latent_transmission_count += last_metrics.latent_transmission_count
        fusion_count += last_metrics.fusion_count
        fragmentation_count += last_metrics.fragmentation_count
        noise_spawn_count += last_metrics.noise_spawn_count
    elapsed = max(time.perf_counter() - started, 1e-12)
    return {
        "generations": generations,
        "generation": state.generation,
        "active_cells": len(state.active_slots()),
        "collision_count": collision_count,
        "bond_contact_count": bond_contact_count,
        "latent_transmission_count": latent_transmission_count,
        "fusion_count": fusion_count,
        "fragmentation_count": fragmentation_count,
        "noise_spawn_count": noise_spawn_count,
        "generations_per_second": generations / elapsed if generations else 0.0,
        "last_step_generations_per_second": last_metrics.generations_per_second if last_metrics else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UniverseGenome headless Phase 5 runner")
    parser.add_argument("--config", default="config/default.json")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--generations", type=int, default=0)
    parser.add_argument("--population", action="store_true", help="run the Phase 3 128-slot population")
    parser.add_argument("--experiment", action="store_true", help="run the Phase 4 baseline/trained measurement")
    parser.add_argument(
        "--experiment-config",
        default="config/experiment_v0_1.json",
        help="effective Phase 4 experiment protocol JSON",
    )
    parser.add_argument("--optimizer", action="store_true", help="run the Phase 5 optimizer diagnostics")
    parser.add_argument(
        "--optimizer-iterations",
        type=int,
        default=1,
        help="bounded integrated optimizer steps; seed evidence is reported from actual slots",
    )
    parser.add_argument(
        "--optimizer-timeout-generations",
        type=int,
        default=8,
        help="per-candidate Phase 4 timeout budget for optimizer runs (default: 8)",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    raw_config = load_config(args.config)
    config = PhysicsConfig.from_mapping(raw_config)
    if config.max_cells != DEFAULT_MAX_CELLS:
        raise ValueError("Phase 1 default config must keep max_cells=1024")
    status = build_status(raw_config)
    if not status["phase1_physics_implemented"]:
        raise ValueError("config must explicitly enable Phase 1 physics")
    status["seed"] = args.seed
    status["generations"] = args.generations
    status["performance"] = run_headless(args.seed, args.generations, config)
    if args.population:
        if not status["phase3_runtime_implemented"]:
            raise ValueError("config must explicitly enable Phase 3 runtime")
        status["population_performance"] = run_population_headless(
            seed=args.seed,
            generations=args.generations,
            config=config,
        )
    if args.experiment:
        if not status["phase4_io_learning_implemented"]:
            raise ValueError("config must explicitly enable Phase 4 I/O learning")
        experiment = load_experiment_config(args.experiment_config)
        measurement = compare_baseline_trained(
            seeds=(args.seed, args.seed + 1, args.seed + 2),
            config=config,
            experiment=experiment,
        )
        status["experiment_measurement"] = {
            "seed_count": measurement.seed_count,
            "baseline_successes": measurement.baseline_successes,
            "trained_successes": measurement.trained_successes,
            "baseline_no_input_clean": measurement.baseline_no_input_clean,
            "trained_no_input_clean": measurement.trained_no_input_clean,
            "baseline_alternate_input_clean": measurement.baseline_alternate_input_clean,
            "trained_alternate_input_clean": measurement.trained_alternate_input_clean,
            "criterion": measurement.criterion,
            "learning_claim": measurement.learning_claim,
        }
    if args.optimizer:
        if not status["phase5_optimizer_implemented"]:
            raise ValueError("config must explicitly enable Phase 5 optimizer")
        optimizer_experiment = load_experiment_config(args.experiment_config)
        if args.optimizer_timeout_generations < 0:
            raise ValueError("optimizer timeout generations must be non-negative")
        optimizer_values = optimizer_experiment.to_dict()
        optimizer_values["evaluation_timeout_generations"] = min(
            optimizer_values["evaluation_timeout_generations"],
            args.optimizer_timeout_generations,
        )
        optimizer_experiment = ExperimentConfig(**optimizer_values)
        status["optimizer_measurement"] = run_optimizer_headless(
            seeds=(args.seed, args.seed + 1, args.seed + 2, args.seed + 3),
            base_config=config,
            experiment=optimizer_experiment,
            iterations=args.optimizer_iterations,
        )
    if args.as_json:
        print(json.dumps(status, sort_keys=True))
    else:
        print(f"UniverseGenome Phase {status['phase']} headless run")
        print(json.dumps(status["performance"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
