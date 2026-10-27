"""Regenerate checked-in deterministic examples from the replay fixture."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flockoff.cli import _load_jsonl
from flockoff.export import (
    build_public_bundle, make_local_draft_approval, publication_request_digest,
)
from flockoff.replay import run_records


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    signature = json.loads((ROOT / "SIGNATURES" / "candidate" / "flock_you_wifi_assertion_v0.1.0.json").read_text())
    records = _load_jsonl(ROOT / "TESTS" / "synthetic_traces" / "fixed_two_pass.jsonl")
    result = run_records(
        records, signature=signature, rotation_secret=bytes(range(32)),
        include_restricted=True,
    )
    examples = ROOT / "SCHEMAS" / "examples"
    examples.mkdir(parents=True, exist_ok=True)
    write(examples / "observation.json", result["observations"][0])
    write(examples / "receiver_pose.json", result["poses"][0])
    write(examples / "signature_match.json", result["signature_matches"][0])
    write(examples / "pose_association.json", result["pose_associations"][0])
    write(examples / "pass_partition.json", result["pass_partitions"][0])
    write(examples / "measurement_lineage.json", result["measurement_lineages"][0])
    write(examples / "node_estimate.json", result["node_revision"])
    write(examples / "evidence_receipt.json", result["receipt"])
    write(examples / "spatial_evidence_receipt.json", result["spatial_receipt"])
    public_args = {
        "node_revisions": [{
            **result["node_revision"], "publication_state": "PUBLIC_CANDIDATE",
        }],
        "public_evidence": [],
        "receipt_ids": [result["receipt"]["receipt_id"]],
        "aggregate_counts": {"WIFI_80211": len(result["observations"])},
    }
    approval = make_local_draft_approval(
        request_digest=publication_request_digest(**public_args),
        approved_at_utc="2026-08-22T12:30:00Z",
        operator_confirmation=True,
    )
    bundle = build_public_bundle(**public_args, approval=approval)
    write(examples / "publication_approval.json", approval)
    write(examples / "export_bundle.json", bundle)
    write(ROOT / "TESTS" / "receipts" / "fixed_two_pass.receipt.json", result["receipt"])
    write(ROOT / "TESTS" / "fixtures" / "fixed_two_pass.expected.json", {
        "node_id": result["node_revision"]["node_id"],
        "receipt_id": result["receipt"]["receipt_id"],
        "location": result["node_revision"]["location"],
        "observation_count": len(result["observations"]),
        "signature_match_count": len(result["signature_matches"]),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
