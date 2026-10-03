"""Snapshot metadata contracts."""

from dataclasses import dataclass


SNAPSHOT_FORMAT_VERSION = 1


@dataclass(frozen=True)
class SnapshotMetadata:
    format_version: int
    generation: int
    seed: int
