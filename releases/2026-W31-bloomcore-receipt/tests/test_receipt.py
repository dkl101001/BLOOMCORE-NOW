# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ

from __future__ import annotations

import datetime as dt
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "packages" / "evidence-validator" / "bloomcore_receipt.py"
SPEC = importlib.util.spec_from_file_location("bloomcore_receipt", MODULE_PATH)
assert SPEC and SPEC.loader
receipt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(receipt)

FIXED_TIME = dt.datetime(2026, 7, 29, 12, 0, tzinfo=dt.timezone.utc)


class ReceiptTests(unittest.TestCase):
    def test_extracts_urls_and_dois_once(self) -> None:
        text = (
            "See https://example.com/report. "
            "The DOI is 10.1234/ABC.567 and https://doi.org/10.1234/ABC.567."
        )
        self.assertEqual(
            receipt.extract_references(text),
            ["https://example.com/report", "https://doi.org/10.1234/ABC.567"],
        )

    def test_offline_preserves_reference_as_unresolved(self) -> None:
        result = receipt.audit_text(
            "A published survey reports lower trust. https://example.com/survey",
            online=False,
            now=lambda: FIXED_TIME,
        )
        self.assertEqual(result["mode"], "offline")
        self.assertEqual(result["summary"]["references"], 1)
        self.assertEqual(result["findings"][0]["verdict"], "unresolved")
        self.assertFalse(result["limitations"] == [])

    def test_online_aligned_source(self) -> None:
        def fake_fetcher(url: str) -> dict[str, object]:
            return {
                "status": "reachable",
                "http_status": 200,
                "final_url": url,
                "content_type": "text/html",
                "title": "Developer survey trust in artificial intelligence",
                "text": "The developer survey reports lower trust in artificial intelligence tools.",
            }

        result = receipt.audit_text(
            "The developer survey reports lower trust in artificial intelligence tools. "
            "https://example.com/survey",
            online=True,
            fetcher=fake_fetcher,
            now=lambda: FIXED_TIME,
        )
        finding = result["findings"][0]
        self.assertEqual(finding["verdict"], "aligned")
        self.assertGreaterEqual(finding["alignment"], 0.45)

    def test_online_unreachable_is_red_flag(self) -> None:
        def fake_fetcher(url: str) -> dict[str, object]:
            return {"status": "unreachable", "error": "not found", "text": "", "title": ""}

        result = receipt.audit_text(
            "A source proves the numerical claim. https://example.invalid/paper",
            online=True,
            fetcher=fake_fetcher,
            now=lambda: FIXED_TIME,
        )
        self.assertEqual(result["summary"]["red_flags"], 1)
        self.assertEqual(result["findings"][0]["source_status"], "unreachable")

    def test_uncited_claim_is_not_silently_discarded(self) -> None:
        result = receipt.audit_text(
            "This claim contains enough words but has no explicit citation.",
            online=False,
            now=lambda: FIXED_TIME,
        )
        self.assertEqual(result["summary"]["claims"], 1)
        self.assertEqual(result["findings"][0]["kind"], "claim")
        self.assertEqual(result["findings"][0]["verdict"], "unresolved")

    def test_markdown_states_observational_boundary(self) -> None:
        result = receipt.audit_text(
            "This claim contains enough words but has no explicit citation.",
            online=False,
            now=lambda: FIXED_TIME,
        )
        rendered = receipt.render_markdown(result)
        self.assertIn("does not certify truth", rendered)
        self.assertIn("Authority: `observational`", rendered)

    def test_private_destination_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            receipt._validate_public_destination("http://127.0.0.1/private")

    def test_redirect_handler_rejects_private_destination(self) -> None:
        handler = receipt.SafeRedirectHandler()
        request = receipt.urllib.request.Request("https://example.com")
        with self.assertRaises(ValueError):
            handler.redirect_request(
                request,
                None,
                302,
                "found",
                {},
                "http://127.0.0.1/private",
            )

    def test_reference_limit_is_visible(self) -> None:
        text = " ".join(
            f"Claim number {index} cites https://example.com/{index}."
            for index in range(receipt.MAX_REFERENCES + 2)
        )
        result = receipt.audit_text(text, online=False, now=lambda: FIXED_TIME)
        limits = [item for item in result["findings"] if item["kind"] == "inspection_limit"]
        self.assertEqual(result["summary"]["references"], receipt.MAX_REFERENCES)
        self.assertTrue(limits)


if __name__ == "__main__":
    unittest.main()
