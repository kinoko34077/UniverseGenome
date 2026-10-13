"""Verify repository-native compact A1.4 evidence retains all 36 original source events."""
import json
from collections import Counter
from pathlib import Path
import unittest

from core.physics import apply_latent_operator

ARCHIVE=Path("research/artifacts/a1_317_bit_support_native_2026-10-13.json")

class A14ArchivedEvidenceTests(unittest.TestCase):
    def test_complete_original_changed_mask_events_are_semantically_replayable(self):
        data=json.loads(ARCHIVE.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"],"UG_A1_317_FROZEN_BIT_SUPPORT_COMPACT_V1")
        self.assertEqual(data["source_pr_head_sha"],
                         "ad8384967cbe740729e636d1724ecfe0fa0a30e3")
        self.assertEqual(data["conditions"]["seed_roles"],
            {"544":"previously_exposed_h0_positive","545":"previously_exposed_h0_negative"})
        self.assertEqual(data["conditions"]["original_r2_checkpoint_generations"],
                         [1,10,100,250,500,1000])
        self.assertFalse(data["conditions"]["learning_claim"])
        self.assertFalse(data["conditions"]["independent_confirmation"])
        self.assertEqual(data["observation"]["544"]["changed_mask"],36)
        self.assertEqual(data["observation"]["545"]["changed_mask"],0)
        self.assertEqual(len(data["original_changed_mask_rows"]),36)
        unique=set()
        groups=Counter()
        for row in data["original_changed_mask_rows"]:
            self.assertEqual(len(row),len(data["original_changed_mask_rows_fields"]))
            (relative,native,address,src_slot,dst_slot,src_epoch,dst_epoch,
                tr_b,tr_h,mask_b,mask_h,src,dst,after_b,after_h)=row
            self.assertEqual(native-relative,12)
            self.assertNotEqual(mask_b,mask_h)
            self.assertNotEqual(tr_b,tr_h)
            self.assertEqual(src,dst)
            self.assertEqual(src,1)
            self.assertEqual(apply_latent_operator("masked_copy",src,dst,mask_b),after_b)
            self.assertEqual(apply_latent_operator("masked_copy",src,dst,mask_h),after_h)
            self.assertEqual(after_b,after_h)
            key=(native,address,src_slot,dst_slot,src_epoch,dst_epoch)
            self.assertNotIn(key,unique)
            unique.add(key)
            period = "1-100" if relative<=100 else ("101-250" if relative<=250
                      else ("251-500" if relative<=500 else "501-1000"))
            self.assertLessEqual(relative,1000)
            groups[period]+=1
        self.assertEqual(dict(groups),{"1-100":1,"251-500":13,"501-1000":22})
        self.assertEqual(sum(data["observation"]["544"]["stage_changed_masks"].values()),36)
        self.assertEqual(len(data["runtime_original_artifacts"]),3)
        for entry in data["runtime_original_artifacts"]:
            self.assertEqual(len(entry["original_zip_sha256"]),64)
            self.assertTrue(all(c in "0123456789abcdef" for c in entry["original_zip_sha256"]))

if __name__=="__main__":unittest.main()
