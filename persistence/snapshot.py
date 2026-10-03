"""Snapshot API boundary.

Actual authoritative array serialization begins with Phase 1 because Phase 0
does not yet contain a universe state to serialize.
"""

from pathlib import Path
from typing import Any


class SnapshotNotImplemented(RuntimeError):
    pass


def save_snapshot(_path: str | Path, _state: Any) -> None:
    raise SnapshotNotImplemented("Phase 1 snapshot state is not implemented")


def load_snapshot(_path: str | Path) -> Any:
    raise SnapshotNotImplemented("Phase 1 snapshot state is not implemented")
