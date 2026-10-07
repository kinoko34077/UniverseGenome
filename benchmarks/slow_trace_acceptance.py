"""Acceptance measurement harness for #135 D1 slow-trace implementation.

This module is intentionally side-effect free: it measures one checked-out
repository tree. The temporary #135 acceptance workflow runs the same harness
against the accepted pre-D1 baseline and the implementation head.
"""

from __future__ import annotations

import argparse
from array import array
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.physics import PhysicsConfig, create_universe, step
from search.evolution import SteadyStateOptimizer

PREEXISTING_ARRAYS = (
    ("lifecycle", "B"),
    ("x", "B"),
    ("y", "B"),
    ("structure", "H"),
    ("latent", "H"),
    ("hp", "B"),
    ("bond_strength", "B"),
    ("direction", "B"),
    ("speed_code", "B"),
    ("age", "I"),
    ("black_hole_timer", "I"),
)


def _config_for_density(density: int) -> PhysicsConfig:
    payload = json.loads((ROOT / "config" / "default.json").read_text(encoding="utf-8"))
    payload["physics"]["initial_density"] = int(density)
    return PhysicsConfig.from_mapping(payload)


def _update_array_digest(digest: Any, values: Any, typecode: str) -> None:
    packed = array(typecode, (int(value) for value in values))
    if sys.byteorder != "little" and packed.itemsize > 1:
        packed.byteswap()
    digest.update(packed.tobytes())


def _update_state_digest(digest: Any, state: Any) -> None:
    digest.update(int(state.generation).to_bytes(8, "little", signed=False))
    for name, typecode in PREEXISTING_ARRAYS:
        _update_array_digest(digest, getattr(state, name), typecode)


def compatibility_fingerprint(*, density: int, generations: int) -> str:
    digest = hashlib.sha256()
    digest.update(f"density={density};generations={generations}".encode("ascii"))
    config = _config_for_density(density)
    for seed in range(32):
        state = create_universe(seed=seed, config=config)
        digest.update(int(seed).to_bytes(4, "little", signed=False))
        for _ in range(generations):
            step(state)
        _update_state_digest(digest, state)
    return digest.hexdigest()


def fingerprint_report(generations: int) -> dict[str, Any]:
    return {
        "kind": "UniverseGenomeD1InertCompatibilityFingerprint",
        "generations": int(generations),
        "seed_range": [0, 31],
        "preexisting_arrays": [name for name, _ in PREEXISTING_ARRAYS],
        "density4": compatibility_fingerprint(density=4, generations=generations),
        "density32": compatibility_fingerprint(density=32, generations=generations),
    }


def _benchmark_density(
    *,
    density: int,
    generations: int,
    warmup: int,
    repeats: int,
) -> dict[str, Any]:
    config = _config_for_density(density)
    samples: list[float] = []
    for repeat in range(repeats):
        state = create_universe(seed=1000 + repeat, config=config)
        for _ in range(warmup):
            step(state)
        started = time.perf_counter()
        for _ in range(generations):
            step(state)
        elapsed = max(time.perf_counter() - started, 1e-12)
        samples.append(generations / elapsed)
    return {
        "density": density,
        "generations_per_repeat": generations,
        "warmup_generations": warmup,
        "repeats": repeats,
        "generations_per_second_samples": samples,
        "median_generations_per_second": statistics.median(samples),
    }


def _snapshot_bytes(density: int) -> int:
    config = _config_for_density(density)
    state = create_universe(seed=0, config=config)
    for _ in range(16):
        step(state)
    payload = json.dumps(
        state.to_snapshot(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return len(payload)


def measurement_report(
    *,
    generations: int,
    warmup: int,
    repeats: int,
) -> dict[str, Any]:
    config = _config_for_density(4)
    state = create_universe(seed=0, config=config)
    slow_trace = getattr(state, "slow_trace", None)
    raw_trace_bytes = len(slow_trace) if isinstance(slow_trace, (bytes, bytearray)) else 0
    trace_container_bytes = sys.getsizeof(slow_trace) if slow_trace is not None else 0

    optimizer = SteadyStateOptimizer.from_defaults(
        base_seed=0,
        base_config=config,
    )
    optimizer_snapshot_bytes = len(
        json.dumps(
            optimizer.to_snapshot(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )

    return {
        "kind": "UniverseGenomeD1Measurement",
        "trace": {
            "raw_bytes_per_universe": raw_trace_bytes,
            "raw_bytes_across_128_slots": raw_trace_bytes * 128,
            "python_container_bytes_per_universe": trace_container_bytes,
            "storage_type": type(slow_trace).__name__ if slow_trace is not None else None,
        },
        "throughput": {
            "density4": _benchmark_density(
                density=4,
                generations=generations,
                warmup=warmup,
                repeats=repeats,
            ),
            "density32": _benchmark_density(
                density=32,
                generations=generations,
                warmup=warmup,
                repeats=repeats,
            ),
        },
        "snapshot_bytes": {
            "density4_universe": _snapshot_bytes(4),
            "density32_universe": _snapshot_bytes(32),
            "optimizer_128_slots": optimizer_snapshot_bytes,
        },
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    sub = result.add_subparsers(dest="command", required=True)

    fp = sub.add_parser("fingerprint")
    fp.add_argument("--generations", type=int, default=1024)

    measure = sub.add_parser("measure")
    measure.add_argument("--generations", type=int, default=512)
    measure.add_argument("--warmup", type=int, default=32)
    measure.add_argument("--repeats", type=int, default=3)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "fingerprint":
        report = fingerprint_report(args.generations)
    else:
        report = measurement_report(
            generations=args.generations,
            warmup=args.warmup,
            repeats=args.repeats,
        )
    json.dump(report, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
