"""Headless runner and bounded performance reporting through Phase 2B."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import Any

from .physics import PhysicsConfig, create_universe, step
from .state import DEFAULT_MAX_CELLS, HP_BITS, LATENT_BITS, STRUCTURE_BITS


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema_version") != 1:
        raise ValueError("unsupported config schema_version")
    return data


def build_status(config: dict[str, Any]) -> dict[str, Any]:
    phase1 = bool(config.get("features", {}).get("phase1_physics", False))
    phase2a = bool(config.get("features", {}).get("phase2a_bond_physics", False))
    phase2b = bool(config.get("features", {}).get("phase2b_latent_operators", False))
    return {
        "project": "UniverseGenome",
        "phase": 2 if phase2a and phase1 else (1 if phase1 else 0),
        "phase0_scaffold": not phase1,
        "phase1_physics_implemented": phase1,
        "phase2a_bond_physics_implemented": phase2a and phase1,
        "phase2b_latent_operators_implemented": phase2b and phase2a and phase1,
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
            "Phase 2C fusion"
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
    noise_spawn_count = 0
    last_metrics = None
    for _ in range(generations):
        last_metrics = step(state)
        collision_count += last_metrics.collision_count
        bond_contact_count += last_metrics.bond_contact_count
        latent_transmission_count += last_metrics.latent_transmission_count
        noise_spawn_count += last_metrics.noise_spawn_count
    elapsed = max(time.perf_counter() - started, 1e-12)
    return {
        "generations": generations,
        "generation": state.generation,
        "active_cells": len(state.active_slots()),
        "collision_count": collision_count,
        "bond_contact_count": bond_contact_count,
        "latent_transmission_count": latent_transmission_count,
        "noise_spawn_count": noise_spawn_count,
        "generations_per_second": generations / elapsed if generations else 0.0,
        "last_step_generations_per_second": last_metrics.generations_per_second if last_metrics else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UniverseGenome headless Phase 2B runner")
    parser.add_argument("--config", default="config/default.json")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--generations", type=int, default=0)
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
    if args.as_json:
        print(json.dumps(status, sort_keys=True))
    else:
        print(f"UniverseGenome Phase {status['phase']} headless run")
        print(json.dumps(status["performance"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
