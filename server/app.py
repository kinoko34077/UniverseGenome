"""Serve the Phase 5 authoritative optimizer through the bounded runtime API.

The server-owned runtime owns the SteadyStateOptimizer; browser rendering only
observes state and submits explicit controls.
"""

from __future__ import annotations

import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from core.experiment import ExperimentConfig, load_experiment_config
from core.physics import PhysicsConfig

from .runtime import PopulationRuntime


ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "ui"
DEFAULT_CONFIG = ROOT / "config" / "default.json"
DEFAULT_EXPERIMENT_CONFIG = ROOT / "config" / "experiment_v0_1.json"


def _load_physics_config(path: str | Path) -> PhysicsConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("physics config must be an object")
    return PhysicsConfig.from_mapping(payload)


class UniverseGenomeHandler(SimpleHTTPRequestHandler):
    runtime: PopulationRuntime

    def _json_response(self, payload: dict[str, Any], *, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path == "/api/state":
            self._json_response(self.runtime.state())
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path != "/api/control":
            self.send_error(404, "unknown API path")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("control payload must be an object")
            action = payload.pop("action")
            result = self.runtime.control(str(action), **payload)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._json_response({"error": str(exc)}, status=400)
            return
        self._json_response(result)


def build_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    runtime: PopulationRuntime | None = None,
    history_length: int = PopulationRuntime.DEFAULT_HISTORY_LENGTH,
    config: PhysicsConfig | None = None,
    experiment: ExperimentConfig | None = None,
) -> ThreadingHTTPServer:
    resolved_runtime = runtime or PopulationRuntime(
        history_length=history_length,
        config=config or _load_physics_config(DEFAULT_CONFIG),
        experiment=experiment or load_experiment_config(DEFAULT_EXPERIMENT_CONFIG),
    )
    handler_class = type(
        "ConfiguredUniverseGenomeHandler",
        (UniverseGenomeHandler,),
        {"runtime": resolved_runtime},
    )
    handler = partial(handler_class, directory=str(UI_DIR))
    server = ThreadingHTTPServer((host, port), handler)
    server.runtime = resolved_runtime
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the UniverseGenome observation runtime")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="authoritative base physics config JSON",
    )
    parser.add_argument(
        "--experiment-config",
        default=str(DEFAULT_EXPERIMENT_CONFIG),
        help="Phase 4/5 experiment protocol JSON",
    )
    parser.add_argument(
        "--history-length",
        type=int,
        choices=(128, 256, 512),
        default=PopulationRuntime.DEFAULT_HISTORY_LENGTH,
        help="bounded rewind history in generations",
    )
    args = parser.parse_args(argv)

    server = build_server(
        args.host,
        args.port,
        history_length=args.history_length,
        config=_load_physics_config(args.config),
        experiment=load_experiment_config(args.experiment_config),
    )
    print(f"Serving UniverseGenome runtime at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.runtime.close()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
