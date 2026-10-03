"""Serve the static Phase 3 observation/control surface.

This server is not a simulation clock and owns no authoritative universe state.
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "ui"


def build_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    handler = partial(SimpleHTTPRequestHandler, directory=str(UI_DIR))
    return ThreadingHTTPServer((host, port), handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the UniverseGenome Phase 3 UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    server = build_server(args.host, args.port)
    print(f"Serving Phase 3 UI at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
