"""#226 bounded Linux witness: inherited D15 writer flock, spawn, cgroup RSS.

Test-only. No optimizer/journal writes. A subprocess intentionally SIGKILLs its
parent while a known disposable child remains alive for a brief observation.
The harness always terminates that child and never deletes the writer lock.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import multiprocessing as mp
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


def _rss(pid: int) -> int:
    with Path(f"/proc/{pid}/statm").open(encoding="ascii") as stream:
        fields = stream.read().split()
    return int(fields[1]) * os.sysconf("SC_PAGE_SIZE")


def cgroup_v2_memory() -> dict[str, int | None]:
    """No inference of unrestricted memory when counters are missing."""
    root = Path("/sys/fs/cgroup")
    current = root / "memory.current"
    maximum = root / "memory.max"
    if not current.is_file() or not maximum.is_file():
        return {"current_bytes": None, "max_bytes": None, "remaining_bytes": None}
    now = int(current.read_text(encoding="ascii").strip())
    cap = maximum.read_text(encoding="ascii").strip()
    limit = None if cap == "max" else int(cap)
    return {"current_bytes": now, "max_bytes": limit,
            "remaining_bytes": None if limit is None else max(0, limit - now)}


def conservative_admit(parent_pid: int, worker_pids: list[int],
                       *, limit_mib: int = 1536, headroom_mib: int = 64) -> dict:
    if type(limit_mib) is not int or not 1024 <= limit_mib <= 2048:
        raise ValueError("invalid D15 resource limit")
    if type(headroom_mib) is not int or not 1 <= headroom_mib <= 256:
        raise ValueError("invalid required headroom")
    if len(worker_pids) > 4 or len(set(worker_pids)) != len(worker_pids):
        raise ValueError("invalid bounded worker pids")
    participants = [parent_pid, *worker_pids]
    rss = {str(pid): _rss(pid) for pid in participants}
    reserve = headroom_mib * 1024 * 1024
    # Conservative: summing RSS counts shared pages multiple times rather
    # than undercounting memory used by independent interpreter children.
    summed = sum(rss.values())
    cg = cgroup_v2_memory()
    if summed + reserve > limit_mib * 1024 * 1024:
        raise MemoryError("aggregate parent+worker RSS exceeds user budget")
    if cg["remaining_bytes"] is None:
        raise RuntimeError("bounded parallel admission needs cgroup-v2 memory headroom")
    if cg["remaining_bytes"] < reserve:
        raise MemoryError("cgroup memory headroom insufficient for workers")
    return {"individual_rss":rss,"conservative_rss_bytes":summed,
            "reserve_bytes":reserve,"cgroup":cg, "admitted":True}


def _idle(conn) -> None:
    try:
        conn.send(os.getpid())
    finally:
        conn.close()
    # Deliberate bounded orphan witness: test harness SIGTERM/SIGKILL in finally.
    time.sleep(20)


def intentional_parent_sigkill(method: str, child_pid_path: Path, lock_path: Path) -> None:
    if method not in ("fork", "spawn"):
        raise ValueError("unexpected start method")
    ctx = mp.get_context(method)
    with lock_path.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        receiver, sender = ctx.Pipe(duplex=False)
        proc = ctx.Process(target=_idle, args=(sender,))
        proc.start()
        sender.close()
        if not receiver.poll(8):
            proc.terminate()
            proc.join(timeout=2)
            raise RuntimeError("child not started")
        child_pid = receiver.recv()
        receiver.close()
        if child_pid != proc.pid:
            proc.terminate()
            proc.join(timeout=2)
            raise RuntimeError("child identity disagrees")
        child_pid_path.write_text(str(child_pid), encoding="ascii")
        # Parent is intentionally killed without flock(LOCK_UN).
        os.kill(os.getpid(), signal.SIGKILL)


def _try_new_writer(lock_path: Path) -> bool:
    with lock_path.open("a+b") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            return False
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        return True


def witness(method: str) -> dict:
    if sys.platform != "linux":
        raise RuntimeError("POSIX Linux-only lock inheritance witness")
    if method not in ("fork", "spawn"):
        raise ValueError("invalid start method")
    with tempfile.TemporaryDirectory(prefix="ug226-lock-") as td:
        root = Path(td)
        lock_path = root / "writer.lock"
        pidfile = root / "child.pid"
        proc = subprocess.run(
            [sys.executable, "-m", "benchmarks.perf_d15_worker_safety_226",
             "--intentionally-kill-parent", method, str(pidfile), str(lock_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=12,
        )
        if proc.returncode != -signal.SIGKILL:
            raise AssertionError(f"intended SIGKILL did not happen: {proc.returncode}")
        if not pidfile.exists():
            raise AssertionError("child pid missing")
        child_pid = int(pidfile.read_text(encoding="ascii"))
        try:
            os.kill(child_pid, 0)
            before_cleanup_lock_acquired = _try_new_writer(lock_path)
            if method == "fork" and before_cleanup_lock_acquired:
                raise AssertionError("fork inherited lock failure mode not reproduced")
            if method == "spawn" and not before_cleanup_lock_acquired:
                raise AssertionError("spawn unexpectedly holds writer lock")
            memory = {
                "worker_rss_bytes": _rss(child_pid),
                "host_cgroup": cgroup_v2_memory(),
            }
        finally:
            try:
                os.kill(child_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        # The writer lock is a persistent sibling name, not unlinked/reset.
        return {"method":method,
                "parent_killed":True,
                "child_alive_during_test":True,
                "new_writer_acquired_while_child_alive":before_cleanup_lock_acquired,
                "memory":memory}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--intentionally-kill-parent", nargs=3, default=None,
                   metavar=("METHOD","PIDFILE","LOCKFILE"))
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if args.intentionally_kill_parent:
        method, pidfile, lockfile = args.intentionally_kill_parent
        intentional_parent_sigkill(method, Path(pidfile), Path(lockfile))
        return
    if args.output is None:
        p.error("--output required for observations")
    results = [witness(m) for m in ("fork", "spawn")]
    admitted = conservative_admit(os.getpid(), [],
                                  limit_mib=1536, headroom_mib=64)
    result = {"kind":"P0_D15_FORK_WRITER_FD_INHERITANCE",
              "source_sha":subprocess.check_output(
                  ["git","rev-parse","HEAD"],text=True,timeout=10).strip(),
              "observations":results,
              "parent_alone_resource":admitted,
              "production_backend_changed":False,
              "D16_seed16384_experiment":False,
              "learning_claim":False}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",
                           encoding="utf-8")
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__ == "__main__":
    main()
