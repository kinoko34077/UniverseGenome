"""A2 #336 authenticated exposed result: read-only postmortem, no physics steps."""
from __future__ import annotations

import base64
import hashlib
from io import BytesIO
import json
from pathlib import Path
import unittest
from zipfile import ZipFile

from core.physics import apply_latent_operator

ARCHIVE = Path(
    "research/artifacts/"
    "a2_e2_336_original_exposed_544_545_run38544898470.zip.base64"
)
ARCHIVE_SHA256 = "04a502b7ec7a908d87b1053e26e068f4b9592c9148b796f25b287bc983f89c27"
RAW_SHA256 = "cb321787f18592e981aadc28d008efaf6ff0626f2299ff41cdfb4fa5233bcc8c"
DECISION_SHA256 = "16b37df9a03aca47d6cbfc0f26d18c8fb9991feea3d47014a97c44d90e70530c"
EXPECTED_COUNTS = {
    "matched_selected_contacts": 764,
    "same_nontrace_context": 740,
    "confounded_precontext": 24,
    "unmatched_topology": 0,
    "trace_difference_with_equal_context": 72,
    "mask_difference_with_equal_context": 35,
    "recipient_difference_with_equal_context": 0,
}
HORIZONS = ("1", "10", "100", "250", "500", "1000")
DIVERSITY = {
    "544": (1, 1, 6, 8, 8, 3),
    "545": (1, 3, 3, 9, 10, 6),
}


def read_original_evidence():
    """Decode fixed original ZIP, never create/run any source-native universe."""
    raw = base64.b64decode(ARCHIVE.read_bytes(), validate=False)
    if hashlib.sha256(raw).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("original authentic E2 ZIP hash mismatch")
    with ZipFile(BytesIO(raw)) as z:
        names = set(z.namelist())
        expected = {
            "a2_e2_336_original_exposed_544_545.json",
            "a2_e2_336_classification.json",
        }
        if names != expected:
            raise ValueError("unexpected original ZIP members")
        data = z.read("a2_e2_336_original_exposed_544_545.json")
        decision = z.read("a2_e2_336_classification.json")
        if hashlib.sha256(data).hexdigest() != RAW_SHA256:
            raise ValueError("original full E2 report hash mismatch")
        if hashlib.sha256(decision).hexdigest() != DECISION_SHA256:
            raise ValueError("original predeclared F5 decision hash mismatch")
    return json.loads(data), json.loads(decision)


def local_mask_effect(source: int, dest: int, mask_b: int, mask_h: int) -> int:
    """Exact conditional XOR of output latent words for matched precontact."""
    rotated = ((source << 4) | (source >> 12)) & 0xFFFF
    return ((dest ^ rotated) & (mask_b ^ mask_h)) & 0xFFFF


class ArchivedE2MechanismRegression(unittest.TestCase):
    def test_original_zip_valid_negative_and_control_provenance(self):
        report, decision = read_original_evidence()
        self.assertEqual(report["runner_source_sha"],
                         "c5bb3429159098a4be4eef547dbb044c552a7f4c")
        self.assertEqual(decision["classification"],
                         "NEGATIVE_NO_MATCHED_RECIPIENT_EFFECT")
        self.assertEqual(decision["validity"], "CONTROLS_AND_MATCHED_CONTACT_COUNTS_VALID")
        self.assertFalse(decision["learning_claim"])
        self.assertFalse(decision["independent_confirmation"])
        self.assertEqual(decision["long_term_retention"], "NOT_ESTABLISHED")
        self.assertTrue(report["original_masked_copy_golden_parity"])
        self.assertTrue(report["negative_BH_full_equality"])
        self.assertTrue(report["positive_BB_sham_full_equality"])
        for key, value in EXPECTED_COUNTS.items():
            self.assertEqual(decision["counts"][key], value)
        self.assertEqual(
            decision["counts"]["matched_selected_contacts"],
            decision["counts"]["same_nontrace_context"]
            + decision["counts"]["confounded_precontext"],
        )

    def test_teacher_blind_alphabet_diversification_not_memory(self):
        report, _ = read_original_evidence()
        for seed, roles in (("544", ("b", "h", "control")), ("545", ("b", "h"))):
            for role in roles:
                record = report["data"][seed][role]
                observed = tuple(
                    record["distribution"][h]["distinct_latent_words"]
                    for h in HORIZONS
                )
                with self.subTest(seed=seed, role=role):
                    self.assertEqual(observed, DIVERSITY[seed])
                    self.assertEqual(record["metrics"]["native_fusions"], 0)
                    self.assertEqual(record["metrics"]["native_fragmentations"], 0)
                    self.assertTrue(record["uninstrumented_full_state_parity"])
        self.assertEqual(
            report["data"]["544"]["h"]["checkpoints"],
            report["data"]["544"]["control"]["checkpoints"],
        )
        self.assertNotEqual(
            report["data"]["544"]["b"]["checkpoints"]["1000"],
            report["data"]["544"]["h"]["checkpoints"]["1000"],
        )
        # Diversity does not identify teacher content or carrier persistence.

    def test_rotate_copy_exact_mask_xor_identity_without_native_step(self):
        words = (0, 1, 16, 17, 0x1234, 0x5555, 0x8000, 0xFFFF)
        masks = (0, 1, 8, 16, 17, 0x1234, 0xAAAA, 0xFFFF)
        for source in words:
            for dest in words:
                for mask_b in masks:
                    for mask_h in masks:
                        with self.subTest(source=source, dest=dest,
                                          mask_b=mask_b, mask_h=mask_h):
                            actual = (
                                apply_latent_operator(
                                    "rotate_copy", source, dest, mask_b, rotate_amount=4
                                )
                                ^ apply_latent_operator(
                                    "rotate_copy", source, dest, mask_h, rotate_amount=4
                                )
                            )
                            self.assertEqual(
                                actual, local_mask_effect(source, dest, mask_b, mask_h)
                            )

    def test_mask_change_can_be_effectively_invisible(self):
        # Given an identical source/destination precontext, mask bits that
        # select no source-vs-recipient difference cannot change output.
        self.assertEqual(local_mask_effect(1, 1, 0, 8), 0)
        self.assertEqual(local_mask_effect(1, 1, 0, 16), 16)


if __name__ == "__main__":
    unittest.main()
