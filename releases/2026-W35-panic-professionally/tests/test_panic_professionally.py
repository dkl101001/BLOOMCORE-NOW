# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ

from __future__ import annotations

import sys
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

RELEASE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RELEASE_ROOT / "packages"))

from panic_professionally.core import InvalidTransition  # noqa: E402
from panic_professionally.store import PanicStore  # noqa: E402


class PanicStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = PanicStore(Path(self.temp.name) / "panic.db")
        self.incident = self.store.start_incident("Production smells like toast", "SEV-2", "Root Jenkins")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_incident_lifecycle_and_receipts(self) -> None:
        incident_id = self.incident["id"]
        self.store.transition(incident_id, "investigating")
        self.store.append_event(incident_id, "Smoke is metaphorical", "observation")
        action = self.store.add_action(incident_id, "Ask the toaster", "Chad Starch")
        self.store.complete_action(action["id"])
        self.store.transition(incident_id, "identified")
        self.store.transition(incident_id, "monitoring")
        resolved = self.store.transition(incident_id, "resolved")

        self.assertEqual(resolved["status"], "resolved")
        self.assertTrue(resolved["receipt_verification"]["valid"])
        self.assertEqual(resolved["actions"][0]["status"], "done")
        self.assertGreaterEqual(len(resolved["events"]), 7)

    def test_invalid_transition_is_rejected(self) -> None:
        with self.assertRaises(InvalidTransition):
            self.store.transition(self.incident["id"], "monitoring")

    def test_receipt_tampering_is_detected(self) -> None:
        incident_id = self.incident["id"]
        self.store.append_event(incident_id, "Original observation")
        self.store._connection.execute(
            "UPDATE events SET message = 'Edited after the meeting' WHERE incident_id = ? AND kind = 'observation'",
            (incident_id,),
        )
        self.store._connection.commit()
        verification = self.store.verify_receipts(incident_id)
        self.assertFalse(verification["valid"])
        self.assertTrue(verification["failed_sequences"])

    def test_exports_are_human_and_machine_readable(self) -> None:
        incident_id = self.incident["id"]
        markdown = self.store.export_markdown(incident_id)
        json_text = self.store.export_json(incident_id)
        self.assertIn("Production smells like toast", markdown)
        self.assertIn("Receipt chain: **VALID**", markdown)
        self.assertIn('"receipt_verification"', json_text)

    def test_serious_demo_creates_valid_synthetic_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory) / "demo"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RELEASE_ROOT / "examples" / "serious_demo.py"),
                    "--output-dir",
                    str(output_directory),
                ],
                cwd=RELEASE_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertTrue(summary["synthetic_data"])
            self.assertTrue(summary["receipt_verification"]["valid"])
            self.assertEqual(summary["receipt_verification"]["events_checked"], 10)
            self.assertTrue((output_directory / "incident.md").is_file())
            self.assertTrue((output_directory / "incident.json").is_file())


if __name__ == "__main__":
    unittest.main()
