"""#226 experimental opt-in Linux spawn evaluator for original D15 journal.

The default serial path remains authoritative. This helper never opens a journal
nor takes the writer lock; children receive an immutable optimizer snapshot,
evaluate disjoint native slots, and send only original serialized slot patches.
A parent still owns writer lock, patch ordering and original finalizer.
"""
from __future__ import annotations

import ctypes
import fcntl
import multiprocessing as mp
from multiprocessing.connection import wait
import os
from pathlib import Path
import resource
import signal
import sys
import time
from typing import Any

from research.d15_sparse_recovery_213 import ResourceBudget, JournalIntegrityError
from search.evolution import SteadyStateOptimizer

RESERVE_BYTES = 128 * 1024 * 1024
MIN_WORKER_VIRTUAL_BYTES = 192 * 1024 * 1024
MAX_BATCH_WALL_SECONDS = 180
MAX_CHILDREN = 4


def _proc_bytes(pid: int) -> tuple[int, int]:
    """Virtual size and resident memory from Linux /proc, or fail closed."""
    with Path(f"/proc/{pid}/statm").open("r", encoding="ascii") as stream:
        virtual_pages, resident_pages, *_ = stream.read().split()
    size = os.sysconf("SC_PAGE_SIZE")
    return int(virtual_pages)*size, int(resident_pages)*size


def _assert_not_inherited_writer_lock(lock_path: str) -> None:
    """Reject any child with its parent's writer lock descriptor still open."""
    expected = os.path.realpath(lock_path)
    for fd in Path("/proc/self/fd").iterdir():
        try:
            dest = os.readlink(fd)
        except (FileNotFoundError, OSError):
            continue
        if dest == expected or dest == expected + " (deleted)":
            raise JournalIntegrityError("child inherited D15 writer lock FD")


def _set_parent_death_signal(parent_pid: int) -> None:
    if not sys.platform.startswith("linux"):
        raise RuntimeError("opt-in workers require Linux")
    libc = ctypes.CDLL(None, use_errno=True)
    # Linux PR_SET_PDEATHSIG=1; the target PID must still be the parent after
    # installation or a parent-killed-during-start child must die closed.
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "PR_SET_PDEATHSIG failed")
    if os.getppid() != parent_pid:
        os._exit(92)


def _child_main(conn, original_snapshot: dict, parent_pid: int,
                lock_path: str, virtual_limit_bytes: int) -> None:
    try:
        _set_parent_death_signal(parent_pid)
        _assert_not_inherited_writer_lock(lock_path)
        virtual, _rss = _proc_bytes(os.getpid())
        if virtual + 24*1024*1024 > virtual_limit_bytes:
            raise MemoryError("worker interpreter virtual size exceeds hard cap")
        resource.setrlimit(
            resource.RLIMIT_AS, (virtual_limit_bytes, virtual_limit_bytes),
        )
        opt = SteadyStateOptimizer.from_snapshot(original_snapshot)
        conn.send(("READY", os.getpid()))
        while True:
            message = conn.recv()
            if not isinstance(message, tuple) or not message:
                raise JournalIntegrityError("invalid worker request")
            if message[0] == "STOP":
                return
            if message[0] != "EVAL" or len(message) != 2:
                raise JournalIntegrityError("unexpected worker request")
            indices = message[1]
            if (not isinstance(indices, tuple) or
                any(type(i) is not int or i < 0 or i >= 128 for i in indices)
                or tuple(sorted(set(indices))) != indices):
                raise JournalIntegrityError("worker requested invalid slot indices")
            patches = []
            for i in indices:
                slot = opt.slots[i]
                if slot.index != i:
                    raise JournalIntegrityError("worker original slot id mismatch")
                opt._evaluate_slot(slot)
                patches.append((i, slot.to_dict()))
            conn.send(("RESULT", patches, _proc_bytes(os.getpid())[1]))
    except BaseException as exc:
        # Failure is not silently interpreted as a slot record by the parent.
        try:
            conn.send(("ERROR", type(exc).__name__, str(exc)))
        except (OSError, EOFError, BrokenPipeError):
            pass
    finally:
        conn.close()


class SpawnEvaluator:
    """Bounded no-fork writer-safe pool, for D15 opt-in only.

    This is a prototype. The entire optimizer is rebuilt inside each worker,
    so startup cost and group memory limit are part of acceptance.
    """
    def __init__(self, original_snapshot: dict, *, workers: int,
                 budget: ResourceBudget, lock_path: Path) -> None:
        if type(workers) is not int or workers not in (2, 4):
            raise ValueError("D15 spawn workers only accept 2 or 4")
        if sys.platform != "linux":
            raise RuntimeError("D15 spawn workers require Linux")
        if not isinstance(original_snapshot, dict):
            raise ValueError("D15 worker base snapshot required")
        self.snapshot = original_snapshot
        self.workers = workers
        self.budget = budget
        self.lock_path = str(lock_path.absolute())
        self.context = mp.get_context("spawn")
        self.processes = []
        self.pipes = []
        self._processed: set[int] = set()
        self.virtual_cap = 0
        self.peak_aggregate_rss = 0

    def _admit(self) -> None:
        parent_rss = _proc_bytes(os.getpid())[1]
        pids = [proc.pid for proc in self.processes]
        if any(pid is None for pid in pids):
            raise MemoryError("unstarted worker cannot be admitted")
        child_rss = sum(_proc_bytes(int(pid))[1] for pid in pids)
        total = parent_rss + child_rss
        self.peak_aggregate_rss = max(total, self.peak_aggregate_rss)
        self.budget.admit(
            estimated_additional_bytes=RESERVE_BYTES,
            current_rss_bytes=total,
            available_host_bytes=self.budget.available_host_bytes(),
        )
        if self.virtual_cap:
            # Even if all workers grew to their OS-enforced per-worker virtual
            # caps, leave space for the current parent and next patch.
            if parent_rss + self.workers*self.virtual_cap + RESERVE_BYTES > self.budget.limit_bytes:
                raise MemoryError("aggregate worker hard virtual cap exceeds memory budget")

    def __enter__(self) -> "SpawnEvaluator":
        parent_rss = _proc_bytes(os.getpid())[1]
        headroom = self.budget.limit_bytes - parent_rss - RESERVE_BYTES
        self.virtual_cap = headroom // self.workers
        if self.virtual_cap < MIN_WORKER_VIRTUAL_BYTES:
            raise MemoryError("no sufficient virtual memory for even bounded spawn workers")
        # A hard per-worker virtual limit ensures workers cannot grow beyond
        # their share; parent also samples aggregate live RSS every 250ms.
        self._admit()
        parent_pid = os.getpid()
        try:
            for _ in range(self.workers):
                parent, child = self.context.Pipe(duplex=True)
                proc = self.context.Process(
                    target=_child_main,
                    args=(child, self.snapshot, parent_pid,
                          self.lock_path, self.virtual_cap),
                )
                proc.start()
                child.close()
                self.processes.append(proc)
                self.pipes.append(parent)
            self._read_messages(set(range(self.workers)), expected="READY",
                                timeout_seconds=35)
            self._admit()
        except BaseException:
            self.close()
            raise
        return self

    def _read_messages(self, pending: set[int], *, expected: str,
                       timeout_seconds: float) -> dict[int, tuple]:
        replies = {}
        end = time.monotonic()+timeout_seconds
        while pending:
            self._admit()
            for i in pending:
                if not self.processes[i].is_alive() and not self.pipes[i].poll():
                    raise JournalIntegrityError("D15 worker exited before complete response")
            remaining = end-time.monotonic()
            if remaining <= 0:
                raise TimeoutError("D15 worker batch exceeded bounded wall time")
            handles = [self.pipes[i] for i in sorted(pending)]
            ready = wait(handles, timeout=min(0.25,remaining))
            for handle in ready:
                index = self.pipes.index(handle)
                try:
                    response = handle.recv()
                except (EOFError, OSError) as exc:
                    raise JournalIntegrityError("D15 worker pipe disconnected") from exc
                if not isinstance(response, tuple) or not response:
                    raise JournalIntegrityError("invalid D15 worker response")
                if response[0] == "ERROR":
                    raise JournalIntegrityError(f"D15 worker failure: {response[1:]}")
                if response[0] != expected:
                    raise JournalIntegrityError("unexpected D15 worker state transition")
                replies[index] = response
                pending.remove(index)
        self._admit()
        return replies

    def evaluate(self, indices: tuple[int, ...]) -> dict[int, dict]:
        if (not indices or len(indices) > 32 or
            any(type(i) is not int or i not in range(128) for i in indices) or
            tuple(sorted(set(indices))) != indices or
            self._processed.intersection(indices)):
            raise JournalIntegrityError("invalid/repeated bounded D15 worker batch")
        slices = {
            worker: tuple(indices[worker::self.workers])
            for worker in range(self.workers)
        }
        participants = {k for k,v in slices.items() if v}
        for worker in sorted(participants):
            self.pipes[worker].send(("EVAL", slices[worker]))
        answers = self._read_messages(participants,expected="RESULT",
                                     timeout_seconds=MAX_BATCH_WALL_SECONDS)
        merged: dict[int,dict] = {}
        for worker, response in answers.items():
            records = response[1]
            if (not isinstance(records, list)
                    or [i for i,_ in records] != list(slices[worker])):
                raise JournalIntegrityError("worker slot response order mismatch")
            for index, payload in records:
                if index in merged or not isinstance(payload, dict):
                    raise JournalIntegrityError("duplicate/invalid D15 worker output")
                merged[index] = payload
        if set(merged) != set(indices):
            raise JournalIntegrityError("missing D15 worker slot output")
        self._processed.update(indices)
        return merged

    def close(self) -> None:
        for conn in self.pipes:
            try:
                conn.send(("STOP",))
            except (EOFError, OSError, BrokenPipeError):
                pass
        for proc in self.processes:
            proc.join(timeout=1)
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=1)
            if proc.is_alive():
                proc.kill()
                proc.join(timeout=1)
        for conn in self.pipes:
            conn.close()
        self.pipes = []
        self.processes = []

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
