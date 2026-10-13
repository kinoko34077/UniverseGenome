"""Validate source-bound exact original A1.7 JSONs retained in repository.

Decodes gzip+USTAR+base64 without writing extracted files to disk.
Shows original three Action JSON bytes are fully reproducible from Git alone.
"""
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import unittest


BASE = Path("research/artifacts")
MANIFEST = BASE / "a17_329_original_fusion_funnel_2026-10-14_manifest.json"
ARCHIVE = BASE / "a17_329_original_r2_fusion_reports.tar.gz.b64"


class OriginalFusionArchiveContract(unittest.TestCase):
    def test_exact_host_json_bytes_and_native_gate_disposition(self):
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(m["schema"],"UG_A17_ORIGINAL_R2_FUSION_ELIGIBILITY_GIT_ARCHIVE_V1")
        self.assertEqual(m["source_pr_head_sha"],
                         "e5bd5bd431e596b3e7ab2de987690a2d5a8acd8e")
        self.assertFalse(m["conditions"]["learning_claim"])
        self.assertFalse(m["conditions"]["independent_confirmation"])
        self.assertEqual(m["conditions"]["original_checkpoints"],[1,10,100,250,500,1000])
        self.assertEqual(m["conditions"]["original_h0_generation"],13)
        encoded=ARCHIVE.read_text(encoding="ascii").strip()
        data=base64.b64decode(encoded,validate=True)
        self.assertEqual(len(data),m["retained_original_bytes"]["decoded_gzip_bytes"])
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         m["retained_original_bytes"]["decoded_gzip_sha256"])
        tar_bytes=gzip.decompress(data)
        with tarfile.open(fileobj=io.BytesIO(tar_bytes),mode="r:") as tar:
            members=tar.getmembers()
            expected=m["retained_original_bytes"]["contained_json_exact_sha256"]
            self.assertEqual({x.name for x in members},set(expected))
            decoded={}
            for member in members:
                self.assertTrue(member.isfile())
                contents=tar.extractfile(member).read()
                self.assertEqual(hashlib.sha256(contents).hexdigest(),
                                 expected[member.name])
                decoded[member.name]=json.loads(contents)
        cp,pp=(decoded[x] for x in ("original-3.12.json",
                                     "original-pypy3.11.json"))
        cmp=decoded["a17-comparator.json"]
        self.assertEqual(cp["environment"]["python"],"cpython")
        self.assertEqual(pp["environment"]["python"],"pypy")
        self.assertEqual(cp["studies"],pp["studies"])
        self.assertEqual(cp["source_sha"],m["source_pr_head_sha"])
        self.assertEqual(cp["source_sha"],pp["source_sha"])
        self.assertEqual(cmp["status"],"PASS_SOURCE_FROZEN_EXPOSED_FUSION_STAGE_PARITY")
        self.assertTrue(cp["identical_replay"] and pp["identical_replay"])
        self.assertFalse(cp["learning_claim"] or pp["learning_claim"])
        self.assertEqual(cp["original_R2_manifest_digest"],
                         m["original_r2_manifest_sha256"])
        for seed, expected in (("544",(5843,3973,764,95,36)),
                               ("545",(6397,4325,966,0,0))):
            case=cp["studies"][seed]
            self.assertEqual(case["b"]["funnel_whole_horizon"],
                             case["h"]["funnel_whole_horizon"])
            self.assertEqual(case["original_paired_reader_counts"],
                {"matched":expected[2],"trace_diff":expected[3],
                 "changed_mask":expected[4]})
            result=case["b"]["funnel_whole_horizon"]
            g=result["gate_counts"]
            self.assertEqual((g["enumerated_groups"],g["nonoverlap"]),
                             expected[:2])
            self.assertEqual(g["exact_cover"],0)
            self.assertEqual(result["actual_fusions"],0)
            self.assertEqual(result["native_steps"],1000)
            summary=m["summary_per_branch"][seed]
            self.assertEqual(summary["exact_complete_2x2_cover"],0)
            for period, counts in summary["by_original_period_enumerated_nonoverlap_exact"].items():
                gates=case["b"]["funnel_by_original_period"][period]["gate_counts"]
                self.assertEqual([gates["enumerated_groups"],gates["nonoverlap"],
                                  gates["exact_cover"]],counts)


if __name__=="__main__":
    unittest.main()
