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
    owners = configured.get("blocking_owners", [])
    if not isinstance(owners, list) or not all(isinstance(owner, str) for owner in owners):
        raise ValueError("current_state.blocking_owners must be a list of strings")
    return {
        "acceptance_state": str(configured.get("acceptance_state", "remediation_in_progress")),
        "phase6_ready": bool(configured.get("phase6_ready", False)),
        "blocking_owners": list(owners),
        "readiness_owner": str(configured.get("readiness_owner", "#60")),
        "next_phase": str(
            configured.get("next_phase", "Readiness rerun (#60; Phase 6+ blocked)")
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
    phase6 = bool(config.get("features", {}).get("phase6_capabilities", False))
    phase6_multi_mapping = bool(
        config.get("features", {}).get("phase6_multi_mapping", False)
    )
    phase6_temporal_sequence = bool(
        config.get("features", {}).get("phase6_temporal_sequence", False)
    )
    phase6_multi_event_timing = bool(
        config.get("features", {}).get("phase6_multi_event_timing", False)
    )
    phase6_retention_relearning = bool(
        config.get("features", {}).get("phase6_retention_relearning", False)
    )
    phase6_noise_robustness = bool(
        config.get("features", {}).get("phase6_noise_robustness", False)
    )
    phase6_generalization = bool(
        config.get("features", {}).get("phase6_generalization", False)
    )
    phase6_multi_byte_sequences = bool(
        config.get("features", {}).get("phase6_multi_byte_sequences", False)
    )
    phase6_raw_utf8 = bool(
        config.get("features", {}).get("phase6_raw_utf8", False)
    )
    phase6_mixed_length_sequences = bool(
        config.get("features", {}).get("phase6_mixed_length_sequences", False)
    )
    return {
        "project": "UniverseGenome",
        "phase": (
            6
            if phase6 and phase5 and phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1
            else 5
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
        "phase6_capabilities_implemented": phase6 and phase5 and phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1,
        "phase6_multi_mapping_implemented": phase6_multi_mapping and phase6 and phase5 and phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1,
        "phase6_temporal_sequence_implemented": phase6_temporal_sequence and phase6_multi_mapping and phase6 and phase5 and phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1,
        "phase6_multi_event_timing_implemented": phase6_multi_event_timing and phase6_temporal_sequence and phase6_multi_mapping and phase6 and phase5 and phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1,
        "phase6_retention_relearning_implemented": phase6_retention_relearning and phase6_multi_event_timing and phase6_temporal_sequence and phase6_multi_mapping and phase6 and phase5 and phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1,
        "phase6_noise_robustness_implemented": phase6_noise_robustness and phase6_retention_relearning and phase6_multi_event_timing and phase6_temporal_sequence and phase6_multi_mapping and phase6 and phase5 and phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1,
        "phase6_generalization_implemented": phase6_generalization and phase6_noise_robustness and phase6_retention_relearning and phase6_multi_event_timing and phase6_temporal_sequence and phase6_multi_mapping and phase6 and phase5 and phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1,
        "phase6_multi_byte_sequences_implemented": phase6_multi_byte_sequences and phase6_generalization and phase6_noise_robustness and phase6_retention_relearning and phase6_multi_event_timing and phase6_temporal_sequence and phase6_multi_mapping and phase6 and phase5 and phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1,
        "phase6_raw_utf8_implemented": phase6_raw_utf8 and phase6_multi_byte_sequences and phase6_generalization and phase6_noise_robustness and phase6_retention_relearning and phase6_multi_event_timing and phase6_temporal_sequence and phase6_multi_mapping and phase6 and phase5 and phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1,
        "phase6_mixed_length_sequences_implemented": phase6_mixed_length_sequences and phase6_raw_utf8 and phase6_multi_byte_sequences and phase6_generalization and phase6_noise_robustness and phase6_retention_relearning and phase6_multi_event_timing and phase6_temporal_sequence and phase6_multi_mapping and phase6 and phase5 and phase4 and phase3 and phase2e and phase2d and phase2c and phase2b and phase2a and phase1,
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
        default=None,
        help=(
            "explicit per-candidate Phase 4 timeout override for optimizer runs; "
            "when omitted, preserve the experiment protocol unchanged"
        ),
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
            "mapping_count": measurement.mapping_count,
            "evaluation_case_count": measurement.evaluation_case_count,
            "counterfactual_input_byte": measurement.counterfactual_input_byte,
            "counterfactual_prefix": list(measurement.counterfactual_prefix),
            "counterfactual_input_sequence": list(
                measurement.counterfactual_input_sequence
            ),
            "output_event_count": measurement.output_event_count,
            "mapping_input_lengths": [
                len(item.mapping.input_bytes)
                for item in measurement.per_mapping
            ],
            "mapping_output_event_counts": [
                len(
                    getattr(item.mapping, "output_bytes", ())
                    or (
                        (item.mapping.output_byte,)
                        * measurement.output_event_count
                    )
                )
                for item in measurement.per_mapping
            ],
            "output_event_interval_generations": (
                measurement.output_event_interval_generations
            ),
            "retention_enabled": experiment.retention_enabled,
            "retention_delay_generations": experiment.retention_delay_generations,
            "retention_interference_repetitions": (
                experiment.retention_interference_repetitions
            ),
            "relearning_teacher_repetitions": (
                experiment.relearning_teacher_repetitions
            ),
            "noise_robustness_enabled": experiment.noise_robustness_enabled,
            "noise_robustness_rate_delta": experiment.noise_robustness_rate_delta,
            "baseline_successes": measurement.baseline_successes,
            "trained_successes": measurement.trained_successes,
            "baseline_no_input_clean": measurement.baseline_no_input_clean,
            "trained_no_input_clean": measurement.trained_no_input_clean,
            "baseline_alternate_input_clean": measurement.baseline_alternate_input_clean,
            "trained_alternate_input_clean": measurement.trained_alternate_input_clean,
            "baseline_prefix_input_clean": measurement.baseline_prefix_input_clean,
            "trained_prefix_input_clean": measurement.trained_prefix_input_clean,
            "baseline_sequence_counterfactual_clean": (
                measurement.baseline_sequence_counterfactual_clean
            ),
            "trained_sequence_counterfactual_clean": (
                measurement.trained_sequence_counterfactual_clean
            ),
            "retention_eligible_count": measurement.retention_eligible_count,
            "retained_count": measurement.retained_count,
            "forgotten_count": measurement.forgotten_count,
            "relearning_eligible_count": measurement.relearning_eligible_count,
            "relearned_count": measurement.relearned_count,
            "retention_rate": measurement.retention_rate,
            "relearning_rate": measurement.relearning_rate,
            "noise_robustness_eligible_count": (
                measurement.noise_robustness_eligible_count
            ),
            "noise_robust_count": measurement.noise_robust_count,
            "noise_failed_count": measurement.noise_failed_count,
            "noise_robustness_rate": measurement.noise_robustness_rate,
            "generalization_enabled": experiment.generalization_enabled,
            "held_out_mapping": (
                experiment.held_out_mapping.to_dict()
                if experiment.held_out_mapping is not None
                else None
            ),
            "training_qualified_count": measurement.training_qualified_count,
            "generalization_eligible_count": measurement.generalization_eligible_count,
            "generalized_count": measurement.generalized_count,
            "generalization_failed_count": measurement.generalization_failed_count,
            "generalization_rate": measurement.generalization_rate,
            "per_mapping": [
                {
                    "input_bytes": list(item.mapping.input_bytes),
                    **(
                        {"input_byte": item.mapping.input_byte}
                        if hasattr(item.mapping, "input_byte")
                        else {}
                    ),
                    "output_byte": item.mapping.output_byte,
                    "output_bytes": list(
                        getattr(item.mapping, "output_bytes", ())
                        or (item.mapping.output_byte,) * measurement.output_event_count
                    ),
                    "baseline_successes": item.baseline_successes,
                    "trained_successes": item.trained_successes,
                }
                for item in measurement.per_mapping
            ],
            "per_seed": [
                {
                    "seed": item.seed,
                    "retention_checkpoint_generations": list(
                        item.retention_checkpoint_generations
                    ),
                    "clean_noise_rate": item.clean_noise_rate,
                    "noisy_noise_rate": item.noisy_noise_rate,
                    "noisy_no_input_clean": (
                        item.noisy_no_input.success
                        if item.noisy_no_input is not None
                        else None
                    ),
                    "noisy_alternate_input_clean": (
                        item.noisy_alternate.success
                        if item.noisy_alternate is not None
                        else None
                    ),
                    "noisy_prefix_input_clean": (
                        item.noisy_prefix.success
                        if item.noisy_prefix is not None
                        else None
                    ),
                    "noisy_sequence_counterfactual_clean": (
                        item.noisy_sequence_counterfactual.success
                        if item.noisy_sequence_counterfactual is not None
                        else None
                    ),
                    "baseline_held_out_success": (
                        item.baseline_held_out.success
                        if item.baseline_held_out is not None
                        else None
                    ),
                    "trained_held_out_success": (
                        item.trained_held_out.success
                        if item.trained_held_out is not None
                        else None
                    ),
                    "baseline_held_out_event_generations": (
                        list(item.baseline_held_out.event_generations)
                        if item.baseline_held_out is not None
                        else []
                    ),
                    "trained_held_out_event_generations": (
                        list(item.trained_held_out.event_generations)
                        if item.trained_held_out is not None
                        else []
                    ),
                    "training_qualified": item.generalization_classification()[0],
                    "generalization_eligible": item.generalization_classification()[1],
                    "generalized": item.generalization_classification()[2],
                    "generalization_failed": item.generalization_classification()[3],
                    "mappings": [
                        {
                            "input_bytes": list(record.mapping.input_bytes),
                            "output_byte": record.mapping.output_byte,
                            "output_bytes": list(
                                getattr(record.mapping, "output_bytes", ())
                                or (
                                    (record.mapping.output_byte,)
                                    * measurement.output_event_count
                                )
                            ),
                            "baseline_success": record.baseline.success,
                            "trained_success": record.trained.success,
                            "baseline_events": [
                                {
                                    "kind": event.kind,
                                    "value": event.value,
                                    "generation": generation,
                                }
                                for event, generation in zip(
                                    record.baseline.autonomous_events,
                                    record.baseline.event_generations,
                                )
                            ],
                            "trained_events": [
                                {
                                    "kind": event.kind,
                                    "value": event.value,
                                    "generation": generation,
                                }
                                for event, generation in zip(
                                    record.trained.autonomous_events,
                                    record.trained.event_generations,
                                )
                            ],
                            "baseline_event_generations": list(
                                record.baseline.event_generations
                            ),
                            "trained_event_generations": list(
                                record.trained.event_generations
                            ),
                            "t0_success": record.t0.success,
                            "t1_success": (
                                record.t1.success if record.t1 is not None else None
                            ),
                            "t2_success": (
                                record.t2.success if record.t2 is not None else None
                            ),
                            "noisy_success": (
                                record.noisy.success
                                if record.noisy is not None
                                else None
                            ),
                            "noise_eligible": item.noise_classification(record)[0],
                            "noise_robust": item.noise_classification(record)[1],
                            "noise_failed": item.noise_classification(record)[2],
                            "t0_event_generations": list(
                                record.t0.event_generations
                            ),
                            "t1_event_generations": (
                                list(record.t1.event_generations)
                                if record.t1 is not None
                                else None
                            ),
                            "t2_event_generations": (
                                list(record.t2.event_generations)
                                if record.t2 is not None
                                else None
                            ),
                            "noisy_event_generations": (
                                list(record.noisy.event_generations)
                                if record.noisy is not None
                                else []
                            ),
                        }
                        for record in item.mapping_results
                    ],
                }
                for item in measurement.per_seed
            ],
            "criterion": measurement.criterion,
            "learning_claim": measurement.learning_claim,
        }
    if args.optimizer:
        if not status["phase5_optimizer_implemented"]:
            raise ValueError("config must explicitly enable Phase 5 optimizer")
        optimizer_experiment = load_experiment_config(args.experiment_config)
        protocol_mode = "canonical"
        if args.optimizer_timeout_generations is not None:
            if args.optimizer_timeout_generations < 0:
                raise ValueError("optimizer timeout generations must be non-negative")
            optimizer_values = optimizer_experiment.to_dict()
            optimizer_values["evaluation_timeout_generations"] = (
                args.optimizer_timeout_generations
            )
            optimizer_experiment = ExperimentConfig.from_mapping(optimizer_values)
            protocol_mode = "explicit_timeout_override"
        status["optimizer_protocol"] = {
            "mode": protocol_mode,
            "evaluation_timeout_generations": (
                optimizer_experiment.evaluation_timeout_generations
            ),
            "mapping_count": len(optimizer_experiment.mappings),
            "mappings": [
                mapping.to_dict()
                for mapping in optimizer_experiment.mappings
            ],
            "counterfactual_input_byte": optimizer_experiment.counterfactual_input_byte,
            "inter_input_generations": optimizer_experiment.inter_input_generations,
            "counterfactual_prefix": list(
                optimizer_experiment.counterfactual_prefix
            ),
            "counterfactual_input_sequence": list(
                optimizer_experiment.counterfactual_input_sequence
            ),
            "output_event_count": optimizer_experiment.output_event_count,
            "mapping_input_lengths": [
                len(mapping.input_bytes)
                for mapping in optimizer_experiment.mappings
            ],
            "mapping_output_event_counts": [
                len(
                    getattr(mapping, "output_bytes", ())
                    or (
                        (mapping.output_byte,)
                        * optimizer_experiment.output_event_count
                    )
                )
                for mapping in optimizer_experiment.mappings
            ],
            "output_event_interval_generations": (
                optimizer_experiment.output_event_interval_generations
            ),
            "retention_enabled": optimizer_experiment.retention_enabled,
            "retention_delay_generations": (
                optimizer_experiment.retention_delay_generations
            ),
            "retention_interference_repetitions": (
                optimizer_experiment.retention_interference_repetitions
            ),
            "relearning_teacher_repetitions": (
                optimizer_experiment.relearning_teacher_repetitions
            ),
            "noise_robustness_enabled": (
                optimizer_experiment.noise_robustness_enabled
            ),
            "noise_robustness_rate_delta": (
                optimizer_experiment.noise_robustness_rate_delta
            ),
            "generalization_enabled": optimizer_experiment.generalization_enabled,
            "held_out_mapping": (
                optimizer_experiment.held_out_mapping.to_dict()
                if optimizer_experiment.held_out_mapping is not None
                else None
            ),
            "experiment_config": args.experiment_config,
        }
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
