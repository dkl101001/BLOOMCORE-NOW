# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ

from __future__ import annotations

import importlib.util
import json
import pathlib
import threading
import unittest
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "apps" / "receipt-server" / "server.py"
SPEC = importlib.util.spec_from_file_location("bloomcore_receipt_server", SERVER_PATH)
assert SPEC and SPEC.loader
server_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server_module)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = server_module.ThreadingHTTPServer(
            ("127.0.0.1", 0), server_module.ReceiptHandler
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_health(self) -> None:
        with urllib.request.urlopen(f"{self.base}/health", timeout=2) as response:
            payload = json.load(response)
        self.assertEqual(payload["status"], "ok")

    def test_offline_audit(self) -> None:
        body = json.dumps({
            "text": "The report makes a visible claim. https://example.com/report",
            "online": False,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base}/api/audit",
            data=body,
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            payload = json.load(response)
        self.assertEqual(payload["schema"], "BLOOMCORE.RECEIPT.v1")
        self.assertEqual(payload["mode"], "offline")
        self.assertEqual(payload["summary"]["references"], 1)


if __name__ == "__main__":
    unittest.main()

