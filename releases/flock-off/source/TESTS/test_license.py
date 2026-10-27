from __future__ import annotations

import hashlib
import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APACHE_2_LICENSE_SHA256 = "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"


class LicenseCustodyTests(unittest.TestCase):
    def test_original_license_is_consistent_across_release_metadata(self):
        self.assertEqual(
            hashlib.sha256((ROOT / "LICENSES" / "Apache-2.0.txt").read_bytes()).hexdigest(),
            APACHE_2_LICENSE_SHA256,
        )
        self.assertIn("Copyright 2026 Frazer", (ROOT / "NOTICE").read_text())
        pyproject = tomllib.loads(
            (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(pyproject["project"]["license"], "AGPL-3.0-only")
        self.assertEqual(hashlib.sha256((ROOT/'LICENSE').read_bytes()).hexdigest(),
                         '8efd18c6e6527d9f853673c691ebbc0fc017b7a549c26b834f93bb0645b7093e')
        sbom = json.loads(
            (ROOT / "THIRD_PARTY_NOTICES" / "sbom.cdx.json").read_text(encoding="utf-8")
        )
        declared = sbom["metadata"]["component"]["licenses"]
        self.assertEqual(declared, [{"license": {"id": "AGPL-3.0-only"}}])
        self.assertEqual(
            (ROOT / "SCHEMAS" / "observation.schema.json").read_bytes(),
            (
                ROOT / "src" / "flockoff" / "resources" / "SCHEMAS"
                / "observation.schema.json"
            ).read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
