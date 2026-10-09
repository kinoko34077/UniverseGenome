"""D15 #213 isolated fail-closed per-world sparse checkpoint primitive.

This module is not wired to the native genetic optimizer. A native
selection round must not use it until an accepted adapter proves that the
post-evaluation selection phase runs exactly once after all 128 worlds.
"""
from __future__ import annotations

from dataclasses import dataclass
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping


class JournalIntegrityError(ValueError):
    """Journal cannot be trusted for an authoritative round."""


def _bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_limited(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise JournalIntegrityError("checkpoint file exceeds admission bound")
    return data


def _atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    try:
        with temp.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        if os.name == "posix":
            # Durable rename: a killed writer cannot expose a partial final file.
            descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        if temp.exists():
            temp.unlink()


@dataclass(frozen=True)
class ResourceBudget:
    memory_mib: int = 1536

    def __post_init__(self) -> None:
        if type(self.memory_mib) is not int or not 1024 <= self.memory_mib <= 2048:
            raise ValueError("D15 memory_mib must be an integer 1024..2048")

    @property
    def limit_bytes(self) -> int:
        return self.memory_mib * 1024 * 1024

    def admit(
        self,
        *,
        estimated_additional_bytes: int,
        current_rss_bytes: int,
        available_host_bytes: int,
    ) -> None:
        for value in (estimated_additional_bytes, current_rss_bytes, available_host_bytes):
            if type(value) is not int or value < 0:
                raise ValueError("resource admission requires nonnegative byte counts")
        if current_rss_bytes + estimated_additional_bytes > self.limit_bytes:
            raise MemoryError("D15 projected RSS exceeds configured user ceiling")
        # Always retain some host memory, even if process budget has room.
        if estimated_additional_bytes > (available_host_bytes * 3) // 4:
            raise MemoryError("D15 projected new allocation exceeds host headroom")

    @staticmethod
    def current_rss_bytes() -> int:
        """Linux current RSS (not peak ru_maxrss); fail closed elsewhere."""
        with Path("/proc/self/statm").open("r", encoding="ascii") as stream:
            _size, resident, *_ = stream.read().split()
        return int(resident) * os.sysconf("SC_PAGE_SIZE")

    @staticmethod
    def available_host_bytes() -> int:
        """Conservative Linux MemAvailable; caller must account for cgroup limits."""
        with Path("/proc/meminfo").open("r", encoding="ascii") as stream:
            for line in stream:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
        raise RuntimeError("D15 host availability is unavailable")


@dataclass(frozen=True)
class RecoveryView:
    snapshot: dict[str, Any]
    next_index: int
    evaluation_complete: bool
    final_snapshot: dict[str, Any] | None
    final_committed: bool
    read_only: bool


class SparseEvaluationJournal:
    """Atomic sparse journal: one full-round base, incremental changed slots.

    The full state is written only at committed round boundaries. Patch order
    is strictly consecutive original slot indices. A corrupt tail can be
    salvaged *read-only* for inspection, never accepted silently for writing.
    """

    SCHEMA = 1
    MAX_BASE = 256 * 1024 * 1024
    MAX_PATCH = 16 * 1024 * 1024
    MAX_SLOTS_PER_PATCH = 32

    def __init__(
        self, root: Path, manifest: dict[str, Any], base: dict[str, Any],
        patches: list[dict[str, Any]], *, read_only: bool,
        final: dict[str, Any] | None,
    ) -> None:
        self.root = root
        self.manifest = manifest
        self._base = base
        self._patches = patches
        self._read_only = read_only
        self._final = final

    @classmethod
    def create(
        cls,
        root: Path,
        *,
        base_snapshot: Mapping[str, Any],
        source_commit: str,
        max_bytes: int = 128 * 1024 * 1024,
    ) -> "SparseEvaluationJournal":
        if not isinstance(source_commit, str) or not source_commit.strip():
            raise ValueError("source commit required")
        if type(max_bytes) is not int or not 1 * 1024 * 1024 <= max_bytes <= cls.MAX_BASE:
            raise ValueError("D15 journal must have 1..256MiB total budget")
        if "slots" not in base_snapshot or not isinstance(base_snapshot["slots"], list):
            raise ValueError("journal base requires indexed native slot list")
        slots = base_snapshot["slots"]
        if not slots or len(slots) > 128 or any(
            not isinstance(slot, Mapping) or slot.get("index") != i
            for i, slot in enumerate(slots)
        ):
            raise ValueError("base slots must have a complete indexed ordering")
        root = Path(root)
        if root.exists() and any(root.iterdir()):
            raise FileExistsError("journal directory must be empty")
        raw = _bytes(base_snapshot)
        if len(raw) > cls.MAX_BASE or len(raw) + 4096 > max_bytes:
            raise ValueError("base snapshot exceeds disk budget")
        manifest = {
            "schema": cls.SCHEMA,
            "kind": "UniverseGenomeSparseEvaluationJournal",
            "source_commit": source_commit,
            "slot_count": len(slots),
            "base_generation": int(base_snapshot["generation"]),
            "base_sha256": _hash(raw),
            "max_bytes": max_bytes,
        }
        _atomic(root / "base.json", raw)
        _atomic(root / "manifest.json", _bytes(manifest))
        return cls.open(root, source_commit=source_commit)

    @classmethod
    def open(
        cls, root: Path, *, source_commit: str, salvage_last: bool = False,
    ) -> "SparseEvaluationJournal":
        root = Path(root)
        try:
            manifest = json.loads(_read_limited(root / "manifest.json", 65536))
            if (
                manifest.get("schema") != cls.SCHEMA
                or manifest.get("kind") != "UniverseGenomeSparseEvaluationJournal"
                or manifest.get("source_commit") != source_commit
            ):
                raise JournalIntegrityError("journal schema or source is incompatible")
            base_raw = _read_limited(root / "base.json", cls.MAX_BASE)
            if _hash(base_raw) != manifest["base_sha256"]:
                raise JournalIntegrityError("journal base checksum mismatch")
            base = json.loads(base_raw)
            count = int(manifest["slot_count"])
            if not 1 <= count <= 128 or len(base["slots"]) != count:
                raise JournalIntegrityError("journal base slot count mismatch")
            if [x["index"] for x in base["slots"]] != list(range(count)):
                raise JournalIntegrityError("journal base slot order mismatch")
            if int(base["generation"]) != manifest["base_generation"]:
                raise JournalIntegrityError("journal base generation mismatch")
            limit = int(manifest["max_bytes"])
            if not 1 * 1024 * 1024 <= limit <= cls.MAX_BASE:
                raise JournalIntegrityError("journal max byte budget invalid")
            files = sorted(root.glob("batch-*.json"))
            expected_index = 0
            previous = manifest["base_sha256"]
            patches: list[dict[str, Any]] = []
            read_only = False
            for i, path in enumerate(files):
                try:
                    if path.name != f"batch-{i:05d}.json":
                        raise JournalIntegrityError("journal patch sequence has a gap")
                    packet_raw = _read_limited(path, cls.MAX_PATCH)
                    packet = json.loads(packet_raw)
                    checksum = packet.pop("sha256", None)
                    if checksum != _hash(_bytes(packet)):
                        raise JournalIntegrityError("journal patch checksum mismatch")
                    slots_patch = packet["slots"]
                    length = len(slots_patch)
                    if (
                        packet["previous"] != previous
                        or packet["start"] != expected_index
                        or packet["end"] != expected_index + length
                        or not 1 <= length <= cls.MAX_SLOTS_PER_PATCH
                        or packet["end"] > count
                        or [slot["index"] for slot in slots_patch]
                        != list(range(expected_index, expected_index + length))
                    ):
                        raise JournalIntegrityError("journal order/chain integrity failed")
                    previous = checksum
                    expected_index += length
                    patches.append(packet)
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    if not salvage_last or i != len(files)-1:
                        raise JournalIntegrityError("journal committed patch is corrupt") from exc
                    read_only = True
                    break
            final = None
            final_path = root / "final.json"
            if final_path.exists():
                if read_only or expected_index != count:
                    raise JournalIntegrityError("final state exists with incomplete evaluation")
                payload = json.loads(_read_limited(final_path, cls.MAX_BASE))
                if (payload.get("previous") != previous
                    or payload.get("sha256") != _hash(_bytes(payload.get("snapshot")))
                    or payload["snapshot"].get("generation") != manifest["base_generation"]+1):
                    raise JournalIntegrityError("committed selected state is corrupt")
                final = payload["snapshot"]
            total = sum(x.stat().st_size for x in root.iterdir() if x.is_file())
            if total > limit:
                raise JournalIntegrityError("journal disk admission budget exceeded")
            return cls(root, manifest, base, patches, read_only=read_only,
                       final=final)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            if isinstance(exc, JournalIntegrityError):
                raise
            raise JournalIntegrityError("journal cannot be recovered") from exc

    def recover(self) -> RecoveryView:
        state = copy.deepcopy(self._base)
        offset = 0
        for patch in self._patches:
            for slot in patch["slots"]:
                state["slots"][offset] = copy.deepcopy(slot)
                offset += 1
        count = self.manifest["slot_count"]
        return RecoveryView(
            snapshot=state, next_index=offset,
            evaluation_complete=offset == count,
            final_snapshot=copy.deepcopy(self._final),
            final_committed=self._final is not None,
            read_only=self._read_only,
        )

    def _footprint(self) -> int:
        return sum(f.stat().st_size for f in self.root.iterdir() if f.is_file())

    def commit(self, slots: list[Mapping[str, Any]]) -> None:
        if self._read_only or self._final is not None:
            raise JournalIntegrityError("journal is salvaged or already finalized")
        current = sum(len(p["slots"]) for p in self._patches)
        if (
            not isinstance(slots, list)
            or not 1 <= len(slots) <= self.MAX_SLOTS_PER_PATCH
            or current + len(slots) > self.manifest["slot_count"]
            or any(not isinstance(x, Mapping) or x.get("index") != current+i
                   for i,x in enumerate(slots))
        ):
            raise ValueError("journal requires contiguous new evaluated slot records")
        previous = (self._patches[-1]["checksum"] if self._patches else
                    self.manifest["base_sha256"])
        packet = {
            "start": current, "end": current+len(slots),
            "previous": previous,
            "slots": [dict(x) for x in slots],
        }
        checksum = _hash(_bytes(packet))
        saved = {**packet, "sha256": checksum}
        raw = _bytes(saved)
        if len(raw) > self.MAX_PATCH or self._footprint()+len(raw) > self.manifest["max_bytes"]:
            raise ValueError("journal patch exceeds declared disk budget")
        path = self.root / f"batch-{len(self._patches):05d}.json"
        if path.exists():
            raise FileExistsError("journal committed index already exists")
        _atomic(path, raw)
        packet["checksum"] = checksum
        self._patches.append(packet)

    def commit_final(self, selected_snapshot: Mapping[str, Any]) -> None:
        if self._read_only or self._final is not None:
            raise JournalIntegrityError("journal is readonly or already finalized")
        if sum(len(p["slots"]) for p in self._patches) != self.manifest["slot_count"]:
            raise ValueError("cannot commit selection before every world was evaluated")
        if selected_snapshot.get("generation") != self.manifest["base_generation"]+1:
            raise ValueError("selected round must advance exactly one outer generation")
        if len(selected_snapshot.get("slots", ())) != self.manifest["slot_count"]:
            raise ValueError("selected snapshot must preserve full population")
        previous = self._patches[-1]["checksum"]
        payload = {
            "previous": previous, "snapshot": dict(selected_snapshot),
            "sha256": _hash(_bytes(selected_snapshot)),
        }
        raw = _bytes(payload)
        if len(raw) > self.MAX_BASE or self._footprint()+len(raw) > self.manifest["max_bytes"]:
            raise ValueError("journal final checkpoint exceeds disk budget")
        _atomic(self.root / "final.json", raw)
        self._final = dict(selected_snapshot)
