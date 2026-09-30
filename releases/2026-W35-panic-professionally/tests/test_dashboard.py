# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from pathlib import Path

RELEASE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RELEASE_ROOT / "packages"))

from panic_professionally.store import PanicStore  # noqa: E402

SERVER_PATH = RELEASE_ROOT / "apps" / "dashboard" / "server.py"
SPEC = importlib.util.spec_from_file_location("panic_dashboard", SERVER_PATH)
assert SPEC and SPEC.loader
SERVER_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERVER_MODULE)


class DashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "panic.db"
        with PanicStore(self.database) as store:
            self.incident = store.start_incident("Moon fax machine unavailable", "SEV-4")
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), SERVER_MODULE.handler_factory(self.database)
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def test_dashboard_and_incident_api(self) -> None:
        with urllib.request.urlopen(self.base_url + "/", timeout=2) as response:
            page = response.read().decode("utf-8")
        self.assertIn("Panic Professionally", page)

        with urllib.request.urlopen(self.base_url + "/api/incidents", timeout=2) as response:
            listing = json.load(response)
        self.assertEqual(listing[0]["id"], self.incident["id"])

        with urllib.request.urlopen(
            self.base_url + "/api/incidents/" + self.incident["id"], timeout=2
        ) as response:
            detail = json.load(response)
        self.assertEqual(detail["title"], "Moon fax machine unavailable")
        self.assertTrue(detail["receipt_verification"]["valid"])

    def test_packaged_dashboard_matches_source_interface(self) -> None:
        source_html = (RELEASE_ROOT / "apps" / "dashboard" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertEqual(SERVER_MODULE.INDEX.decode("utf-8").splitlines(), source_html.splitlines())

    def test_missing_database_is_not_created(self) -> None:
        missing_database = Path(self.temp.name) / "missing.db"
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), SERVER_MODULE.handler_factory(missing_database)
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(HTTPError) as raised:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{server.server_port}/api/incidents", timeout=2
                )
            self.assertEqual(raised.exception.code, 503)
            self.assertFalse(missing_database.exists())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
