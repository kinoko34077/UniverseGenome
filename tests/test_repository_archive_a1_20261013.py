"""Verify the repository-committed original A1.3 ZIP research evidence.

No computation/seed/rule mutation; this tests provenance integrity only.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import unittest
import zipfile

from research.phase_g_memory_search_159 import _digest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research/artifacts/a1_317_mask_native_2026-10-13_manifest.json"


class RepositoryArchivedA1Study(unittest.TestCase):
    def test_original_zip_hashes_payload_digest_and_cross_interpreter_equality(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["observer_source_head_sha"],
                         "63ca219f807e184408e0a42640c5a7496938dd4c")
        self.assertFalse(manifest["learning_claim"])
        self.assertFalse(manifest["independent_confirmation"])
        self.assertEqual(manifest["experimental_conditions"]["checkpoints"],
                         [1, 10, 100, 250, 500, 1000])
        self.assertEqual(manifest["experimental_conditions"]["seed_roles"],
                         {"544": "exposed_h0_positive", "545": "exposed_h0_negative"})
        stored = {}
        for item in manifest["original_artifacts"]:
            path = ROOT / item["path"]
            raw = path.read_bytes()
            self.assertEqual(len(raw), item["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item["sha256"])
            with zipfile.ZipFile(path) as zf:
                self.assertEqual(zf.testzip(), None)
                self.assertEqual(zf.namelist(), [item["zip_member"]])
                payload = zf.read(item["zip_member"])
            result = json.loads(payload)
            if "json_digest" in item:
                self.assertEqual(result["digest"], item["json_digest"])
                self.assertEqual(_digest({k:v for k,v in result.items()
                                         if k != "digest"}), result["digest"])
                self.assertEqual(result["source_sha"],
                                 manifest["observer_source_head_sha"])
                self.assertFalse(result["learning_claim"])
            stored[item["zip_member"]] = (payload, result)
        a = stored["mask-3.12.json"][1]
        b = stored["mask-pypy3.11.json"][1]
        c = stored["mask-comparator.json"][1]
        self.assertEqual(a["environment"]["implementation"], "cpython")
        self.assertEqual(b["environment"]["implementation"], "pypy")
        self.assertEqual(a["observed"], b["observed"])
        self.assertEqual(c["status"], "PASS_ORIGINAL_NATIVE_MASK_ALGEBRA_PARITY")
        self.assertEqual(c["original_source"],
                         manifest["observer_source_head_sha"])
        self.assertEqual(c["observed_counts"],
                         {seed: value["counts"] for seed, value in a["observed"].items()})
        for name in ("mask-3.12.json", "mask-pypy3.11.json"):
            self.assertEqual(c["zip_input_json_sha256"][name],
                             hashlib.sha256(stored[name][0]).hexdigest())
        self.assertEqual(a["observed"]["544"]["counts"]["different_mask"], 36)
        self.assertEqual(a["observed"]["544"]["counts"]["different_mask_algebraic_inert"], 36)
        self.assertEqual(a["observed"]["544"]["counts"]["different_mask_native_output_different"], 0)
        self.assertEqual(a["observed"]["545"]["counts"]["matched_trace_different"], 0)
        self.assertEqual(a["observed"]["545"]["counts"]["different_mask"], 0)


if __name__ == "__main__":
    unittest.main()
