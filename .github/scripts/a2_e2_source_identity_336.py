"""#336: read-only frozen Git blob inventory guard, never starts native physics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

LOCK = Path(".github/a2-e2-reviewed-code-lock-336.json")
ROOTS = ("core", "config", "persistence", "research", "search", "server")
EXTENSIONS = (".py", ".json", ".yaml", ".yml", ".toml", ".js", ".ts")
ACTION_FILES = (
    ".github/workflows/a2-e2-original-exposed-336.yml",
    ".github/scripts/a2_e2_source_identity_336.py",
)
BASELINE = "5faedcdf21c686fa2d4bee78a442c8e397f5a451"
REQUIRED = frozenset((
    *ACTION_FILES,
    "research/a2_locked_rotate_copy_pilot_336.py",
    "research/a2_e2_exposed_activation_336.py",
    "research/a2_e2_failure_manifest_336.py",
    "research/a2_e2_outcome_scoring_336.py",
    "research/a2_matched_recipient_contract_336.py",
    "research/a2_passive_native_recipient_observer_336.py",
    "research/a1_exposed_reader_pilot_317.py",
    "research/r2_write_rules_175.py",
    "research/protocols/a2_e2_exposed_rotate_336.json",
    "core/physics.py",
))


def tracked_source_blobs(ref: str) -> dict[str, str]:
    """Derive blob SHA from the checked-out Git *tree*, never the working dir."""
    raw = subprocess.check_output(
        ("git", "ls-tree", "-r", "-z", ref, "--", *ROOTS, *ACTION_FILES), timeout=15
    )
    result: dict[str, str] = {}
    for item in raw.split(b"\0"):
        if not item:
            continue
        header, path_bytes = item.split(b"\t", 1)
        _, kind, sha = header.decode("ascii").split()
        path = path_bytes.decode("utf-8")
        if (kind != "blob" or not path.endswith(EXTENSIONS)
                or not (path.startswith(tuple(root + "/" for root in ROOTS))
                        or path in ACTION_FILES)):
            continue
        if path in result:
            raise ValueError("duplicate source Git tree path")
        result[path] = sha
    return result


def compare_locked_sources(expected: dict[str, str],
                           observed: dict[str, str]) -> None:
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        raise ValueError("source inventory must be a path-to-SHA mapping")
    if not REQUIRED.issubset(expected):
        raise ValueError("scientific or failure-handler source missing from lock")
    if any(not isinstance(key, str) or not isinstance(value, str)
           or not re.fullmatch(r"[0-9a-f]{40}", value)
           for key, value in expected.items()):
        raise ValueError("malformed source-blob lock")
    if expected != observed:
        removed = sorted(set(expected) - set(observed))
        extra = sorted(set(observed) - set(expected))
        changed = sorted(key for key in set(expected) & set(observed)
                         if expected[key] != observed[key])
        raise ValueError(
            "unreviewed scientific source divergence: "
            + "removed=" + str(removed[:5])
            + " extra=" + str(extra[:5])
            + " changed=" + str(changed[:5])
        )


def verify_locked_tree(ref: str) -> dict[str, object]:
    """Verify exact source blob inventory; works on shallow CI checkouts."""
    manifest = json.loads(LOCK.read_text(encoding="utf-8"))
    if (manifest.get("schema") != "UG_A2_E2_REVIEWED_CODE_BLOB_LOCK_V1"
            or manifest.get("owner_issue") != 336
            or manifest.get("baseline_commit") != BASELINE
            or manifest.get("source_roots") != list(ROOTS)
            or manifest.get("source_actions") != list(ACTION_FILES)
            or manifest.get("file_extensions") != list(EXTENSIONS)
            or manifest.get("excluded_outcome_marker")
                != "research/approvals/a2_e2_336.run"):
        raise ValueError("source lock envelope is not the reviewed specification")
    actual = tracked_source_blobs(ref)
    compare_locked_sources(manifest["blobs"], actual)
    return {"status": "SOURCE_BLOB_LOCK_MATCH",
            "baseline": BASELINE,
            "locked_file_count": len(actual),
            "ref": ref,
            "scientific_experiment_executed": False}



def verify_source_lock(ref: str) -> dict[str, object]:
    """Execution gate: inventory AND complete Git ancestry, fail closed."""
    result = verify_locked_tree(ref)
    subprocess.run(
        ("git", "merge-base", "--is-ancestor", BASELINE, ref),
        check=True, timeout=10,
    )
    return result

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD^")
    args = parser.parse_args()
    print(json.dumps(verify_source_lock(args.ref), sort_keys=True))


if __name__ == "__main__":
    main()
