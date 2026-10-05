"""Read-only baseline benchmarks for UniverseGenome performance workstream #93.

This module intentionally measures existing production paths without changing
physics, optimizer, API, GUI, or learning semantics. It separates projection
cost from JSON serialization cost so later optimization work has a stable
measurement boundary.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from typing import Any, Callable

from core.physics import create_universe, step
from server.runtime import PopulationRuntime

REPORT_SCHEMA_VERSION = 1
UNMEASURED_IN_THIS_SLICE = (
    "optimizer_step",
    "http_socket",
    "gui_polling",
)


def _timing_summary(unit: str, operations: int, elapsed_s: float) -> dict[str, Any]:
    count = int(operations)
    elapsed = float(elapsed_s)
    if count < 1:
        raise ValueError("operations must be positive")
    if elapsed <= 0:
        raise ValueError("elapsed_s must be positive")
    return {
        "unit": unit,
        "operations": count,
        "wall_s": elapsed,
        "operations_per_s": count / elapsed,
        "mean_ms_per_operation": elapsed / count * 1000.0,
    }


def _measure_calls(
    fn: Callable[[], Any],
    *,
    samples: int,
    timer: Callable[[], float] = time.perf_counter,
) -> tuple[dict[str, Any], Any]:
    if int(samples) < 1:
        raise ValueError("samples must be positive")
    last: Any = None
    started = timer()
    for _ in range(int(samples)):
        last = fn()
    elapsed = timer() - started
    return _timing_summary("calls", int(samples), elapsed), last


def _json_bytes(payload: dict[str, Any]) -> bytes:
    """Match server.app._json_response serialization semantics."""
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def benchmark_physics(
    *,
    seed: int,
    generations: int,
    warmup_generations: int,
) -> dict[str, Any]:
    if generations < 1:
        raise ValueError("physics generations must be positive")
    if warmup_generations < 0:
        raise ValueError("physics warmup must be non-negative")

    if warmup_generations:
        warm = create_universe(seed=seed)
        for _ in range(warmup_generations):
            step(warm)

    state = create_universe(seed=seed)
    started = time.perf_counter()
    for _ in range(generations):
        step(state)
    elapsed = time.perf_counter() - started
    result = _timing_summary("generations", generations, elapsed)
    result["final_generation"] = int(state.generation)
    return result


def benchmark_projection_and_serialization(
    *,
    seed: int,
    projection_samples: int,
    serialization_samples: int,
    warmup_projections: int,
    warmup_serializations: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if projection_samples < 1 or serialization_samples < 1:
        raise ValueError("projection/serialization samples must be positive")
    if warmup_projections < 0 or warmup_serializations < 0:
        raise ValueError("warmup samples must be non-negative")

    runtime = PopulationRuntime(base_seed=seed)
    try:
        for _ in range(warmup_projections):
            runtime.state()
        projection, payload = _measure_calls(runtime.state, samples=projection_samples)
        projection["slot_count"] = int(payload["slot_count"])

        for _ in range(warmup_serializations):
            _json_bytes(payload)
        serialization, encoded = _measure_calls(
            lambda: _json_bytes(payload),
            samples=serialization_samples,
        )
        serialization["payload_bytes"] = len(encoded)
        return projection, serialization
    finally:
        runtime.close()


def build_report(
    *,
    parameters: dict[str, Any],
    physics: dict[str, Any],
    projection: dict[str, Any],
    serialization: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "kind": "UniverseGenomePerformanceBaseline",
        "measurement_boundary": "read_only_existing_production_paths",
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "parameters": dict(parameters),
        "measurements": {
            "physics_step": dict(physics),
            "runtime_state_projection": dict(projection),
            "json_serialization": dict(serialization),
        },
        "not_measured": list(UNMEASURED_IN_THIS_SLICE),
    }


def run_benchmarks(args: argparse.Namespace) -> dict[str, Any]:
    parameters = {
        "seed": args.seed,
        "physics_generations": args.physics_generations,
        "projection_samples": args.projection_samples,
        "serialization_samples": args.serialization_samples,
        "warmup_generations": args.warmup_generations,
        "warmup_projections": args.warmup_projections,
        "warmup_serializations": args.warmup_serializations,
    }
    physics = benchmark_physics(
        seed=args.seed,
        generations=args.physics_generations,
        warmup_generations=args.warmup_generations,
    )
    projection, serialization = benchmark_projection_and_serialization(
        seed=args.seed,
        projection_samples=args.projection_samples,
        serialization_samples=args.serialization_samples,
        warmup_projections=args.warmup_projections,
        warmup_serializations=args.warmup_serializations,
    )
    return build_report(
        parameters=parameters,
        physics=physics,
        projection=projection,
        serialization=serialization,
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="UniverseGenome #93 read-only performance baseline")
    result.add_argument("--seed", type=int, default=0)
    result.add_argument("--physics-generations", type=int, default=200)
    result.add_argument("--projection-samples", type=int, default=5)
    result.add_argument("--serialization-samples", type=int, default=20)
    result.add_argument("--warmup-generations", type=int, default=10)
    result.add_argument("--warmup-projections", type=int, default=1)
    result.add_argument("--warmup-serializations", type=int, default=1)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    report = run_benchmarks(args)
    json.dump(report, sys.stdout, ensure_ascii=False, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
