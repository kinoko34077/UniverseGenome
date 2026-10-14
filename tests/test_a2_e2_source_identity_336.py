"""E2 #336: declared code hash must equal actual Git checkout, never a label."""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from research.a2_e2_exposed_activation_336 import (
    verify_activated_exposed_only,
)

SOURCE="710b906d5fd5bf800912abcb5e282e5d0f13068b"
MARKER=b"A2-E2-336-EXPOSED-544-545-ROTATE4-ONCE\n"


class ExactCheckoutProof(TestCase):
    def test_wrong_checkout_sha_is_not_authorized(self):
        outputs=iter([
            SimpleNamespace(stdout="f"*40+"\n",returncode=0),
            SimpleNamespace(stdout="",returncode=0),
        ])
        with patch("research.a2_e2_exposed_activation_336.Path.is_file",return_value=True), \
             patch("research.a2_e2_exposed_activation_336.Path.read_bytes",return_value=MARKER), \
             patch("research.a2_e2_exposed_activation_336.subprocess.run",
                   side_effect=lambda *a,**kw: next(outputs)):
            with self.assertRaises(PermissionError):
                verify_activated_exposed_only(exact_source_sha=SOURCE)

    def test_right_source_with_dirty_tracked_code_is_not_authorized(self):
        outputs=iter([
            SimpleNamespace(stdout=SOURCE+"\n",returncode=0),
            SimpleNamespace(stdout="",returncode=1),
        ])
        with patch("research.a2_e2_exposed_activation_336.Path.is_file",return_value=True), \
             patch("research.a2_e2_exposed_activation_336.Path.read_bytes",return_value=MARKER), \
             patch("research.a2_e2_exposed_activation_336.subprocess.run",
                   side_effect=lambda *a,**kw: next(outputs)):
            with self.assertRaises(PermissionError):
                verify_activated_exposed_only(exact_source_sha=SOURCE)
