# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from reconstruction_preflight.core import (
    ManifestError,
    canonical_bytes,
    digest_bytes,
    evaluate_manifest,
    load_manifest,
    verify_receipt,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def verified_manifest() -> tuple[dict, Path, str]:
    return load_manifest(EXAMPLES / "verified.json")


class CoreTests(unittest.TestCase):
    def test_verified_fixture(self) -> None:
        manifest, path, digest = verified_manifest()
        result = evaluate_manifest(manifest, manifest_path=path, input_sha256=digest)
        self.assertEqual(result.disposition, "VERIFIED_FOR_BUILD_SCOPE")
        self.assertEqual(result.issues, ())

    def test_missing_meaning_blocks(self) -> None:
        manifest, path, digest = load_manifest(EXAMPLES / "blocked-missing-meaning.json")
        result = evaluate_manifest(manifest, manifest_path=path, input_sha256=digest)
        self.assertEqual(result.disposition, "RECONSTRUCTION_BLOCKED")
        self.assertIn("meaning", {issue["subject"] for issue in result.issues})

    def test_each_dimension_is_independent(self) -> None:
        base, path, digest = verified_manifest()
        for name in base["dimensions"]:
            with self.subTest(name=name):
                manifest = deepcopy(base)
                manifest["dimensions"][name]["status"] = "UNKNOWN"
                manifest["scope"]["held_work"] = ["EX-001"]
                result = evaluate_manifest(manifest, manifest_path=path, input_sha256=digest)
                self.assertEqual(result.disposition, "RECONSTRUCTION_BLOCKED")

    def test_safe_independent_work_can_continue(self) -> None:
        manifest, path, digest = verified_manifest()
        manifest["dimensions"]["ancestry"]["status"] = "MISSING"
        manifest["scope"]["held_work"] = ["parent-dependent-change"]
        manifest["scope"]["independent_work"] = [{
            "id": "fresh-schema-doc",
            "dependency_ids": ["synthetic-source"],
            "dimension_ids": ["authority", "dependencies", "state", "behavior", "meaning"],
            "requirement_ids": ["EX-001"],
        }]
        result = evaluate_manifest(manifest, manifest_path=path, input_sha256=digest)
        self.assertEqual(result.disposition, "PARTIAL_BUT_INDEPENDENT_WORK_SAFE")

    def test_false_independence_is_rejected(self) -> None:
        manifest, path, digest = verified_manifest()
        manifest["dimensions"]["meaning"]["status"] = "MISSING"
        manifest["scope"]["held_work"] = ["semantic-change"]
        manifest["scope"]["independent_work"] = [{
            "id": "relabeled-independent",
            "dependency_ids": ["synthetic-source"],
            "dimension_ids": ["authority", "meaning"],
            "requirement_ids": ["EX-001"],
        }]
        result = evaluate_manifest(manifest, manifest_path=path, input_sha256=digest)
        self.assertEqual(result.disposition, "RECONSTRUCTION_BLOCKED")
        self.assertIn("INDEPENDENCE_NOT_ESTABLISHED", {i["code"] for i in result.issues})

    def test_required_reference_without_bytes_blocks(self) -> None:
        manifest, path, digest = verified_manifest()
        del manifest["sources"][0]["path"]
        result = evaluate_manifest(manifest, manifest_path=path, input_sha256=digest)
        self.assertEqual(result.disposition, "RECONSTRUCTION_BLOCKED")
        self.assertIn("SOURCE_UNRETRIEVED", {i["code"] for i in result.issues})

    def test_hash_mismatch_blocks(self) -> None:
        manifest, path, digest = verified_manifest()
        manifest["sources"][0]["sha256"] = "0" * 64
        result = evaluate_manifest(manifest, manifest_path=path, input_sha256=digest)
        self.assertEqual(result.disposition, "RECONSTRUCTION_BLOCKED")
        self.assertIn("SOURCE_HASH_MISMATCH", {i["code"] for i in result.issues})

    def test_path_traversal_is_rejected(self) -> None:
        manifest, path, digest = verified_manifest()
        manifest["sources"][0]["path"] = "../RVP_PREBUILD_LEDGER.md"
        with self.assertRaisesRegex(ManifestError, "escapes"):
            evaluate_manifest(manifest, manifest_path=path, input_sha256=digest)

    def test_absolute_path_is_rejected(self) -> None:
        manifest, path, digest = verified_manifest()
        manifest["sources"][0]["path"] = "/etc/passwd"
        with self.assertRaisesRegex(ManifestError, "relative"):
            evaluate_manifest(manifest, manifest_path=path, input_sha256=digest)

    def test_duplicate_source_id_is_rejected(self) -> None:
        manifest, path, digest = verified_manifest()
        manifest["sources"].append(deepcopy(manifest["sources"][0]))
        with self.assertRaisesRegex(ManifestError, "duplicate source"):
            evaluate_manifest(manifest, manifest_path=path, input_sha256=digest)

    def test_receipt_is_stable_under_object_key_reordering(self) -> None:
        manifest, path, digest = verified_manifest()
        first = evaluate_manifest(manifest, manifest_path=path, input_sha256=digest).receipt_with_hash()
        reordered = json.loads(json.dumps(manifest, sort_keys=True))
        second = evaluate_manifest(reordered, manifest_path=path, input_sha256=digest).receipt_with_hash()
        self.assertEqual(first, second)

    def test_receipt_verification_and_tamper_detection(self) -> None:
        manifest, path, digest = verified_manifest()
        receipt = evaluate_manifest(manifest, manifest_path=path, input_sha256=digest).receipt_with_hash()
        valid, _ = verify_receipt(receipt)
        self.assertTrue(valid)
        receipt["disposition"] = "RECONSTRUCTION_BLOCKED"
        valid, detail = verify_receipt(receipt)
        self.assertFalse(valid)
        self.assertIn("mismatch", detail)

    def test_noncanonical_status_is_rejected(self) -> None:
        manifest, path, digest = verified_manifest()
        manifest["dimensions"]["state"]["status"] = "PASS"
        with self.assertRaisesRegex(ManifestError, "status is invalid"):
            evaluate_manifest(manifest, manifest_path=path, input_sha256=digest)

    def test_invalid_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{no", encoding="utf-8")
            with self.assertRaises(ManifestError):
                load_manifest(path)

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema":"first","schema":"second"}', encoding="utf-8")
            with self.assertRaisesRegex(ManifestError, "duplicate JSON object key"):
                load_manifest(path)

    def test_canonical_bytes_preserve_unicode_and_sort_keys(self) -> None:
        value = {"z": "Sara ΣΩ", "a": 1}
        self.assertEqual(canonical_bytes(value), b'{"a":1,"z":"Sara \xce\xa3\xce\xa9"}\n')
        self.assertEqual(len(digest_bytes(canonical_bytes(value))), 64)


if __name__ == "__main__":
    unittest.main()

