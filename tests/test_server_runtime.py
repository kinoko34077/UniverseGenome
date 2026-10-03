from __future__ import annotations

import json
from threading import Thread
import unittest
from urllib.request import Request, urlopen

from server.app import build_server


class ServerRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.server = build_server(port=0)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request) as response:
            self.assertEqual(response.status, 200)
            return json.loads(response.read().decode("utf-8"))

    def test_api_state_and_controls_change_authoritative_population(self):
        initial = self.request("GET", "/api/state")
        self.assertEqual(initial["generation"], 0)
        self.assertEqual(initial["slot_count"], 128)
        self.assertEqual(len(initial["summaries"]), 128)
        self.assertGreater(initial["active_cells"], 0)
        self.assertEqual(initial["history_length"], 512)
        self.assertEqual(initial["observation_target"], "authoritative")
        self.assertEqual(initial["selected_index"], 0)

        stepped = self.request("POST", "/api/control", {"action": "step"})
        self.assertEqual(stepped["generation"], 1)
        selected = self.request("POST", "/api/control", {"action": "select", "index": 7})
        self.assertEqual(selected["selected_index"], 7)
        clone = self.request("POST", "/api/control", {"action": "clone"})
        self.assertEqual(clone["clone"]["index"], 7)
        self.assertEqual(clone["generation"], 1)
        self.assertEqual(clone["observation_target"], "clone")

    def test_api_rewind_snapshot_reset_and_run_pause_are_bounded(self):
        self.request("POST", "/api/control", {"action": "step", "generations": 3})
        rewound = self.request("POST", "/api/control", {"action": "rewind", "generations": 2})
        self.assertEqual(rewound["generation"], 1)

        saved = self.request("POST", "/api/control", {"action": "save"})
        self.request("POST", "/api/control", {"action": "step"})
        loaded = self.request("POST", "/api/control", {"action": "load", "snapshot": saved["snapshot"]})
        self.assertEqual(loaded["generation"], 1)

        running = self.request("POST", "/api/control", {"action": "run"})
        self.assertTrue(running["running"])
        paused = self.request("POST", "/api/control", {"action": "pause"})
        self.assertFalse(paused["running"])
        reset = self.request("POST", "/api/control", {"action": "reset"})
        self.assertEqual(reset["generation"], 0)


if __name__ == "__main__":
    unittest.main()
