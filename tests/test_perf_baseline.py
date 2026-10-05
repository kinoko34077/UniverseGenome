import unittest

from benchmarks.perf_baseline import (
    REPORT_SCHEMA_VERSION,
    UNMEASURED_IN_THIS_SLICE,
    _json_bytes,
    _timing_summary,
    build_report,
)


class PerformanceBaselineTests(unittest.TestCase):
    def test_timing_summary_uses_actual_elapsed_time(self):
        result = _timing_summary("generations", 212, 7.528)
        self.assertEqual(result["operations"], 212)
        self.assertAlmostEqual(result["operations_per_s"], 28.1615302869, places=6)
        self.assertAlmostEqual(result["mean_ms_per_operation"], 35.5094339623, places=6)

    def test_timing_summary_rejects_invalid_measurements(self):
        with self.assertRaises(ValueError):
            _timing_summary("calls", 0, 1.0)
        with self.assertRaises(ValueError):
            _timing_summary("calls", 1, 0.0)

    def test_json_bytes_matches_unicode_http_payload_semantics(self):
        encoded = _json_bytes({"label": "日本語"})
        self.assertIn("日本語".encode("utf-8"), encoded)
        self.assertNotIn(b"\\u65e5", encoded)

    def test_report_schema_keeps_measurement_boundaries_explicit(self):
        report = build_report(
            parameters={"seed": 0},
            physics={"unit": "generations", "operations": 1},
            projection={"unit": "calls", "operations": 1},
            serialization={"unit": "calls", "operations": 1, "payload_bytes": 42},
        )
        self.assertEqual(report["schema_version"], REPORT_SCHEMA_VERSION)
        self.assertEqual(report["kind"], "UniverseGenomePerformanceBaseline")
        self.assertEqual(report["measurement_boundary"], "read_only_existing_production_paths")
        self.assertEqual(
            set(report["measurements"]),
            {"physics_step", "runtime_state_projection", "json_serialization"},
        )
        self.assertEqual(tuple(report["not_measured"]), UNMEASURED_IN_THIS_SLICE)


if __name__ == "__main__":
    unittest.main()
