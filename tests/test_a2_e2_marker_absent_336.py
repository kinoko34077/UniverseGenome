"""E2 #336: activation must remain unavailable before reviewed marker."""
from unittest import TestCase
from unittest.mock import patch

from research.a2_e2_exposed_activation_336 import verify_activated_exposed_only


class ExposedActivationAbsentContract(TestCase):
    def test_absent_activation_marker_fails_closed(self):
        with patch("research.a2_e2_exposed_activation_336.Path.is_file", return_value=False):
            with self.assertRaises(PermissionError):
                verify_activated_exposed_only(
                    exact_source_sha="710b906d5fd5bf800912abcb5e282e5d0f13068b"
                )
