"""Serve the static Phase 3 observation/control surface.

This server is not a simulation clock and owns no authoritative universe state.
"""

from __future__ import annotations

import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .runtime import PopulationRuntime


ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "ui"


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
) -> ThreadingHTTPServer:
    resolved_runtime = runtime or PopulationRuntime()
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
    args = parser.parse_args(argv)

    server = build_server(args.host, args.port)
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
