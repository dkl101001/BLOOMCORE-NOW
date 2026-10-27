"""Recursive discovery and signature-drift state machine.

Detection failure is evidence about the detector, not evidence of target absence.
This module turns a bounded miss into an immutable failure artifact and an
explicit next-test campaign.  It never transmits to or controls a target.
"""

from __future__ import annotations

from typing import Any

from . import CODE_REVISION, runtime_source_digest
from .canonical import content_id, sha256_uri

DISCOVERY_STATES = {
    "HUNTING",
    "CANDIDATE_SIGNATURE",
    "CONTROL_TESTING",
    "REPLICATION_PENDING",
    "VALIDATED",
    "SENSING_APERTURE_INSUFFICIENT",
    "NO_PRACTICALLY_SEPARABLE_PASSIVE_SIGNATURE_YET",
}

_TRANSITIONS = {
    "HUNTING": {"CANDIDATE_SIGNATURE", "SENSING_APERTURE_INSUFFICIENT"},
    "CANDIDATE_SIGNATURE": {"CONTROL_TESTING", "HUNTING"},
    "CONTROL_TESTING": {"REPLICATION_PENDING", "HUNTING"},
    "REPLICATION_PENDING": {
        "VALIDATED",
        "HUNTING",
        "NO_PRACTICALLY_SEPARABLE_PASSIVE_SIGNATURE_YET",
    },
    "SENSING_APERTURE_INSUFFICIENT": {"HUNTING"},
    "NO_PRACTICALLY_SEPARABLE_PASSIVE_SIGNATURE_YET": {"HUNTING"},
    "VALIDATED": set(),
}


def _with_hash(body: dict[str, Any], id_prefix: str, id_field: str) -> dict[str, Any]:
    seeded = {**body, id_field: ""}
    identifier = content_id(id_prefix, seeded, 40)
    artifact = {**body, id_field: identifier}
    artifact["content_hash"] = sha256_uri(artifact)
    return artifact


def make_failure_packet(
    *,
    target_asset_ref: str,
    failed_expectation: str,
    observation_refs: list[str],
    coverage_refs: list[str],
    context_refs: list[str] | None = None,
    failed_assumption: str,
    rationale: str,
    next_test_seed: str,
    observed_at_utc: str,
) -> dict[str, Any]:
    """Preserve a detector miss without converting it into an absence claim."""

    if not target_asset_ref or not failed_expectation or not failed_assumption:
        raise ValueError("target, expectation and failed assumption are required")
    context_refs = list(context_refs or [])
    if not observation_refs and not coverage_refs and not context_refs:
        raise ValueError("a failure packet requires observation, coverage, or contextual evidence")
    if not next_test_seed:
        raise ValueError("a failure must seed a next test")
    body = {
        "schema_version": "1.1.0",
        "target_asset_ref": target_asset_ref,
        "failed_expectation": failed_expectation,
        "observation_refs": sorted(set(observation_refs)),
        "coverage_refs": sorted(set(coverage_refs)),
        "context_refs": sorted(set(context_refs)),
        "failed_assumption": failed_assumption,
        "rationale": rationale,
        "absence_claim_permitted": False,
        "next_test_seed": next_test_seed,
        "observed_at_utc": observed_at_utc,
        "algorithm": {
            "name": "recursive_failure_capture",
            "version": "1.1.0",
            "code_revision": CODE_REVISION,
            "code_digest": runtime_source_digest(),
        },
    }
    return _with_hash(body, "failure", "failure_id")


def open_discovery_campaign(
    failure_packet: dict[str, Any], *, next_tests: list[str], opened_at_utc: str
) -> dict[str, Any]:
    """Open a campaign from a preserved miss; UNKNOWN is never a terminal state."""

    if failure_packet.get("absence_claim_permitted") is not False:
        raise ValueError("failure packet must explicitly forbid absence inference")
    if not next_tests:
        raise ValueError("an unresolved campaign requires at least one next test")
    body = {
        "schema_version": "1.1.0",
        "target_asset_ref": failure_packet["target_asset_ref"],
        "origin_failure_ref": failure_packet["failure_id"],
        "state": "HUNTING",
        "known_features": [],
        "missing_features": [failure_packet["failed_expectation"]],
        "failed_assumptions": [failure_packet["failed_assumption"]],
        "next_tests": list(dict.fromkeys(next_tests)),
        "evidence_history": [failure_packet["failure_id"]],
        "signature_lineage": [],
        "claim_ceiling": "RF_ACTIVITY_PRESENT",
        "opened_at_utc": opened_at_utc,
        "updated_at_utc": opened_at_utc,
        "revision": 1,
        "parent_campaign_hash": None,
    }
    return _with_hash(body, "campaign", "campaign_id")


def advance_campaign(
    campaign: dict[str, Any], *, new_state: str, evidence_refs: list[str],
    next_tests: list[str], updated_at_utc: str, known_features: list[str] | None = None,
    missing_features: list[str] | None = None, signature_refs: list[str] | None = None,
    claim_ceiling: str | None = None,
) -> dict[str, Any]:
    """Append one deterministic campaign revision and enforce legal recursion."""

    current = campaign["state"]
    if current not in DISCOVERY_STATES or new_state not in DISCOVERY_STATES:
        raise ValueError("unsupported discovery state")
    if new_state not in _TRANSITIONS[current]:
        raise ValueError(f"illegal discovery transition {current} -> {new_state}")
    if new_state != "VALIDATED" and not next_tests:
        raise ValueError("unresolved discovery states require a next test")
    if new_state == "VALIDATED" and next_tests:
        raise ValueError("validated campaign cannot carry unresolved next tests")
    body = {
        "schema_version": "1.1.0",
        "campaign_id": campaign["campaign_id"],
        "target_asset_ref": campaign["target_asset_ref"],
        "origin_failure_ref": campaign["origin_failure_ref"],
        "state": new_state,
        "known_features": sorted(set(known_features if known_features is not None else campaign["known_features"])),
        "missing_features": sorted(set(missing_features if missing_features is not None else campaign["missing_features"])),
        "failed_assumptions": list(campaign["failed_assumptions"]),
        "next_tests": list(dict.fromkeys(next_tests)),
        "evidence_history": list(dict.fromkeys(campaign["evidence_history"] + evidence_refs)),
        "signature_lineage": list(dict.fromkeys(campaign["signature_lineage"] + (signature_refs or []))),
        "claim_ceiling": claim_ceiling or campaign["claim_ceiling"],
        "opened_at_utc": campaign["opened_at_utc"],
        "updated_at_utc": updated_at_utc,
        "revision": int(campaign["revision"]) + 1,
        "parent_campaign_hash": campaign["content_hash"],
    }
    # campaign_id is identity-stable across revisions; content hash is revision-specific.
    body["content_hash"] = sha256_uri(body)
    return body


def detect_signature_drift(
    *, target_asset_ref: str, signature_ref: str, prior_match_refs: list[str],
    current_match_refs: list[str], current_match_states: list[str],
    coverage_refs: list[str], coverage_adequate: bool, independent_miss_count: int,
    observed_at_utc: str,
) -> dict[str, Any]:
    """Classify a mismatch against a previously useful signature.

    Insufficient coverage never becomes drift.  Adequate repeated misses reactivate
    discovery but do not claim that the target stopped transmitting.
    """

    if not prior_match_refs:
        raise ValueError("drift requires prior matching evidence")
    if len(current_match_refs) != len(current_match_states) or not current_match_refs:
        raise ValueError("current match refs/states must be non-empty and aligned")
    mismatch = all(state in {"NO_MATCH", "NOT_EVALUABLE"} for state in current_match_states)
    if not mismatch:
        drift_state = "NO_DRIFT"
        action = "KEEP_DETECT"
    elif not coverage_adequate:
        drift_state = "INSUFFICIENT_COVERAGE"
        action = "RETEST_WITH_COMPLETE_COVERAGE"
    elif independent_miss_count >= 2:
        drift_state = "CONFIRMED_DRIFT"
        action = "DEGRADE_SIGNATURE_AND_REACTIVATE_DISCOVERY"
    else:
        drift_state = "SUSPECTED_DRIFT"
        action = "REACTIVATE_DISCOVERY"
    body = {
        "schema_version": "1.1.0",
        "target_asset_ref": target_asset_ref,
        "signature_ref": signature_ref,
        "prior_match_refs": sorted(set(prior_match_refs)),
        "current_match_refs": sorted(set(current_match_refs)),
        "coverage_refs": sorted(set(coverage_refs)),
        "coverage_adequate": bool(coverage_adequate),
        "independent_miss_count": int(independent_miss_count),
        "drift_state": drift_state,
        "required_action": action,
        "absence_claim_permitted": False,
        "observed_at_utc": observed_at_utc,
    }
    return _with_hash(body, "drift", "drift_id")


def validation_decision(
    *, candidate_signature_ref: str, positive_physical_nodes: int,
    negative_control_count: int, false_positive_count: int,
    independent_replication_sites: int, contradiction_refs: list[str],
    evidence_refs: list[str], evaluated_at_utc: str,
) -> dict[str, Any]:
    """Gate candidate evolution without manufacturing probability.

    This gate only decides whether a candidate may advance to registry field
    testing.  ACTIVE still requires the stricter signature registry policy.
    """

    if min(positive_physical_nodes, negative_control_count, false_positive_count, independent_replication_sites) < 0:
        raise ValueError("validation counts cannot be negative")
    if false_positive_count > negative_control_count:
        raise ValueError("false positives cannot exceed controls")
    reasons = []
    if positive_physical_nodes < 2:
        reasons.append("needs at least two distinct positive physical nodes")
    if negative_control_count < 30:
        reasons.append("needs at least thirty negative controls before field testing")
    if false_positive_count != 0:
        reasons.append("candidate produced false positives in current control set")
    if independent_replication_sites < 1:
        reasons.append("needs at least one replication site outside the discovery site")
    if contradiction_refs:
        reasons.append("unresolved contradictions remain")
    decision = "ADVANCE_TO_FIELD_TESTING" if not reasons else "RECURSE"
    body = {
        "schema_version": "1.1.0",
        "candidate_signature_ref": candidate_signature_ref,
        "positive_physical_nodes": positive_physical_nodes,
        "negative_control_count": negative_control_count,
        "false_positive_count": false_positive_count,
        "independent_replication_sites": independent_replication_sites,
        "contradiction_refs": sorted(set(contradiction_refs)),
        "evidence_refs": sorted(set(evidence_refs)),
        "decision": decision,
        "reasons": reasons,
        "probability": None,
        "evaluated_at_utc": evaluated_at_utc,
    }
    return _with_hash(body, "validation", "validation_id")
