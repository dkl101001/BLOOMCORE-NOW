# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
from __future__ import annotations

import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

RELEASE = pathlib.Path(__file__).resolve().parents[1]
PACKAGES = RELEASE / "packages"
EXAMPLES = RELEASE / "examples"
sys.path.insert(0, str(PACKAGES))

from pledge_receipt.core import (  # noqa: E402
    audit_packet,
    diff_packets,
    inspect_json_bytes,
    render_markdown,
    scaffold_markdown,
    verify_receipt,
)


class PledgeReceiptTests(unittest.TestCase):
    def packet(self, name: str) -> dict:
        return inspect_json_bytes((EXAMPLES / name).read_bytes())

    def test_scaffold_extracts_normative_lines_without_inference(self) -> None:
        raw = (EXAMPLES / "policy-v1.md").read_bytes()
        packet = scaffold_markdown(
            raw,
            title="Example",
            issuer="Fixture",
            version="1",
            source_url="https://example.invalid/1",
        )
        self.assertEqual(len(packet["commitments"]), 3)
        self.assertTrue(all(item["actor"] is None for item in packet["commitments"]))
        self.assertIn("candidate extraction only", packet["scaffold_boundary"])

    def test_scaffold_is_deterministic(self) -> None:
        raw = (EXAMPLES / "policy-v1.md").read_bytes()
        kwargs = dict(title="Example", issuer="Fixture", version="1", source_url="https://example.invalid/1")
        self.assertEqual(scaffold_markdown(raw, **kwargs), scaffold_markdown(raw, **kwargs))

    def test_scaffold_rejects_non_utf8_and_no_pledges(self) -> None:
        with self.assertRaisesRegex(ValueError, "UTF-8"):
            scaffold_markdown(b"\xff", title="x", issuer="x", version="1", source_url="https://x.invalid")
        with self.assertRaisesRegex(ValueError, "no candidate"):
            scaffold_markdown(b"Plain factual sentence.\n", title="x", issuer="x", version="1", source_url="https://x.invalid")

    def test_complete_packet_is_testable_and_source_bound(self) -> None:
        receipt = audit_packet(
            self.packet("complete.packet.json"),
            (EXAMPLES / "complete-policy.md").read_bytes(),
        )
        self.assertEqual(receipt["summary"]["testable"], 2)
        self.assertEqual(receipt["summary"]["active_structural_gaps"], 0)
        self.assertTrue(receipt["source_verification"]["matched"])

    def test_gap_packet_preserves_partial_and_declarative(self) -> None:
        receipt = audit_packet(self.packet("with-gaps.packet.json"))
        self.assertEqual(receipt["summary"]["partial"], 2)
        self.assertEqual(receipt["summary"]["declarative"], 1)
        self.assertFalse(receipt["summary"]["all_active_commitments_testable"])
        flourishing = next(item for item in receipt["findings"] if item["id"] == "human-flourishing")
        self.assertIn("actor", flourishing["missing_fields"])

    def test_empty_exceptions_means_explicit_none(self) -> None:
        receipt = audit_packet(self.packet("complete.packet.json"))
        finding = receipt["findings"][0]
        self.assertEqual(finding["field_states"]["exceptions"], "explicit_none")

    def test_source_hash_mismatch_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "source SHA-256"):
            audit_packet(self.packet("complete.packet.json"), b"different bytes")

    def test_duplicate_ids_and_bad_hash_fail(self) -> None:
        packet = self.packet("complete.packet.json")
        packet["commitments"].append(copy.deepcopy(packet["commitments"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate commitment id"):
            audit_packet(packet)
        packet = self.packet("complete.packet.json")
        packet["document"]["source_sha256"] = "ABC"
        with self.assertRaisesRegex(ValueError, "64 lowercase"):
            audit_packet(packet)

    def test_json_parser_rejects_duplicates_and_nonfinite_numbers(self) -> None:
        for raw, message in (
            (b'{"schema":"x","schema":"y"}', "duplicate JSON key"),
            (b'{"value":NaN}', "non-finite JSON number"),
        ):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, message):
                    inspect_json_bytes(raw)

    def test_receipts_are_deterministic_verifiable_and_tamper_evident(self) -> None:
        packet = self.packet("complete.packet.json")
        first = audit_packet(packet)
        second = audit_packet(packet)
        self.assertEqual(first, second)
        self.assertTrue(verify_receipt(first))
        tampered = copy.deepcopy(first)
        tampered["summary"]["testable"] = 99
        self.assertFalse(verify_receipt(tampered))

    def test_diff_preserves_removed_and_lost_fields(self) -> None:
        receipt = diff_packets(
            self.packet("version-1.packet.json"),
            self.packet("version-2.packet.json"),
        )
        self.assertEqual(receipt["removed_ids"], ["human-flourishing"])
        self.assertGreaterEqual(receipt["summary"]["structural_weakening_signals"], 2)
        quarterly = next(item for item in receipt["changed_commitments"] if item["id"] == "quarterly-evaluation")
        changes = {(item["field"], item["kind"]) for item in quarterly["changes"]}
        self.assertIn(("deadline_or_cadence", "field_lost"), changes)
        self.assertTrue(verify_receipt(receipt))

    def test_rendering_states_boundaries(self) -> None:
        audit = render_markdown(audit_packet(self.packet("with-gaps.packet.json")))
        diff = render_markdown(diff_packets(self.packet("version-1.packet.json"), self.packet("version-2.packet.json")))
        self.assertIn("does not establish policy quality", audit)
        self.assertIn("Phi — RELEASE_CANDIDATE_NOT_SHIPPED", audit)
        self.assertIn("Structural weakening signals", diff)

    def test_cli_exit_codes_verification_and_no_clobber(self) -> None:
        env = {**os.environ, "PYTHONPATH": str(PACKAGES)}
        base = [sys.executable, "-m", "pledge_receipt"]
        with tempfile.TemporaryDirectory() as temp:
            out = pathlib.Path(temp)
            receipt = out / "receipt.json"
            markdown = out / "receipt.md"
            complete = subprocess.run(
                base + ["audit", str(EXAMPLES / "complete.packet.json"), "--source", str(EXAMPLES / "complete-policy.md"), "--json", str(receipt), "--markdown", str(markdown)],
                env=env, text=True, capture_output=True,
            )
            self.assertEqual(complete.returncode, 0, complete.stderr)
            verified = subprocess.run(base + ["verify", str(receipt)], env=env, text=True, capture_output=True)
            self.assertEqual(verified.returncode, 0, verified.stderr)
            gaps = subprocess.run(base + ["audit", str(EXAMPLES / "with-gaps.packet.json")], env=env, text=True, capture_output=True)
            self.assertEqual(gaps.returncode, 1)
            advisory = subprocess.run(base + ["audit", str(EXAMPLES / "with-gaps.packet.json"), "--advisory"], env=env, text=True, capture_output=True)
            self.assertEqual(advisory.returncode, 0)
            clobber = subprocess.run(base + ["audit", str(EXAMPLES / "complete.packet.json"), "--json", str(receipt)], env=env, text=True, capture_output=True)
            self.assertEqual(clobber.returncode, 2)
            self.assertIn("refusing to overwrite", clobber.stderr)

    def test_cli_diff_is_strict_on_structural_weakening(self) -> None:
        env = {**os.environ, "PYTHONPATH": str(PACKAGES)}
        command = [sys.executable, "-m", "pledge_receipt", "diff", str(EXAMPLES / "version-1.packet.json"), str(EXAMPLES / "version-2.packet.json")]
        strict = subprocess.run(command, env=env, text=True, capture_output=True)
        advisory = subprocess.run(command + ["--advisory"], env=env, text=True, capture_output=True)
        self.assertEqual(strict.returncode, 1)
        self.assertEqual(advisory.returncode, 0)


if __name__ == "__main__":
    unittest.main()
