from __future__ import annotations

import json
from threading import Thread
import unittest
from urllib.request import Request, urlopen

from core.experiment import ExperimentConfig
from core.physics import PhysicsConfig
from server.app import build_server
from server.runtime import PopulationRuntime


class ServerRuntimeTests(unittest.TestCase):
    def setUp(self):
        config = PhysicsConfig(
            max_cells=4,
            initial_density=4,
            hp_decay=0,
            bond_gain=0,
            bond_decay=0,
        )
        experiment = ExperimentConfig(
            byte_hold_generations=0,
            byte_gap_generations=0,
            teacher_delay_generations=0,
            teacher_repetitions=1,
            evaluation_timeout_generations=0,
        )
        self.runtime = PopulationRuntime(
            history_length=128,
            config=config,
            experiment=experiment,
        )
        self.server = build_server(port=0, runtime=self.runtime)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.runtime.close()
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

    def test_api_state_and_controls_use_authoritative_phase5_optimizer(self):
        initial = self.request("GET", "/api/state")
        self.assertEqual(initial["authority"], "phase5_optimizer")
        self.assertEqual(initial["optimizer_generation"], 0)
        self.assertEqual(initial["slot_count"], 128)
        self.assertEqual(len(initial["summaries"]), 128)
        self.assertGreater(initial["summaries"][0]["active_cells"], 0)
        self.assertEqual(initial["history_length"], 128)
        self.assertEqual(initial["observation_target"], "authoritative")
        self.assertEqual(initial["selected_index"], 0)

        selected = self.request(
            "POST", "/api/control", {"action": "select", "index": 7}
        )
        self.assertEqual(selected["selected_index"], 7)

        authoritative_generation = selected["summaries"][7]["generation"]
        clone = self.request("POST", "/api/control", {"action": "clone"})
        self.assertEqual(clone["selected"]["index"], 7)
        self.assertEqual(clone["observation_target"], "clone")

        stepped = self.request(
            "POST", "/api/control", {"action": "step", "generations": 1}
        )
        self.assertEqual(
            stepped["selected"]["generation"],
            authoritative_generation + 1,
        )
        self.assertEqual(
            stepped["summaries"][7]["generation"],
            authoritative_generation,
        )
        self.assertEqual(stepped["optimizer_generation"], 0)

        searched = self.request(
            "POST", "/api/control", {"action": "search_step", "iterations": 1}
        )
        self.assertEqual(searched["optimizer_generation"], 1)

    def test_api_clone_rewind_optimizer_snapshot_reset_and_run_pause_are_bounded(self):
        initial = self.request("GET", "/api/state")
        authoritative_generation = initial["summaries"][0]["generation"]

        self.request("POST", "/api/control", {"action": "clone"})
        self.request(
            "POST", "/api/control", {"action": "step", "generations": 3}
        )
        rewound = self.request(
            "POST", "/api/control", {"action": "rewind", "generations": 2}
        )
        self.assertEqual(
            rewound["selected"]["generation"],
            authoritative_generation + 1,
        )
        self.assertEqual(
            rewound["summaries"][0]["generation"],
            authoritative_generation,
        )

        saved = self.request("POST", "/api/control", {"action": "save"})
        self.assertEqual(
            saved["snapshot"]["kind"],
            "UniverseGenomePhase5SteadyStateOptimizer",
        )
        self.request(
            "POST", "/api/control", {"action": "search_step", "iterations": 1}
        )
        loaded = self.request(
            "POST",
            "/api/control",
            {"action": "load", "snapshot": saved["snapshot"]},
        )
        self.assertEqual(
            loaded["optimizer_generation"],
            saved["snapshot"]["generation"],
        )

        pending = self.request(
            "POST",
            "/api/control",
            {
                "action": "set_parameters",
                "parameters": {"collision_damage": 16, "noise_attempts": 1},
            },
        )
        self.assertEqual(
            pending["pending_reset_parameters"]["collision_damage"],
            16,
        )
        self.assertNotEqual(pending["reset_config"]["collision_damage"], 16)

        running = self.request("POST", "/api/control", {"action": "run"})
        self.assertTrue(running["running"])
        paused = self.request("POST", "/api/control", {"action": "pause"})
        self.assertFalse(paused["running"])

        reset = self.request("POST", "/api/control", {"action": "reset"})
        self.assertEqual(reset["optimizer_generation"], 0)
        self.assertEqual(reset["reset_config"]["collision_damage"], 16)
        self.assertEqual(reset["reset_config"]["noise_attempts"], 1)
        self.assertEqual(reset["pending_reset_parameters"], {})


if __name__ == "__main__":
    unittest.main()
