# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

RELEASE = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE = RELEASE / "examples" / "source-bound-workflow" / "workflow.json"
sys.path.insert(0, str(RELEASE / "packages"))

from triad_workflow.core import (  # noqa: E402
    APERTURE,
    AXES,
    CLAIMS_NOT_OBSERVED,
    WorkflowError,
    build_artifacts,
    load_json,
    replay_packet,
    canonical_bytes,
    sha256_bytes,
    validate_packet,
    verify_run,
)


class TriadWorkflowTests(unittest.TestCase):
    def packet(self) -> dict:
        return load_json(EXAMPLE)

    def test_reference_packet_is_valid_and_complete(self) -> None:
        result = validate_packet(self.packet(), EXAMPLE.parent)
        self.assertEqual(len(result["sources"]), 3)
        self.assertTrue(all(r["state"] == "CLOSED_WITH_EVIDENCE" for r in result["requirements"]))

    def test_requires_exactly_three_differentiated_roles(self) -> None:
        for mutation in ("missing", "fourth", "duplicate"):
            with self.subTest(mutation=mutation):
                packet = self.packet()
                if mutation == "missing":
                    packet["triad"]["roles"].pop()
                elif mutation == "fourth":
                    packet["triad"]["roles"].append(copy.deepcopy(packet["triad"]["roles"][0]))
                else:
                    packet["triad"]["roles"][1]["role"] = packet["triad"]["roles"][0]["role"]
                with self.assertRaises(WorkflowError):
                    validate_packet(packet, EXAMPLE.parent)

    def test_adapter_cannot_gain_semantic_authority(self) -> None:
        packet = self.packet()
        packet["triad"]["roles"][2]["authority"] = "GOVERNS"
        with self.assertRaisesRegex(WorkflowError, "authority mismatch"):
            validate_packet(packet, EXAMPLE.parent)

    def test_companion_is_exactly_aperture_bound(self) -> None:
        packet = self.packet()
        packet["selected_aperture"] = "ALL_PHASE38"
        with self.assertRaisesRegex(WorkflowError, "exact DSK aperture"):
            validate_packet(packet, EXAMPLE.parent)
        packet = self.packet()
        packet["selected_aperture"] = None
        with self.assertRaisesRegex(WorkflowError, "requires the exact DSK aperture"):
            validate_packet(packet, EXAMPLE.parent)
        self.assertEqual(APERTURE, self.packet()["selected_aperture"])

    def test_hash_mismatch_and_path_escape_are_rejected(self) -> None:
        packet = self.packet()
        packet["sources"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(WorkflowError, "role/source hash mismatch"):
            validate_packet(packet, EXAMPLE.parent)
        packet = self.packet()
        packet["sources"][0]["path"] = "../workflow.json"
        with self.assertRaisesRegex(WorkflowError, "escapes packet directory"):
            validate_packet(packet, EXAMPLE.parent)

    def test_all_eight_execution_axes_are_explicit(self) -> None:
        self.assertEqual(tuple(self.packet()["execution_profile"]), AXES)
        packet = self.packet()
        packet["execution_profile"].pop("authority")
        with self.assertRaisesRegex(WorkflowError, "execution_profile keys differ"):
            validate_packet(packet, EXAMPLE.parent)
        packet = self.packet()
        packet["execution_profile"]["seventh_axis_alias"] = ["ambiguous"]
        with self.assertRaises(WorkflowError):
            validate_packet(packet, EXAMPLE.parent)

    def test_all_five_epistemic_classes_are_explicit(self) -> None:
        packet = self.packet()
        packet["epistemic_claims"].pop()
        with self.assertRaisesRegex(WorkflowError, "all five"):
            validate_packet(packet, EXAMPLE.parent)

    def test_contradiction_requires_rejection_and_remainder(self) -> None:
        for field, value in (("rejected_interpretations", []), ("unresolved_remainder", "")):
            with self.subTest(field=field):
                packet = self.packet()
                packet["contradictions"][0][field] = value
                with self.assertRaises(WorkflowError):
                    validate_packet(packet, EXAMPLE.parent)

    def test_permissions_are_closed(self) -> None:
        for permission in self.packet()["permissions"]:
            with self.subTest(permission=permission):
                packet = self.packet()
                packet["permissions"][permission] = True
                with self.assertRaisesRegex(WorkflowError, "must be false"):
                    validate_packet(packet, EXAMPLE.parent)

    def test_completion_cannot_exceed_evidence(self) -> None:
        packet = self.packet()
        packet["requirements"][0]["state"] = "OPEN"
        packet["requirements"][0]["evidence"] = []
        with self.assertRaisesRegex(WorkflowError, "every requirement"):
            validate_packet(packet, EXAMPLE.parent)
        packet = self.packet()
        packet["requested_claim"] = "CANONICAL_PROMOTION"
        with self.assertRaisesRegex(WorkflowError, "exceeds"):
            validate_packet(packet, EXAMPLE.parent)

    def test_closed_requirement_needs_evidence(self) -> None:
        packet = self.packet()
        packet["requirements"][0]["evidence"] = []
        with self.assertRaisesRegex(WorkflowError, "closed without evidence"):
            validate_packet(packet, EXAMPLE.parent)

    def test_artifacts_are_deterministic_and_bounded(self) -> None:
        first = build_artifacts(self.packet(), EXAMPLE.parent)
        second = build_artifacts(self.packet(), EXAMPLE.parent)
        self.assertEqual(first, second)
        receipt = json.loads(first["workflow-receipt.json"])
        self.assertEqual(receipt["execution_axes"], list(AXES))
        self.assertEqual(receipt["claims_not_observed"], list(CLAIMS_NOT_OBSERVED))
        self.assertNotIn("recorded_at", receipt)

    def test_verify_and_replay_detect_tampering(self) -> None:
        artifacts = build_artifacts(self.packet(), EXAMPLE.parent)
        with tempfile.TemporaryDirectory() as temp:
            run = pathlib.Path(temp)
            for name, content in artifacts.items():
                (run / name).write_bytes(content)
            verify_run(run)
            replay_packet(self.packet(), EXAMPLE.parent, run)
            (run / "TRIAD_REPORT.md").write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(WorkflowError, "hash mismatch"):
                verify_run(run)
            with self.assertRaisesRegex(WorkflowError, "replay differs"):
                replay_packet(self.packet(), EXAMPLE.parent, run)

    def test_rehashed_receipt_cannot_change_bounded_invariants(self) -> None:
        artifacts = build_artifacts(self.packet(), EXAMPLE.parent)
        with tempfile.TemporaryDirectory() as temp:
            run = pathlib.Path(temp)
            for name, content in artifacts.items():
                (run / name).write_bytes(content)
            receipt = json.loads((run / "workflow-receipt.json").read_text(encoding="utf-8"))
            receipt.pop("canonical_sha256")
            receipt["bounded_claim"] = "CANONICAL_PROMOTION"
            receipt["canonical_sha256"] = sha256_bytes(canonical_bytes(receipt))
            (run / "workflow-receipt.json").write_bytes(canonical_bytes(receipt))
            with self.assertRaisesRegex(WorkflowError, "invariant mismatch"):
                verify_run(run)

    def test_duplicate_keys_and_nonfinite_numbers_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "bad.json"
            path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaisesRegex(WorkflowError, "duplicate JSON key"):
                load_json(path)
            path.write_text('{"a": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(WorkflowError, "non-finite"):
                load_json(path)

    def test_cli_validate_run_verify_replay_and_no_clobber(self) -> None:
        env_path = str(RELEASE / "packages")
        with tempfile.TemporaryDirectory() as temp:
            run = pathlib.Path(temp) / "run"
            base = [sys.executable, "-m", "triad_workflow"]
            env = {**__import__("os").environ, "PYTHONPATH": env_path}
            validate = subprocess.run(base + ["validate", str(EXAMPLE)], env=env, text=True, capture_output=True)
            self.assertEqual(validate.returncode, 0, validate.stderr)
            created = subprocess.run(base + ["run", str(EXAMPLE), "--out", str(run)], env=env, text=True, capture_output=True)
            self.assertEqual(created.returncode, 0, created.stderr)
            for command in (["verify", str(run)], ["replay", str(EXAMPLE), str(run)]):
                result = subprocess.run(base + command, env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            clobber = subprocess.run(base + ["run", str(EXAMPLE), "--out", str(run)], env=env, text=True, capture_output=True)
            self.assertEqual(clobber.returncode, 2)
            self.assertIn("refusing to overwrite", clobber.stderr)

    def test_source_files_remain_unchanged_after_run(self) -> None:
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (EXAMPLE.parent / "sources").iterdir()}
        with tempfile.TemporaryDirectory() as temp:
            build_artifacts(self.packet(), EXAMPLE.parent)
            self.assertFalse(any(pathlib.Path(temp).iterdir()))
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (EXAMPLE.parent / "sources").iterdir()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
