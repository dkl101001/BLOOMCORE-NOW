# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "reconstruction_preflight", *args],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_verified_exit_code_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            result = self.run_cli("validate", "examples/verified.json", "--receipt", str(receipt))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["disposition"], "VERIFIED_FOR_BUILD_SCOPE")
            self.assertEqual(receipt.read_text(encoding="utf-8"), result.stdout)

    def test_blocked_exit_code(self) -> None:
        result = self.run_cli("validate", "examples/blocked-missing-meaning.json")
        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)["disposition"], "RECONSTRUCTION_BLOCKED")

    def test_verify_receipt_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            self.assertEqual(
                self.run_cli("validate", "examples/verified.json", "--receipt", str(receipt)).returncode,
                0,
            )
            verified = self.run_cli("verify-receipt", str(receipt))
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertTrue(verified.stdout.startswith("VALID "))


if __name__ == "__main__":
    unittest.main()

