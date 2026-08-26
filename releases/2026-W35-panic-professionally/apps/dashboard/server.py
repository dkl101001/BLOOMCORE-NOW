# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Local dashboard server for Panic Professionally."""

from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

RELEASE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RELEASE_ROOT / "packages"))

from panic_professionally.store import PanicStore  # noqa: E402

INDEX = (Path(__file__).with_name("index.html")).read_bytes()


def handler_factory(database: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, value: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/":
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(INDEX)))
                self.end_headers()
                self.wfile.write(INDEX)
                return
            try:
                with PanicStore(database) as store:
                    if path == "/api/incidents":
                        self.send_json(store.list_incidents())
                        return
                    if path.startswith("/api/incidents/"):
                        incident_id = unquote(path.removeprefix("/api/incidents/"))
                        self.send_json(store.get_incident(incident_id))
                        return
            except KeyError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            self.send_json({"error": "route not found"}, HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:
            print(f"DASHBOARD PAPER TRAIL: {format % args}")

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the Panic Professionally dashboard")
    parser.add_argument("--db", type=Path, default=Path("panic-professionally.db"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), handler_factory(args.db))
    print(f"PANIC DASHBOARD: http://{args.host}:{args.port}")
    print("Read-only by design. Make decisions in the CLI where witnesses are present.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPanic contained within acceptable quarterly limits.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
