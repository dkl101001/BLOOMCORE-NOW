# SPDX-License-Identifier: MPL-2.0
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
COMPLETE = RELEASE / "examples" / "complete.cdx.json"
GAPS = RELEASE / "examples" / "with-gaps.cdx.json"
sys.path.insert(0, str(RELEASE / "packages"))

from sbom_receipt.core import inspect_bytes, inspect_document, render_markdown, verify_receipt  # noqa: E402


class SbomReceiptTests(unittest.TestCase):
    def inspect(self, path: pathlib.Path) -> dict:
        return inspect_bytes(path.read_bytes())

    def test_complete_fixture_has_no_structural_gaps(self) -> None:
        receipt = self.inspect(COMPLETE)
        self.assertTrue(receipt["summary"]["structurally_complete"])
        self.assertEqual(receipt["summary"]["missing"], 0)
        self.assertEqual(receipt["summary"]["not_machine_verifiable"], 6)
        self.assertEqual(receipt["input"]["component_count"], 2)

    def test_gaps_and_explicit_unknowns_remain_distinct(self) -> None:
        receipt = self.inspect(GAPS)
        self.assertGreater(receipt["summary"]["missing"], 0)
        self.assertGreater(receipt["summary"]["explicit_unknown"], 0)
        statuses = {
            finding["element_id"]: finding["status"]
            for finding in receipt["component_findings"][0]["findings"]
        }
        self.assertEqual(statuses["component_version"], "explicit_unknown")
        self.assertEqual(statuses["component_dependency_relationship"], "present")

    def test_unlisted_dependency_node_is_missing(self) -> None:
        receipt = self.inspect(GAPS)
        statuses = {
            finding["element_id"]: finding["status"]
            for finding in receipt["component_findings"][1]["findings"]
        }
        self.assertEqual(statuses["component_dependency_relationship"], "missing")

    def test_receipt_is_deterministic_and_verifiable(self) -> None:
        first = self.inspect(COMPLETE)
        second = self.inspect(COMPLETE)
        self.assertEqual(first, second)
        self.assertTrue(verify_receipt(first))
        tampered = copy.deepcopy(first)
        tampered["summary"]["missing"] = 99
        self.assertFalse(verify_receipt(tampered))

    def test_markdown_contains_boundary_and_statuses(self) -> None:
        markdown = render_markdown(self.inspect(GAPS))
        self.assertIn("not a legal, regulatory or procurement compliance", markdown)
        self.assertIn("`explicit_unknown`", markdown)
        self.assertIn("Phi — RELEASE_CANDIDATE_NOT_SHIPPED", markdown)

    def test_public_profile_contract_matches_runtime(self) -> None:
        contract = json.loads(
            (RELEASE / "contracts" / "cisa-2026-structural-profile.json").read_text(
                encoding="utf-8"
            )
        )
        receipt = self.inspect(COMPLETE)
        self.assertEqual(contract["profile"], receipt["profile"]["name"])
        self.assertEqual(
            set(contract["document_elements"]),
            {item["element_id"] for item in receipt["document_findings"]},
        )
        self.assertEqual(
            set(contract["component_elements"]),
            {
                item["element_id"]
                for item in receipt["component_findings"][0]["findings"]
            },
        )
        self.assertEqual(
            set(contract["process_practices"]),
            {item["element_id"] for item in receipt["process_practices"]},
        )

    def test_wrong_format_and_version_are_rejected(self) -> None:
        for document, message in (
            ({"bomFormat": "SPDX", "specVersion": "2.3"}, "only CycloneDX"),
            ({"bomFormat": "CycloneDX", "specVersion": "1.3"}, "supported CycloneDX"),
        ):
            with self.subTest(document=document):
                with self.assertRaisesRegex(ValueError, message):
                    inspect_document(document, "0" * 64)

    def test_empty_component_inventory_is_reported(self) -> None:
        receipt = inspect_document({"bomFormat": "CycloneDX", "specVersion": "1.6"}, "0" * 64)
        finding = next(item for item in receipt["document_findings"] if item["element_id"] == "component_inventory")
        self.assertEqual(finding["status"], "missing")

    def test_duplicate_keys_and_nonfinite_numbers_are_rejected(self) -> None:
        for raw, message in (
            (b'{"bomFormat":"CycloneDX","bomFormat":"CycloneDX","specVersion":"1.6"}', "duplicate JSON key"),
            (b'{"bomFormat":"CycloneDX","specVersion":"1.6","version":NaN}', "non-finite JSON number"),
        ):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, message):
                    inspect_bytes(raw)

    def test_cli_check_verify_exit_codes_and_no_clobber(self) -> None:
        env = {**os.environ, "PYTHONPATH": str(RELEASE / "packages")}
        base = [sys.executable, "-m", "sbom_receipt"]
        with tempfile.TemporaryDirectory() as temp:
            out = pathlib.Path(temp)
            receipt_path = out / "complete.json"
            markdown_path = out / "complete.md"
            complete = subprocess.run(
                base + ["check", str(COMPLETE), "--json", str(receipt_path), "--markdown", str(markdown_path)],
                env=env, text=True, capture_output=True,
            )
            self.assertEqual(complete.returncode, 0, complete.stderr)
            verified = subprocess.run(base + ["verify", str(receipt_path)], env=env, text=True, capture_output=True)
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertIn("VERIFIED", verified.stdout)
            clobber = subprocess.run(base + ["check", str(COMPLETE), "--json", str(receipt_path)], env=env, text=True, capture_output=True)
            self.assertEqual(clobber.returncode, 2)
            self.assertIn("refusing to overwrite", clobber.stderr)

    def test_cli_gaps_fail_unless_advisory(self) -> None:
        env = {**os.environ, "PYTHONPATH": str(RELEASE / "packages")}
        base = [sys.executable, "-m", "sbom_receipt", "check", str(GAPS)]
        strict = subprocess.run(base, env=env, text=True, capture_output=True)
        advisory = subprocess.run(base + ["--advisory"], env=env, text=True, capture_output=True)
        self.assertEqual(strict.returncode, 1)
        self.assertEqual(advisory.returncode, 0)


if __name__ == "__main__":
    unittest.main()
