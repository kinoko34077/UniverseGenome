"""#336 failure metadata is NOT an experiment or inferred outcome."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from research.a2_e2_failure_manifest_336 import (
    SCHEMA, build_failure_record, write_failure_record,
)

HEAD="4e31da5883333801a3255172f052506ea943b1e2"


class HonestE2FailureMetadataTests(unittest.TestCase):
    def test_compact_valid_reproducible_metadata(self):
        with TemporaryDirectory() as t:
            dest=Path(t)/"artifacts"/"failure.json"
            args=dict(stage="native-physics",reason="PROCESS_TIMEOUT",
                      source_sha=HEAD,run_id="38514056747",attempt=1,
                      original_output_exists=False)
            status=write_failure_record(dest,**args)
            original=dest.read_bytes()
            self.assertEqual(status["bytes"],len(original))
            self.assertLess(len(original),8192)
            record=json.loads(original)
            self.assertEqual(record["schema"],SCHEMA)
            self.assertEqual(record["classification"],"NOT_EVALUABLE_PENDING_INVESTIGATION")
            self.assertEqual(record["fixed_protocol"]["positive_exposed_seed"],544)
            self.assertEqual(record["fixed_protocol"]["negative_exposed_seed"],545)
            self.assertEqual(record["fixed_protocol"]["candidate"],"rotate_copy")
            self.assertEqual(record["fixed_protocol"]["post_h0_steps_planned"],1000)
            self.assertFalse(record["original_success_report_validated"])
            self.assertFalse(record["source_native_conditions_verified"])
            self.assertFalse(record["learning_claim"])
            with self.assertRaises(FileExistsError):
                write_failure_record(dest,**args)
            self.assertEqual(dest.read_bytes(),original)

    def test_failure_record_only_encodes_fixed_reason_no_raw_logs(self):
        record=build_failure_record(
            stage="source-preflight", reason="VALIDATION_FAILED",
            source_sha=HEAD, run_id="1",attempt=1,
            original_output_exists=True,
        )
        self.assertTrue(record["original_success_report_exists"])
        self.assertFalse(record["original_success_report_validated"])
        self.assertEqual(record["result_kind"],
                         "FAILURE_METADATA_ONLY_NOT_SCIENCE_OUTCOME")

    def test_reject_unbounded_or_forged_metadata(self):
        good=dict(stage="report-validation",reason="STEP_FAILED",
                  source_sha=HEAD,run_id="12345",attempt=1,
                  original_output_exists=False)
        for key,value in [
            ("stage","arbitrary"),("reason","exception: SECRET-TOKEN"),
            ("source_sha","not-a-sha"),("run_id","0"),("run_id","abc"),
            ("attempt",2),("attempt",True),
            ("original_output_exists","no"),
        ]:
            with self.subTest(key=key,value=value):
                bad=dict(good)
                bad[key]=value
                with self.assertRaises(ValueError):
                    build_failure_record(**bad)


if __name__=="__main__":
    unittest.main()
