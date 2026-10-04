"""Versioned JSON snapshots for the current UniverseState persistence contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.physics import PhysicsConfig
from core.state import UniverseState


SNAPSHOT_FORMAT_VERSION = 1


def save_snapshot(path: str | Path, state: UniverseState) -> None:
    payload = state.to_snapshot()
    payload["format_version"] = SNAPSHOT_FORMAT_VERSION
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_snapshot(path: str | Path) -> UniverseState:
    try:
        payload: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("unable to read UniverseState snapshot") from exc
    if not isinstance(payload, dict) or payload.get("format_version") != SNAPSHOT_FORMAT_VERSION:
        raise ValueError("unsupported snapshot format")
    raw_config = payload.get("config")
    if not isinstance(raw_config, dict):
        raise ValueError("snapshot config is required")
    config = PhysicsConfig.from_mapping(raw_config)
    return UniverseState.from_snapshot(payload, config=config)
