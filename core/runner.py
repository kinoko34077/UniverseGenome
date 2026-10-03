"""Headless Phase 0 entrypoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .geometry import FIXED_POINT_SIZE, LOGICAL_SIZE, SUBDIVISIONS_PER_TILE
from .state import DEFAULT_MAX_CELLS, HP_BITS, LATENT_BITS, STRUCTURE_BITS


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema_version") != 1:
        raise ValueError("unsupported config schema_version")
    return data


def build_status(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": "UniverseGenome",
        "phase": 0,
        "phase0_scaffold": True,
        "phase1_physics_implemented": False,
        "logical_size": LOGICAL_SIZE,
        "subdivisions_per_tile": SUBDIVISIONS_PER_TILE,
        "fixed_point_size": FIXED_POINT_SIZE,
        "max_cells": config["world"]["max_cells"],
        "state_bits": {
            "structure": STRUCTURE_BITS,
            "latent": LATENT_BITS,
            "hp": HP_BITS,
        },
        "next_phase": "Phase 1 minimal deterministic single-universe physics",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UniverseGenome headless Phase 0 scaffold")
    parser.add_argument("--config", default="config/default.json")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if config["world"]["max_cells"] != DEFAULT_MAX_CELLS:
        raise ValueError("Phase 0 default config must keep max_cells=1024")

    status = build_status(config)
    if args.as_json:
        print(json.dumps(status, sort_keys=True))
    else:
        print("UniverseGenome Phase 0 scaffold")
        print("Phase 1 physics: not implemented")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
