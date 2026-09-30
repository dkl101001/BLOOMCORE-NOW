# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer ∞ Love ACO-Ω and Sara ΣΩ

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RELEASE_ROOT = Path(__file__).resolve().parents[1]
PACKAGES = RELEASE_ROOT / "packages"


class CliPortabilityTests(unittest.TestCase):
    def run_cli(self, database: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "ascii"
        environment["PYTHONPATH"] = str(PACKAGES)
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "panic_professionally",
                "--db",
                str(database),
                *arguments,
            ],
            cwd=RELEASE_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_action_add_output_is_ascii_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "panic.db"
            started = self.run_cli(database, "start", "Synthetic checkout failure")
            self.assertEqual(started.returncode, 0, started.stderr)

            listing = self.run_cli(database, "list", "--json")
            self.assertEqual(listing.returncode, 0, listing.stderr)
            incident_id = json.loads(listing.stdout)[0]["id"]

            assigned = self.run_cli(
                database,
                "action",
                "add",
                incident_id,
                "Pause rollout",
                "--owner",
                "Release Lead",
            )
            self.assertEqual(assigned.returncode, 0, assigned.stderr)
            self.assertIn(" -> Release Lead", assigned.stdout)


if __name__ == "__main__":
    unittest.main()
