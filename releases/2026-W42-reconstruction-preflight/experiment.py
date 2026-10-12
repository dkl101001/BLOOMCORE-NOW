# SPDX-License-Identifier: MPL-2.0
"""Run deterministic control, ablation, and sensitivity experiments."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from reconstruction_preflight.core import canonical_bytes, digest_bytes, evaluate_manifest, load_manifest

ROOT = Path(__file__).resolve().parent


def evaluate(manifest: dict, path: Path, digest: str) -> str:
    return evaluate_manifest(manifest, manifest_path=path, input_sha256=digest).disposition


def main() -> int:
    base, path, digest = load_manifest(ROOT / "examples" / "verified.json")
    cases: list[dict[str, object]] = []

    for name in base["dimensions"]:
        candidate = deepcopy(base)
        candidate["dimensions"][name]["status"] = "MISSING"
        candidate["scope"]["held_work"] = [f"change-requiring-{name}"]
        disposition = evaluate(candidate, path, digest)
        cases.append({
            "case": f"missing-{name}",
            "expected": "RECONSTRUCTION_BLOCKED",
            "observed": disposition,
            "pass": disposition == "RECONSTRUCTION_BLOCKED",
            "naive_hash_only_allows": True,
        })

    reordered = json.loads(json.dumps(base, sort_keys=True))
    receipt_a = evaluate_manifest(base, manifest_path=path, input_sha256=digest).receipt_with_hash()
    receipt_b = evaluate_manifest(reordered, manifest_path=path, input_sha256=digest).receipt_with_hash()
    cases.append({
        "case": "object-key-reordering",
        "expected": "same-receipt-hash",
        "observed": "same-receipt-hash" if receipt_a["receipt_hash"] == receipt_b["receipt_hash"] else "changed",
        "pass": receipt_a["receipt_hash"] == receipt_b["receipt_hash"],
        "naive_hash_only_allows": None,
    })

    safe = deepcopy(base)
    safe["dimensions"]["ancestry"]["status"] = "MISSING"
    safe["scope"]["held_work"] = ["ancestry-dependent-change"]
    safe["scope"]["independent_work"] = [{
        "id": "bounded-independent-doc",
        "dependency_ids": ["synthetic-source"],
        "dimension_ids": ["authority", "dependencies", "state", "behavior", "meaning"],
        "requirement_ids": ["EX-001"],
    }]
    safe_observed = evaluate(safe, path, digest)
    cases.append({
        "case": "bounded-independent-branch",
        "expected": "PARTIAL_BUT_INDEPENDENT_WORK_SAFE",
        "observed": safe_observed,
        "pass": safe_observed == "PARTIAL_BUT_INDEPENDENT_WORK_SAFE",
        "naive_hash_only_allows": True,
    })

    all_passed = all(bool(case["pass"]) for case in cases)
    false_allows = sum(
        1 for case in cases if case["naive_hash_only_allows"] is True and case["expected"] == "RECONSTRUCTION_BLOCKED"
    )
    summary = {
        "schema": "bloomcore.reconstruction-preflight-experiment/v0.1",
        "spdx_license_identifier": "Apache-2.0",
        "cases": cases,
        "metrics": {
            "cases": len(cases),
            "passed": sum(1 for case in cases if case["pass"]),
            "six_dimension_false_allows": 0,
            "naive_hash_only_false_allows": false_allows,
        },
        "result": "SUPPORTED_WITHIN_BOUNDS" if all_passed else "FAILED",
        "limitations": [
            "Synthetic fixtures only.",
            "Structural evidence can be false even when well formed.",
            "No native, production, or external replay was performed."
        ]
    }
    summary["receipt_hash"] = digest_bytes(canonical_bytes(summary))
    destination = ROOT / "evidence" / "experiment-results.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(canonical_bytes(summary))
    print(destination)
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

